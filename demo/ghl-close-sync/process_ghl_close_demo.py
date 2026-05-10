#!/usr/bin/env python3
"""Generate the WorkflowPatch GHL/Close sync demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T06:31:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    contact_rows = read_csv("contact-map.csv")
    by_close = {row["close_contact_id"]: row for row in contact_rows}
    by_ghl = {row["ghl_contact_id"]: row for row in contact_rows}
    by_email = {row["email"]: row for row in contact_rows}
    policy = {(row["field_name"], row["direction"]): row for row in read_csv("field-policy.csv")}

    seen_correlations: set[str] = set()
    sync_rows: list[dict[str, str]] = []
    conflict_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    def block(event_id: str, direction: str, reason: str, action: str) -> None:
        conflict_rows.append(
            {
                "event_id": event_id,
                "direction": direction,
                "reason": reason,
                "review_action": action,
                "processed_at": GENERATED_AT,
            }
        )

    for event in read_csv("close-appointment-events.csv"):
        event_id = event["event_id"]
        correlation_id = event["correlation_id"]
        if correlation_id in seen_correlations:
            block(event_id, "close_to_ghl", "duplicate_correlation_id", "Confirm replay intent before any CRM write.")
            continue
        seen_correlations.add(correlation_id)

        contact = by_close.get(event["close_contact_id"]) or by_email.get(event["email"])
        if contact is None:
            block(event_id, "close_to_ghl", "missing_contact_match", "Map the Close contact to a GHL contact before syncing.")
            continue

        if not event["appointment_id"] or not event["appointment_status"]:
            error_rows.append(
                {
                    "event_id": event_id,
                    "direction": "close_to_ghl",
                    "error_code": "missing_required_appointment_field",
                    "error_detail": "Appointment events need appointment_id and status for replay-safe sync.",
                }
            )
            continue

        sync_rows.append(
            {
                "event_id": event_id,
                "direction": "close_to_ghl",
                "contact_key": contact["contact_key"],
                "source_record": event["appointment_id"],
                "destination_record": contact["ghl_contact_id"],
                "field_name": "appointment_status",
                "decision": "ready_for_reviewed_ghl_update",
                "decision_detail": f"Set GHL appointment status to {event['appointment_status']} from Close event.",
                "processed_at": GENERATED_AT,
            }
        )

    for event in read_csv("ghl-contact-changes.csv"):
        event_id = event["event_id"]
        correlation_id = event["correlation_id"]
        if correlation_id in seen_correlations:
            block(event_id, "ghl_to_close", "duplicate_correlation_id", "Confirm replay intent before any CRM write.")
            continue
        seen_correlations.add(correlation_id)

        contact = by_ghl.get(event["ghl_contact_id"]) or by_email.get(event["email"])
        if contact is None:
            block(event_id, "ghl_to_close", "missing_contact_match", "Map the GHL contact to a Close contact before syncing.")
            continue

        field_name = event["field_name"]
        rule = policy.get((field_name, "ghl_to_close"))
        if rule is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "direction": "ghl_to_close",
                    "error_code": "unknown_field_policy",
                    "error_detail": f"No field policy exists for {field_name}.",
                }
            )
            continue

        if rule["winning_system"] == "review_required" or contact["contact_source_of_truth"] == "review_required":
            block(event_id, "ghl_to_close", "identity_or_source_of_truth_review", rule["review_rule"])
            continue

        sync_rows.append(
            {
                "event_id": event_id,
                "direction": "ghl_to_close",
                "contact_key": contact["contact_key"],
                "source_record": event["ghl_contact_id"],
                "destination_record": contact["close_contact_id"],
                "field_name": field_name,
                "decision": "ready_for_reviewed_close_update",
                "decision_detail": f"Set Close {field_name} to {event['new_value']} from GHL change.",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "sync-ledger.csv",
        sync_rows,
        [
            "event_id",
            "direction",
            "contact_key",
            "source_record",
            "destination_record",
            "field_name",
            "decision",
            "decision_detail",
            "processed_at",
        ],
    )
    write_csv(
        "conflict-review-queue.csv",
        conflict_rows,
        ["event_id", "direction", "reason", "review_action", "processed_at"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "direction", "error_code", "error_detail"])

    handoff = [
        "# GHL Close Sync Handoff",
        "",
        f"Generated: {GENERATED_AT}",
        "",
        f"- Close appointment events: {len(read_csv('close-appointment-events.csv'))}",
        f"- GHL contact changes: {len(read_csv('ghl-contact-changes.csv'))}",
        f"- Sync ledger rows: {len(sync_rows)}",
        f"- Conflict review rows: {len(conflict_rows)}",
        f"- Hard errors: {len(error_rows)}",
        "",
        "This proof treats two-way CRM sync as a conflict-policy problem. It requires a stable contact map, a direction-specific field policy, duplicate replay blocking, and review rows for unknown contacts or identity-field changes before any live GHL or Close write.",
    ]
    (ROOT / "handoff.md").write_text("\n".join(handoff) + "\n", encoding="utf-8")

    print(f"close_event_rows={len(read_csv('close-appointment-events.csv'))}")
    print(f"ghl_change_rows={len(read_csv('ghl-contact-changes.csv'))}")
    print(f"sync_rows={len(sync_rows)}")
    print(f"conflict_rows={len(conflict_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
