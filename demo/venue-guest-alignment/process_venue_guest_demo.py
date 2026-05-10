#!/usr/bin/env python3
"""Generate the WorkflowPatch venue guest alignment demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T08:36:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def yes(value: str) -> bool:
    return value.strip().lower() == "true"


def block(row: dict[str, str], reason: str, next_step: str) -> dict[str, str]:
    return {
        "event_id": row["event_id"] or "missing",
        "guest_key": row["guest_key"] or "missing",
        "reason": reason,
        "review_owner": "owner-operator",
        "next_step": next_step,
    }


def main() -> int:
    events = read_csv("source-events.csv")
    policies = {row["event_type"]: row for row in read_csv("action-policy.csv")}
    seen_replay_keys: set[str] = set()

    ledger_rows: list[dict[str, str]] = []
    action_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"].strip()
        guest_key = event["guest_key"].strip()
        event_type = event["event_type"].strip()
        replay_key = event["replay_key"].strip()

        if not event_id or not guest_key or not event_type or not replay_key:
            error_rows.append(
                {
                    "event_id": event_id or "missing",
                    "error_code": "missing_required_alignment_field",
                    "error_detail": (
                        f"guest_key={guest_key or 'missing'} "
                        f"event_type={event_type or 'missing'} replay_key={replay_key or 'missing'}"
                    ),
                }
            )
            continue

        if replay_key in seen_replay_keys:
            blocked_rows.append(block(event, "duplicate_replay_key", "Confirm whether this event already created a state or action row."))
            continue
        seen_replay_keys.add(replay_key)

        if event["sensitivity"] != "non_sensitive_ops":
            blocked_rows.append(block(event, "sensitive_guest_scope", "Use redacted non-sensitive fields before any first proof."))
            continue

        policy = policies.get(event_type)
        if policy is None:
            blocked_rows.append(block(event, "unknown_event_type", "Define the alignment rule before routing this event."))
            continue

        if event["identity_match_status"] != "matched":
            blocked_rows.append(block(event, "ambiguous_guest_match", "Resolve the Vemos/Square/Mailchimp identity match before writing state rows."))
            continue

        if event["purchase_status"] in {"refund_pending", "disputed"}:
            blocked_rows.append(block(event, "payment_state_review", "Confirm the Square payment state before any payment-affecting action."))
            continue

        if yes(policy["requires_marketing_consent"]) and not yes(event["marketing_consent"]):
            blocked_rows.append(block(event, "marketing_consent_missing", "Keep Mailchimp or customer-message actions blocked until consent is reviewed."))
            continue

        if event["mailchimp_member_status"] in {"unsubscribed", "cleaned"}:
            blocked_rows.append(block(event, "mailchimp_status_blocked", "Do not create a marketing action for unsubscribed or cleaned contacts."))
            continue

        ledger_rows.append(
            {
                "event_id": event_id,
                "guest_key": guest_key,
                "source_system": event["source_system"],
                "item_or_segment": event["item_or_segment"],
                "state_decision": policy["state_decision"],
                "airtable_status": "draft_ready",
                "processed_at": GENERATED_AT,
            }
        )
        action_rows.append(
            {
                "event_id": event_id,
                "guest_key": guest_key,
                "review_action": policy["review_action"],
                "destination": "review/action queue",
                "customer_message_status": "approval_required",
                "review_owner": policy["review_owner"],
                "draft_status": "dry_run_only",
            }
        )

    write_csv(
        "guest-state-ledger.csv",
        ledger_rows,
        ["event_id", "guest_key", "source_system", "item_or_segment", "state_decision", "airtable_status", "processed_at"],
    )
    write_csv(
        "review-action-queue.csv",
        action_rows,
        ["event_id", "guest_key", "review_action", "destination", "customer_message_status", "review_owner", "draft_status"],
    )
    write_csv("blocked-event-queue.csv", blocked_rows, ["event_id", "guest_key", "reason", "review_owner", "next_step"])
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"event_rows={len(events)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"action_rows={len(action_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
