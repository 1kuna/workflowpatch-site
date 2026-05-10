#!/usr/bin/env python3
"""Generate the WorkflowPatch finance/ops handoff demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T06:08:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def money(value: str) -> int:
    try:
        return int(float(value))
    except ValueError:
        return 0


def main() -> None:
    accounts = {row["account_id"]: row for row in read_csv("account-map.csv")}
    policies = {row["destination_request"]: row for row in read_csv("destination-policy.csv")}
    events = read_csv("zoho-events.csv")

    seen_correlations: set[str] = set()
    handoff_rows: list[dict[str, str]] = []
    approval_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"]
        correlation_id = event["correlation_id"]
        if correlation_id in seen_correlations:
            exception_rows.append(
                {
                    "event_id": event_id,
                    "account_id": event["account_id"],
                    "destination_request": event["destination_request"],
                    "reason": "duplicate_correlation_id",
                    "review_action": "Confirm whether this is a replay before creating another destination artifact.",
                }
            )
            continue
        seen_correlations.add(correlation_id)

        account = accounts.get(event["account_id"])
        if account is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "unknown_account",
                    "error_detail": "Source event references an account that is not in the approved account map.",
                }
            )
            continue

        policy = policies.get(event["destination_request"])
        if policy is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "unknown_destination_request",
                    "error_detail": "No destination policy exists for this requested handoff.",
                }
            )
            continue

        if policy["allowed_without_review"] != "yes" or event["allowed_auto_write"] != "yes":
            approval_rows.append(
                {
                    "event_id": event_id,
                    "account_id": event["account_id"],
                    "account_name": account["account_name"],
                    "destination_request": event["destination_request"],
                    "reason": policy["review_reason"],
                    "finance_owner": account["finance_owner"],
                    "review_action": "Approve, narrow, or block before any destination write or customer-facing action.",
                }
            )
            continue

        if event["destination_request"] == "xero_draft_invoice" and money(event["amount"]) <= 0:
            exception_rows.append(
                {
                    "event_id": event_id,
                    "account_id": event["account_id"],
                    "destination_request": event["destination_request"],
                    "reason": "missing_invoice_amount",
                    "review_action": "Do not prepare a Xero draft until the source amount is present.",
                }
            )
            continue

        handoff_rows.append(
            {
                "event_id": event_id,
                "account_id": event["account_id"],
                "account_name": account["account_name"],
                "source_system": event["source_system"],
                "destination_output": policy["destination_output"],
                "xero_contact_id": account["xero_contact_id"],
                "drive_folder": f"{account['drive_root']}/{event['drive_folder_hint'].split('/')[-1]}",
                "crm_owner": account["crm_owner"],
                "decision": "ready_for_reviewed_handoff",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "handoff-ledger.csv",
        handoff_rows,
        [
            "event_id",
            "account_id",
            "account_name",
            "source_system",
            "destination_output",
            "xero_contact_id",
            "drive_folder",
            "crm_owner",
            "decision",
            "processed_at",
        ],
    )
    write_csv(
        "approval-queue.csv",
        approval_rows,
        ["event_id", "account_id", "account_name", "destination_request", "reason", "finance_owner", "review_action"],
    )
    write_csv(
        "exception-queue.csv",
        exception_rows,
        ["event_id", "account_id", "destination_request", "reason", "review_action"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"event_rows={len(events)}")
    print(f"handoff_rows={len(handoff_rows)}")
    print(f"approval_rows={len(approval_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
