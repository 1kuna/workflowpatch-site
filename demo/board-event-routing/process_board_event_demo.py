#!/usr/bin/env python3
"""Generate the WorkflowPatch board event routing proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-09T09:30:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    policies = {row["status"]: row for row in read_csv("routing-policy.csv")}
    accepted: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()

    for event in read_csv("board-events.csv"):
        event_id = event["event_id"]
        item_id = event["item_id"]
        status = event["status"]
        owner_email = event["owner_email"].strip()

        if not owner_email:
            errors.append(
                {
                    "event_id": event_id,
                    "item_id": item_id,
                    "error_code": "missing_owner_email",
                    "error_detail": "Board event is missing the owner email required for a safe review task.",
                }
            )
            continue

        if event["sensitivity"] != "non_sensitive_ops":
            review.append(
                {
                    "event_id": event_id,
                    "item_id": item_id,
                    "queue": "manual_scope_review",
                    "reason": "sensitive_data_blocked",
                    "reviewer": "ops-lead@sample.test",
                    "next_step": "Use a redacted board schema before automation access or routing.",
                    "source_status": status,
                }
            )
            continue

        policy = policies.get(status)
        if policy is None:
            review.append(
                {
                    "event_id": event_id,
                    "item_id": item_id,
                    "queue": "policy_review",
                    "reason": "no_matching_status_policy",
                    "reviewer": "ops-lead@sample.test",
                    "next_step": "Define the status rule before this item can be routed.",
                    "source_status": status,
                }
            )
            continue

        event_key = (item_id, status)
        if event_key in seen_keys:
            review.append(
                {
                    "event_id": event_id,
                    "item_id": item_id,
                    "queue": "duplicate_review",
                    "reason": "duplicate_item_status",
                    "reviewer": policy["reviewer"],
                    "next_step": "Confirm whether this is a replay before another task is created.",
                    "source_status": status,
                }
            )
            continue
        seen_keys.add(event_key)

        accepted.append(
            {
                "event_id": event_id,
                "item_id": item_id,
                "status": status,
                "destination": policy["destination"],
                "action": policy["action"],
                "reviewer": policy["reviewer"],
                "accepted_at": GENERATED_AT,
                "proof": f"{event['board_name']} -> {policy['destination']}",
            }
        )

    write_csv(
        "routing-ledger.csv",
        accepted,
        ["event_id", "item_id", "status", "destination", "action", "reviewer", "accepted_at", "proof"],
    )
    write_csv(
        "review-queue.csv",
        review,
        ["event_id", "item_id", "queue", "reason", "reviewer", "next_step", "source_status"],
    )
    write_csv("error-log.csv", errors, ["event_id", "item_id", "error_code", "error_detail"])

    print(f"event_rows={len(read_csv('board-events.csv'))}")
    print(f"accepted_rows={len(accepted)}")
    print(f"review_rows={len(review)}")
    print(f"error_rows={len(errors)}")


if __name__ == "__main__":
    main()
