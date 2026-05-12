#!/usr/bin/env python3
"""Generate the WorkflowPatch invoice reminder safety proof outputs."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TODAY = date(2026, 5, 10)


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value: str) -> date:
    year, month, day = (int(part) for part in value.split("-"))
    return date(year, month, day)


def main() -> int:
    invoices = read_csv("invoices.csv")
    policy = sorted(read_csv("reminder-policy.csv"), key=lambda row: int(row["threshold_days_after_due"]))
    payments: dict[str, int] = defaultdict(int)
    replies: dict[str, list[dict[str, str]]] = defaultdict(list)

    for payment in read_csv("payment-events.csv"):
        payments[payment["invoice_id"].strip()] += int(payment["amount"])
    for reply in read_csv("reply-events.csv"):
        replies[reply["invoice_id"].strip()].append(reply)

    seen_invoice_ids: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    send_rows: list[dict[str, str]] = []
    dispute_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for invoice in invoices:
        invoice_id = invoice["invoice_id"].strip()
        customer_email = invoice["customer_email"].strip()
        customer_name = invoice["customer_name"].strip()
        evidence = []

        if not invoice_id or not customer_email or not invoice["due_date"].strip():
            error_rows.append(
                {
                    "invoice_id": invoice_id or "missing",
                    "error": "missing required invoice id, email, or due date",
                    "evidence": f"customer_email={customer_email or 'missing'} due_date={invoice['due_date'] or 'missing'}",
                }
            )
            continue

        if invoice_id in seen_invoice_ids:
            error_rows.append(
                {
                    "invoice_id": invoice_id,
                    "error": "duplicate invoice id",
                    "evidence": f"second row attempted customer_email={customer_email}",
                }
            )
            continue
        seen_invoice_ids.add(invoice_id)

        amount = int(invoice["amount"])
        paid_amount = payments[invoice_id]
        days_overdue = (TODAY - parse_date(invoice["due_date"])).days
        last_stage = int(invoice["last_reminder_stage"] or "0")
        invoice_replies = replies[invoice_id]

        if paid_amount >= amount:
            ledger_rows.append(
                {
                    "invoice_id": invoice_id,
                    "customer_name": customer_name,
                    "days_overdue": str(days_overdue),
                    "paid_amount": str(paid_amount),
                    "next_state": "paid_blocked",
                    "evidence": "payment total covers invoice",
                }
            )
            blocked_rows.append(
                {
                    "invoice_id": invoice_id,
                    "block_reason": "already_paid",
                    "evidence": f"payment total {paid_amount} covers amount {amount}",
                    "next_check": "No reminder. Reconcile and close.",
                }
            )
            continue

        if invoice_replies:
            reply = invoice_replies[-1]
            classification = reply["classification"].strip()
            ledger_rows.append(
                {
                    "invoice_id": invoice_id,
                    "customer_name": customer_name,
                    "days_overdue": str(days_overdue),
                    "paid_amount": str(paid_amount),
                    "next_state": "dispute_review" if classification == "dispute" else "reply_review",
                    "evidence": f"reply classified as {classification}",
                }
            )
            dispute_rows.append(
                {
                    "invoice_id": invoice_id,
                    "customer_email": customer_email,
                    "classification": classification,
                    "received_at": reply["received_at"],
                    "review_note": (
                        "Pause reminders and ask owner to review booth count."
                        if classification == "dispute"
                        else "Pause automated reminders until promised payment date passes."
                    ),
                }
            )
            if classification != "dispute":
                blocked_rows.append(
                    {
                        "invoice_id": invoice_id,
                        "block_reason": "customer_replied",
                        "evidence": f"{classification} received {reply['received_at']}",
                        "next_check": "Check promised payment date before any template send.",
                    }
                )
            continue

        due_stage = None
        for rule in policy:
            if days_overdue >= int(rule["threshold_days_after_due"]):
                due_stage = rule

        if due_stage is None:
            ledger_rows.append(
                {
                    "invoice_id": invoice_id,
                    "customer_name": customer_name,
                    "days_overdue": str(days_overdue),
                    "paid_amount": str(paid_amount),
                    "next_state": "not_due",
                    "evidence": "below first reminder threshold",
                }
            )
            blocked_rows.append(
                {
                    "invoice_id": invoice_id,
                    "block_reason": "not_due",
                    "evidence": f"{days_overdue} days overdue; first reminder threshold is {policy[0]['threshold_days_after_due']}",
                    "next_check": "Check again after 2026-05-11.",
                }
            )
            continue

        stage = int(due_stage["stage"])
        if stage <= last_stage:
            ledger_rows.append(
                {
                    "invoice_id": invoice_id,
                    "customer_name": customer_name,
                    "days_overdue": str(days_overdue),
                    "paid_amount": str(paid_amount),
                    "next_state": "duplicate_stage_blocked",
                    "evidence": f"stage {stage} already sent or exceeded",
                }
            )
            blocked_rows.append(
                {
                    "invoice_id": invoice_id,
                    "block_reason": "duplicate_stage",
                    "evidence": f"last_reminder_stage={last_stage}; due_stage={stage}",
                    "next_check": "Do not resend the same reminder stage.",
                }
            )
            continue

        if paid_amount:
            evidence.append(f"partial payment {paid_amount} of {amount} found")
        else:
            evidence.append("no payment or reply event found")
        send_evidence = f"{days_overdue} days overdue; {'; '.join(evidence)}"
        ledger_rows.append(
            {
                "invoice_id": invoice_id,
                "customer_name": customer_name,
                "days_overdue": str(days_overdue),
                "paid_amount": str(paid_amount),
                "next_state": f"stage_{stage}_review",
                "evidence": f"stage {stage} is due; {'; '.join(evidence)}",
            }
        )
        send_rows.append(
            {
                "invoice_id": invoice_id,
                "customer_email": customer_email,
                "stage": str(stage),
                "template_id": due_stage["template_id"],
                "draft_subject": f"Quick invoice check for {invoice_id}",
                "approval_status": "needs human approval",
                "evidence": send_evidence,
            }
        )

    write_csv(
        "reminder-ledger.csv",
        ledger_rows,
        ["invoice_id", "customer_name", "days_overdue", "paid_amount", "next_state", "evidence"],
    )
    write_csv(
        "send-review-queue.csv",
        send_rows,
        ["invoice_id", "customer_email", "stage", "template_id", "draft_subject", "approval_status", "evidence"],
    )
    write_csv(
        "dispute-review-queue.csv",
        dispute_rows,
        ["invoice_id", "customer_email", "classification", "received_at", "review_note"],
    )
    write_csv(
        "blocked-send-queue.csv",
        blocked_rows,
        ["invoice_id", "block_reason", "evidence", "next_check"],
    )
    write_csv("error-log.csv", error_rows, ["invoice_id", "error", "evidence"])

    print(f"ledger_rows={len(ledger_rows)}")
    print(f"send_rows={len(send_rows)}")
    print(f"dispute_rows={len(dispute_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
