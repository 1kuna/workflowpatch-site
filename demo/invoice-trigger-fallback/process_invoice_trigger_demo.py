#!/usr/bin/env python3
"""Generate the WorkflowPatch invoice trigger fallback proof outputs."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MAX_TRIGGER_DELAY_MINUTES = 30


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def minutes_between(start: str, end: str) -> int:
    return int((parse_dt(end) - parse_dt(start)).total_seconds() // 60)


def main() -> int:
    invoices = read_csv("qbo-invoices.csv")
    runs_by_invoice: dict[str, list[dict[str, str]]] = {}
    for run in read_csv("zap-trigger-runs.csv"):
        runs_by_invoice.setdefault(run["invoice_id"], []).append(run)

    event_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for invoice in invoices:
        invoice_id = invoice["invoice_id"].strip()
        customer_email = invoice["customer_email"].strip()
        invoice_status = invoice["invoice_status"].strip().lower()
        runs = sorted(runs_by_invoice.get(invoice_id, []), key=lambda row: row["zap_triggered_at"])

        if not customer_email:
            error_rows.append(
                {
                    "invoice_id": invoice_id,
                    "error_code": "missing_customer_email",
                    "error_detail": "Cannot prepare invoice email review without a recipient address.",
                }
            )
            continue

        if invoice_status not in {"open", "sent"}:
            blocked_rows.append(
                {
                    "invoice_id": invoice_id,
                    "reason": "invoice_not_open",
                    "evidence": f"invoice_status={invoice_status}",
                    "reviewer_action": "Do not send. Confirm invoice should still be collected before replay.",
                }
            )
            continue

        if not runs:
            review_rows.append(
                {
                    "invoice_id": invoice_id,
                    "reason": "missing_instant_trigger",
                    "evidence": "Invoice exists in QBO export but no Zap trigger run is present.",
                    "reviewer_action": "Queue fallback lookup and compare before any client email.",
                }
            )
            continue

        first_run = runs[0]
        delay = minutes_between(invoice["qbo_created_at"], first_run["zap_triggered_at"])
        link_ready_delay = minutes_between(first_run["zap_triggered_at"], invoice["stripe_link_ready_at"])

        if len(runs) > 1:
            blocked_rows.append(
                {
                    "invoice_id": invoice_id,
                    "reason": "duplicate_trigger_runs",
                    "evidence": f"zap_runs={';'.join(run['zap_run_id'] for run in runs)}",
                    "reviewer_action": "Keep one invoice email draft and block duplicate sends.",
                }
            )

        if first_run["stripe_link_present"].strip().lower() != "true" or link_ready_delay > 0:
            blocked_rows.append(
                {
                    "invoice_id": invoice_id,
                    "reason": "stripe_link_not_ready",
                    "evidence": (
                        f"zap_triggered_at={first_run['zap_triggered_at']} "
                        f"stripe_link_ready_at={invoice['stripe_link_ready_at']}"
                    ),
                    "reviewer_action": "Hold client email until the payment link is present in the review draft.",
                }
            )
            continue

        if delay > MAX_TRIGGER_DELAY_MINUTES:
            review_rows.append(
                {
                    "invoice_id": invoice_id,
                    "reason": "late_instant_trigger",
                    "evidence": f"trigger_delay_minutes={delay}",
                    "reviewer_action": "Confirm the fallback path caught this before staff waited on the instant trigger.",
                }
            )

        event_rows.append(
            {
                "invoice_id": invoice_id,
                "customer_name": invoice["customer_name"],
                "qbo_created_at": invoice["qbo_created_at"],
                "zap_run_id": first_run["zap_run_id"],
                "trigger_delay_minutes": str(delay),
                "decision": "ready_for_invoice_email_review" if delay <= MAX_TRIGGER_DELAY_MINUTES else "late_but_recovered",
                "evidence": f"stripe_link_present=true duplicate_runs={len(runs)}",
                "next_step": "Review draft before any client email send.",
            }
        )

    write_csv(
        "invoice-event-ledger.csv",
        event_rows,
        [
            "invoice_id",
            "customer_name",
            "qbo_created_at",
            "zap_run_id",
            "trigger_delay_minutes",
            "decision",
            "evidence",
            "next_step",
        ],
    )
    write_csv(
        "delayed-invoice-review.csv",
        review_rows,
        ["invoice_id", "reason", "evidence", "reviewer_action"],
    )
    write_csv(
        "blocked-send-queue.csv",
        blocked_rows,
        ["invoice_id", "reason", "evidence", "reviewer_action"],
    )
    write_csv("error-log.csv", error_rows, ["invoice_id", "error_code", "error_detail"])

    print(f"invoice_rows={len(invoices)}")
    print(f"ledger_rows={len(event_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
