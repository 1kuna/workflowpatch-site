#!/usr/bin/env python3
"""Generate the WorkflowPatch producer compensation QA proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-12T20:45:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    producers = {row["producer_id"]: row for row in read_csv("producer-map.csv")}
    policies = {row["event_type"]: row for row in read_csv("compensation-policy.csv")}
    events = read_csv("source-events.csv")

    seen_correlations: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"]
        correlation_id = event["correlation_id"]

        if correlation_id in seen_correlations:
            review_rows.append(
                {
                    "event_id": event_id,
                    "producer_id": event["producer_id"],
                    "policy_id": event["policy_id"],
                    "reason": "duplicate_correlation_id",
                    "owner": "compensation-ops",
                    "review_action": "Confirm replay intent before staging another compensation row.",
                }
            )
            continue
        seen_correlations.add(correlation_id)

        producer = producers.get(event["producer_id"])
        if producer is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "unknown_producer",
                    "error_detail": "Source event references a producer that is not in the approved producer map.",
                }
            )
            continue

        policy = policies.get(event["event_type"])
        if policy is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "unknown_event_type",
                    "error_detail": "No compensation policy exists for this event type.",
                }
            )
            continue

        if event["contains_sensitive_data"] == "yes":
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "producer_id": event["producer_id"],
                    "requested_action": event["requested_action"],
                    "reason": "sensitive_data_scope",
                    "blocked_action": "Remove customer or producer-sensitive details before any proof run.",
                }
            )
            continue

        if event["requested_action"] in {"release_payout", "payment_action", "bank_change"}:
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "producer_id": event["producer_id"],
                    "requested_action": event["requested_action"],
                    "reason": "live_payout_scope",
                    "blocked_action": "Keep payout/payment action outside first proof and require written scope later.",
                }
            )
            continue

        if event["expected_upline"] != producer["approved_hierarchy_path"]:
            review_rows.append(
                {
                    "event_id": event_id,
                    "producer_id": event["producer_id"],
                    "policy_id": event["policy_id"],
                    "reason": "hierarchy_path_mismatch",
                    "owner": producer["finance_owner"],
                    "review_action": "Resolve hierarchy path before staging compensation output.",
                }
            )
            continue

        if policy["allowed_without_review"] != "yes":
            review_rows.append(
                {
                    "event_id": event_id,
                    "producer_id": event["producer_id"],
                    "policy_id": event["policy_id"],
                    "reason": policy["review_reason"],
                    "owner": producer["finance_owner"],
                    "review_action": "Approve, narrow, or block before downstream compensation impact.",
                }
            )
            continue

        ledger_rows.append(
            {
                "event_id": event_id,
                "producer_id": event["producer_id"],
                "producer_name": producer["producer_name"],
                "policy_id": event["policy_id"],
                "event_type": event["event_type"],
                "amount": event["amount"],
                "hierarchy_path": producer["approved_hierarchy_path"],
                "destination_output": policy["destination_output"],
                "decision": "ready_for_owner_review",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "compensation-qa-ledger.csv",
        ledger_rows,
        [
            "event_id",
            "producer_id",
            "producer_name",
            "policy_id",
            "event_type",
            "amount",
            "hierarchy_path",
            "destination_output",
            "decision",
            "processed_at",
        ],
    )
    write_csv(
        "owner-review-queue.csv",
        review_rows,
        ["event_id", "producer_id", "policy_id", "reason", "owner", "review_action"],
    )
    write_csv(
        "blocked-action-queue.csv",
        blocked_rows,
        ["event_id", "producer_id", "requested_action", "reason", "blocked_action"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"source_rows={len(events)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
