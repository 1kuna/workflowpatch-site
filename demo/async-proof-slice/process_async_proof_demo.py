#!/usr/bin/env python3
"""Generate the WorkflowPatch async proof-slice demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T06:13:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    briefs = {row["brief_id"]: row for row in read_csv("workflow-briefs.csv")}
    events = read_csv("sample-events.csv")
    seen_correlations: set[str] = set()
    status_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"]
        brief = briefs.get(event["brief_id"])
        if brief is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "unknown_brief",
                    "error_detail": "Sample event references a workflow brief that is not registered.",
                }
            )
            continue

        correlation_id = event["correlation_id"]
        if correlation_id in seen_correlations:
            review_rows.append(
                {
                    "event_id": event_id,
                    "brief_id": event["brief_id"],
                    "workflow_name": brief["workflow_name"],
                    "reason": "duplicate_correlation_id",
                    "review_action": "Confirm replay intent before any destination write.",
                }
            )
            continue
        seen_correlations.add(correlation_id)

        if not event["owner_email"] or not event["destination_key"]:
            review_rows.append(
                {
                    "event_id": event_id,
                    "brief_id": event["brief_id"],
                    "workflow_name": brief["workflow_name"],
                    "reason": "missing_owner_or_destination",
                    "review_action": brief["blocked_definition"],
                }
            )
            continue

        if float(event["confidence"]) < 0.80:
            review_rows.append(
                {
                    "event_id": event_id,
                    "brief_id": event["brief_id"],
                    "workflow_name": brief["workflow_name"],
                    "reason": "low_confidence_or_unsupported_output",
                    "review_action": brief["blocked_definition"],
                }
            )
            continue

        status_rows.append(
            {
                "event_id": event_id,
                "brief_id": event["brief_id"],
                "workflow_name": brief["workflow_name"],
                "source_record_id": event["source_record_id"],
                "destination_system": brief["destination_system"],
                "destination_key": event["destination_key"],
                "decision": "ready_for_reviewed_delivery",
                "status_note": f"{brief['workflow_name']}: source {event['source_record_id']} passed validation for {brief['destination_system']}.",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "status-ledger.csv",
        status_rows,
        [
            "event_id",
            "brief_id",
            "workflow_name",
            "source_record_id",
            "destination_system",
            "destination_key",
            "decision",
            "status_note",
            "processed_at",
        ],
    )
    write_csv("review-queue.csv", review_rows, ["event_id", "brief_id", "workflow_name", "reason", "review_action"])
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    update_lines = [
        "# Sample Written Status Update",
        "",
        f"Generated: {GENERATED_AT}",
        "",
        f"- Ready rows: {len(status_rows)}",
        f"- Review rows: {len(review_rows)}",
        f"- Hard errors: {len(error_rows)}",
        "",
        "The proof slice accepted only rows with a registered brief, unique correlation id, owner, destination key, and sufficient confidence. Review rows are visible before any live destination write.",
    ]
    (ROOT / "status-update.md").write_text("\n".join(update_lines) + "\n", encoding="utf-8")

    print(f"event_rows={len(events)}")
    print(f"status_rows={len(status_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
