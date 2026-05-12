#!/usr/bin/env python3
"""Generate the WorkflowPatch property booking sync proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T08:46:00Z"


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
        "object_key": row["object_key"] or "missing",
        "reason": reason,
        "review_owner": "ops-lead",
        "next_step": next_step,
    }


def main() -> int:
    events = read_csv("source-events.csv")
    policies = {row["object_type"]: row for row in read_csv("sync-policy.csv")}
    seen_replay_keys: set[str] = set()

    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"].strip()
        object_key = event["object_key"].strip()
        object_type = event["object_type"].strip()
        replay_key = event["replay_key"].strip()

        if not event_id or not object_key or not object_type or not replay_key:
            error_rows.append(
                {
                    "event_id": event_id or "missing",
                    "error_code": "missing_required_sync_field",
                    "error_detail": (
                        f"object_key={object_key or 'missing'} "
                        f"object_type={object_type or 'missing'} replay_key={replay_key or 'missing'}"
                    ),
                }
            )
            continue

        if replay_key in seen_replay_keys:
            blocked_rows.append(block(event, "duplicate_replay_key", "Confirm whether this property or booking was already reviewed."))
            continue
        seen_replay_keys.add(replay_key)

        if event["sensitivity"] != "non_sensitive_ops":
            blocked_rows.append(block(event, "sensitive_property_scope", "Use redacted non-sensitive fields before any first proof."))
            continue

        policy = policies.get(object_type)
        if policy is None:
            blocked_rows.append(block(event, "unknown_object_type", "Define the Airtable and HubSpot handling rule before sync review."))
            continue

        if event["identity_match_status"] != "matched":
            blocked_rows.append(block(event, "ambiguous_property_or_booking_match", "Resolve the Airtable and HubSpot identity match before state or sync rows."))
            continue

        if yes(policy["blocks_private_owner"]) and event["owner_visibility"] == "owner_private":
            blocked_rows.append(block(event, "owner_visibility_review", "Keep private owner fields out of the first proof and request a redacted sample."))
            continue

        if yes(policy["requires_contract_clear"]) and event["contract_status"] not in {"contract_ready", "contract_signed"}:
            exception_rows.append(
                {
                    "event_id": event_id,
                    "object_key": object_key,
                    "exception_type": "contract_state_review",
                    "detail": f"contract_status={event['contract_status']}",
                    "next_step": "Confirm the contract state before any Airtable or HubSpot sync decision.",
                }
            )
            blocked_rows.append(block(event, "contract_state_review", "Confirm contract status before sync review."))
            continue

        if yes(policy["requires_payment_clear"]) and event["payment_status"] in {"disputed", "refund_pending"}:
            exception_rows.append(
                {
                    "event_id": event_id,
                    "object_key": object_key,
                    "exception_type": "payment_state_review",
                    "detail": f"payment_status={event['payment_status']}",
                    "next_step": "Confirm payment state before any payment-affecting or guest-facing action.",
                }
            )
            blocked_rows.append(block(event, "payment_state_review", "Confirm payment status before sync review."))
            continue

        ledger_rows.append(
            {
                "event_id": event_id,
                "object_key": object_key,
                "object_type": object_type,
                "source_system": event["source_system"],
                "state_decision": policy["state_decision"],
                "airtable_status": "draft_ready",
                "processed_at": GENERATED_AT,
            }
        )
        review_rows.append(
            {
                "event_id": event_id,
                "object_key": object_key,
                "hubspot_record": event["hubspot_record"],
                "sync_direction": event["sync_direction"],
                "review_action": policy["hubspot_review_action"],
                "write_status": "review_required",
            }
        )

    write_csv(
        "property-state-ledger.csv",
        ledger_rows,
        ["event_id", "object_key", "object_type", "source_system", "state_decision", "airtable_status", "processed_at"],
    )
    write_csv(
        "hubspot-sync-review.csv",
        review_rows,
        ["event_id", "object_key", "hubspot_record", "sync_direction", "review_action", "write_status"],
    )
    write_csv(
        "contract-payment-exception-log.csv",
        exception_rows,
        ["event_id", "object_key", "exception_type", "detail", "next_step"],
    )
    write_csv("blocked-sync-queue.csv", blocked_rows, ["event_id", "object_key", "reason", "review_owner", "next_step"])
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"event_rows={len(events)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
