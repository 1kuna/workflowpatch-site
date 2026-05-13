#!/usr/bin/env python3
"""Generate the WorkflowPatch member intake QA proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-13T00:56:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    events = read_csv("member-events.csv")
    policies = {row["event_type"]: row for row in read_csv("member-policy.csv")}
    seen_keys: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"]
        policy = policies.get(event["event_type"])
        if policy is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "unknown_event_type",
                    "error_detail": "No member intake policy exists for this event type.",
                }
            )
            continue

        if event["required_fields_complete"] != "yes":
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "missing_required_member_fields",
                    "error_detail": "Required profile or handoff fields are incomplete.",
                }
            )
            continue

        if event["source_boundary"] != "synthetic_or_redacted":
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "member_ref": event["member_ref"],
                    "requested_action": event["requested_action"],
                    "reason": "live_customer_channel_source",
                    "blocked_action": "Use a synthetic or redacted source row before any proof run.",
                }
            )
            continue

        if event["contains_sensitive_detail"] == "yes":
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "member_ref": event["member_ref"],
                    "requested_action": event["requested_action"],
                    "reason": "sensitive_member_detail",
                    "blocked_action": "Remove private dating, health, legal, or identity details before proof work.",
                }
            )
            continue

        if event["requested_action"] in {"send_sms_followup", "send_member_message", "book_date"}:
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "member_ref": event["member_ref"],
                    "requested_action": event["requested_action"],
                    "reason": "member_facing_action",
                    "blocked_action": "Keep member messages and date actions out of the first proof.",
                }
            )
            continue

        duplicate_key = event["duplicate_key"]
        if duplicate_key in seen_keys:
            review_rows.append(
                {
                    "event_id": event_id,
                    "member_ref": event["member_ref"],
                    "reason": "duplicate_member_event",
                    "owner": event["matchmaker_owner"],
                    "review_action": "Confirm replay intent before another profile or handoff row is staged.",
                }
            )
            continue
        seen_keys.add(duplicate_key)

        if policy["allowed_without_review"] != "yes":
            review_rows.append(
                {
                    "event_id": event_id,
                    "member_ref": event["member_ref"],
                    "reason": policy["review_reason"],
                    "owner": event["matchmaker_owner"],
                    "review_action": "Approve, narrow, or block before downstream member workflow impact.",
                }
            )
            continue

        ledger_rows.append(
            {
                "event_id": event_id,
                "member_ref": event["member_ref"],
                "event_type": event["event_type"],
                "profile_state": event["profile_state"],
                "destination_output": policy["destination_output"],
                "decision": "ready_for_owner_review",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "member-intake-qa-ledger.csv",
        ledger_rows,
        ["event_id", "member_ref", "event_type", "profile_state", "destination_output", "decision", "processed_at"],
    )
    write_csv(
        "owner-review-queue.csv",
        review_rows,
        ["event_id", "member_ref", "reason", "owner", "review_action"],
    )
    write_csv(
        "blocked-action-queue.csv",
        blocked_rows,
        ["event_id", "member_ref", "requested_action", "reason", "blocked_action"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"source_rows={len(events)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
