#!/usr/bin/env python3
"""Generate the WorkflowPatch client insight review demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T09:45:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def money(value: float) -> str:
    return f"{value:.2f}"


def ratio(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator / denominator:.2f}"


def block(row: dict[str, str], reason: str, detail: str) -> dict[str, str]:
    return {
        "row_id": row["row_id"] or "missing",
        "client_ref": row["client_ref"] or "missing",
        "blocked_reason": reason,
        "detail": detail,
        "next_step": "review_before_any_client_facing_output_or_live_access",
    }


def exception(row: dict[str, str], reason: str, detail: str) -> dict[str, str]:
    return {
        "row_id": row["row_id"],
        "client_ref": row["client_ref"],
        "exception_type": reason,
        "detail": detail,
        "review_needed": "strategist_review_before_client_ready_claim",
    }


def main() -> int:
    rows = read_csv("report-export.csv")
    seen_keys: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    draft_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in rows:
        required = (
            "row_id",
            "client_ref",
            "channel",
            "period_start",
            "revenue",
            "previous_revenue",
            "evidence_url",
            "duplicate_key",
        )
        missing = [field for field in required if not row[field].strip()]
        if missing:
            error_rows.append(
                {
                    "row_id": row["row_id"] or "missing",
                    "error_code": "missing_required_insight_field",
                    "error_detail": ",".join(missing),
                }
            )
            continue

        if row["source_boundary"] != "approved_redacted_export":
            blocked_rows.append(block(row, "live_client_data_scope", "Use approved redacted exports for the first proof."))
            continue

        duplicate_key = row["duplicate_key"].strip()
        if duplicate_key in seen_keys:
            blocked_rows.append(block(row, "duplicate_insight_key", f"duplicate_key={duplicate_key}"))
            continue
        seen_keys.add(duplicate_key)

        if row["date_range_status"] != "complete":
            exception_rows.append(exception(row, "date_range_exception", f"date_range_status={row['date_range_status']}"))
            continue
        if row["campaign_status"] != "active":
            exception_rows.append(exception(row, "stale_campaign_exception", f"campaign_status={row['campaign_status']}"))
            continue
        if not row["evidence_url"].strip():
            exception_rows.append(exception(row, "missing_evidence_exception", "evidence_url is missing"))
            continue

        spend = float(row["spend"])
        revenue = float(row["revenue"])
        previous_revenue = float(row["previous_revenue"])
        revenue_delta = revenue - previous_revenue
        roas = ratio(revenue, spend)

        if spend > revenue and spend >= 1000:
            exception_rows.append(exception(row, "spend_revenue_mismatch", f"spend={money(spend)} revenue={money(revenue)}"))
            continue

        decision = "monitor"
        review_action = "Keep in monthly review; no client-ready draft yet."
        if revenue_delta >= 1500 or (spend > 0 and revenue / spend >= 3):
            decision = "opportunity_candidate"
            review_action = "Strategist should review evidence before client-ready recommendation."

        ledger = {
            "row_id": row["row_id"],
            "client_ref": row["client_ref"],
            "channel": row["channel"],
            "period_start": row["period_start"],
            "spend": money(spend),
            "revenue": money(revenue),
            "previous_revenue": money(previous_revenue),
            "revenue_delta": money(revenue_delta),
            "roas": roas,
            "decision": decision,
            "evidence_url": row["evidence_url"],
            "processed_at": GENERATED_AT,
        }
        ledger_rows.append(ledger)

        if decision == "opportunity_candidate":
            review_rows.append(
                {
                    "row_id": row["row_id"],
                    "client_ref": row["client_ref"],
                    "review_type": "opportunity_review",
                    "evidence_url": row["evidence_url"],
                    "review_action": review_action,
                }
            )
            if row["draft_requested"] == "true":
                draft_rows.append(
                    {
                        "row_id": row["row_id"],
                        "client_ref": row["client_ref"],
                        "draft_status": "internal_review_only",
                        "draft_summary": f"{row['channel']} has an opportunity signal; verify evidence before client use.",
                        "client_boundary": "no_client_facing_send_or_publish",
                    }
                )

    write_csv(
        "opportunity-ledger.csv",
        ledger_rows,
        [
            "row_id",
            "client_ref",
            "channel",
            "period_start",
            "spend",
            "revenue",
            "previous_revenue",
            "revenue_delta",
            "roas",
            "decision",
            "evidence_url",
            "processed_at",
        ],
    )
    write_csv(
        "strategist-review-queue.csv",
        review_rows,
        ["row_id", "client_ref", "review_type", "evidence_url", "review_action"],
    )
    write_csv(
        "client-ready-draft-queue.csv",
        draft_rows,
        ["row_id", "client_ref", "draft_status", "draft_summary", "client_boundary"],
    )
    write_csv(
        "exception-queue.csv",
        exception_rows,
        ["row_id", "client_ref", "exception_type", "detail", "review_needed"],
    )
    write_csv(
        "blocked-insight-queue.csv",
        blocked_rows,
        ["row_id", "client_ref", "blocked_reason", "detail", "next_step"],
    )
    write_csv("error-log.csv", error_rows, ["row_id", "error_code", "error_detail"])

    print(f"source_rows={len(rows)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"draft_rows={len(draft_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
