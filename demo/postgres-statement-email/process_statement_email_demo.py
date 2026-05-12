#!/usr/bin/env python3
"""Generate the WorkflowPatch Postgres statement email proof outputs."""

from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


def statement_identity(row: dict[str, str]) -> tuple[str, str, str] | None:
    week_start = row["week_start"].strip()
    workflow_type = row["workflow_type"].strip()
    if workflow_type == "pair_statement":
        party_a = row["party_a_email"].strip()
        party_b = row["party_b_email"].strip()
        if not party_a or not party_b:
            return None
        return (week_start, workflow_type, f"{party_a}+{party_b}")
    if workflow_type == "external_statement":
        recipient = row["external_recipient_email"].strip()
        if not recipient:
            return None
        return (week_start, workflow_type, recipient)
    return None


def main() -> int:
    sent_keys = {row["statement_key"].strip() for row in read_csv("send-history.csv")}
    seen_record_ids: set[str] = set()
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in read_csv("session-records.csv"):
        record_id = row["record_id"].strip()
        week_start = row["week_start"].strip()
        workflow_type = row["workflow_type"].strip()

        if not record_id or not week_start or not workflow_type:
            error_rows.append(
                {
                    "record_id": record_id or "missing",
                    "status": "error",
                    "reason": "missing record id, week start, or workflow type",
                    "evidence": f"week_start={week_start or 'missing'} workflow_type={workflow_type or 'missing'}",
                }
            )
            continue

        if record_id in seen_record_ids:
            error_rows.append(
                {
                    "record_id": record_id,
                    "status": "error",
                    "reason": "duplicate source record id",
                    "evidence": "record_id appeared earlier in this run",
                }
            )
            continue
        seen_record_ids.add(record_id)

        if row["status"].strip() != "approved":
            blocked_rows.append(
                {
                    "record_id": record_id,
                    "statement_key": "not_created",
                    "status": "blocked",
                    "reason": "source row not approved",
                    "evidence": f"status={row['status'].strip() or 'missing'}",
                    "next_step": "Approve or remove source row before statement generation.",
                }
            )
            continue

        try:
            Decimal(row["amount"].strip())
            Decimal(row["hours"].strip())
        except (InvalidOperation, ValueError):
            error_rows.append(
                {
                    "record_id": record_id,
                    "status": "error",
                    "reason": "amount or hours is not numeric",
                    "evidence": f"hours={row['hours']} amount={row['amount']}",
                }
            )
            continue

        identity = statement_identity(row)
        if identity is None:
            blocked_rows.append(
                {
                    "record_id": record_id,
                    "statement_key": "not_created",
                    "status": "blocked",
                    "reason": "missing required statement recipient",
                    "evidence": (
                        f"workflow_type={workflow_type} "
                        f"party_a={row['party_a_email'] or 'missing'} "
                        f"party_b={row['party_b_email'] or 'missing'} "
                        f"external={row['external_recipient_email'] or 'missing'}"
                    ),
                    "next_step": "Fix recipient mapping before drafting the email.",
                }
            )
            continue

        statement_key = "|".join(identity)
        if statement_key in sent_keys:
            blocked_rows.append(
                {
                    "record_id": record_id,
                    "statement_key": statement_key,
                    "status": "blocked",
                    "reason": "statement already sent",
                    "evidence": "statement_key exists in send-history.csv",
                    "next_step": "Do not resend unless the prior send is voided and replay is approved.",
                }
            )
            continue

        grouped[identity].append(row)

    ledger_rows: list[dict[str, str]] = []
    draft_rows: list[dict[str, str]] = []
    for (week_start, workflow_type, recipient_key), rows in sorted(grouped.items()):
        total_hours = sum(Decimal(row["hours"]) for row in rows)
        total_amount = sum(Decimal(row["amount"]) for row in rows)
        statement_key = "|".join([week_start, workflow_type, recipient_key])
        to_email = rows[0]["party_a_email"] if workflow_type == "pair_statement" else rows[0]["external_recipient_email"]
        cc_email = rows[0]["party_b_email"] if workflow_type == "pair_statement" else rows[0]["cc_email"]

        ledger_rows.append(
            {
                "statement_key": statement_key,
                "week_start": week_start,
                "workflow_type": workflow_type,
                "recipient_key": recipient_key,
                "record_count": str(len(rows)),
                "total_hours": money(total_hours),
                "total_amount": money(total_amount),
                "source_records": ";".join(row["record_id"] for row in rows),
                "status": "ready_for_email_draft",
            }
        )
        draft_rows.append(
            {
                "statement_key": statement_key,
                "to_email": to_email,
                "cc_email": cc_email,
                "draft_subject": f"Weekly statement for {week_start}",
                "draft_body": (
                    f"Statement for {week_start}: {len(rows)} records, "
                    f"{money(total_hours)} hours, ${money(total_amount)} total. "
                    f"Source records: {';'.join(row['record_id'] for row in rows)}."
                ),
                "send_status": "needs human approval",
                "evidence": "grouped from approved records; statement_key not in send-history.csv",
            }
        )

    write_csv(
        "statement-ledger.csv",
        ledger_rows,
        [
            "statement_key",
            "week_start",
            "workflow_type",
            "recipient_key",
            "record_count",
            "total_hours",
            "total_amount",
            "source_records",
            "status",
        ],
    )
    write_csv(
        "email-draft-queue.csv",
        draft_rows,
        ["statement_key", "to_email", "cc_email", "draft_subject", "draft_body", "send_status", "evidence"],
    )
    write_csv(
        "blocked-statements.csv",
        blocked_rows,
        ["record_id", "statement_key", "status", "reason", "evidence", "next_step"],
    )
    write_csv("error-log.csv", error_rows, ["record_id", "status", "reason", "evidence"])

    print(f"statement_rows={len(ledger_rows)}")
    print(f"draft_rows={len(draft_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
