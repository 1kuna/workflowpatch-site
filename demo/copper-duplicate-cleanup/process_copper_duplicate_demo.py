#!/usr/bin/env python3
"""Generate the WorkflowPatch Copper duplicate-cleanup demo outputs."""

from __future__ import annotations

import csv
from collections import defaultdict
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


def norm(value: str) -> str:
    return " ".join(value.strip().lower().split())


def main() -> int:
    existing = read_csv("existing-copper-records.csv")
    events = read_csv("copper-trigger-events.csv")

    by_external = {row["external_key"]: row for row in existing if row["external_key"].strip()}
    by_opportunity: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_email: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in existing:
        if row["object_type"] == "opportunity":
            by_opportunity[(norm(row["company"]), norm(row["opportunity_name"]))].append(row)
        if row["person_email"].strip():
            by_email[norm(row["person_email"])].append(row)

    seen_events: set[str] = set()
    accepted: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for row in events:
        event_id = row["event_id"]
        if event_id in seen_events:
            conflicts.append(
                {
                    "event_id": event_id,
                    "decision": "hold_duplicate_event",
                    "matched_copper_id": "",
                    "evidence": "event id already appeared in this dry run",
                    "reviewer_action": "Confirm replay behavior before any Copper write.",
                }
            )
            continue
        seen_events.add(event_id)

        if row["payload_status"] != "approved_sample":
            errors.append(
                {
                    "event_id": event_id,
                    "error": "payload is not approved for dry-run processing",
                    "evidence": f"payload_status={row['payload_status']}",
                    "blocked_at": row["updated_at"],
                }
            )
            continue

        if not row["person_email"].strip():
            conflicts.append(
                {
                    "event_id": event_id,
                    "decision": "hold_missing_email",
                    "matched_copper_id": "",
                    "evidence": f"company={row['company']} opportunity={row['opportunity_name']}",
                    "reviewer_action": "Require a match key before create or update.",
                }
            )
            continue

        candidates: list[dict[str, str]] = []
        if row["external_key"].strip() and row["external_key"] in by_external:
            candidates = [by_external[row["external_key"]]]
        elif row["object_type"] == "opportunity":
            candidates = by_opportunity[(norm(row["company"]), norm(row["opportunity_name"]))]
        else:
            candidates = by_email[norm(row["person_email"])]

        if len(candidates) > 1:
            conflicts.append(
                {
                    "event_id": event_id,
                    "decision": "hold_multiple_matches",
                    "matched_copper_id": "|".join(candidate["copper_id"] for candidate in candidates),
                    "evidence": f"{row['company']} / {row['opportunity_name'] or row['person_email']} matched multiple Copper records",
                    "reviewer_action": "Merge or select the canonical Copper record before migration.",
                }
            )
            continue

        if candidates:
            candidate = candidates[0]
            if row["object_type"] == "person" and row["stage"] == "inactive":
                conflicts.append(
                    {
                        "event_id": event_id,
                        "decision": "hold_sensitive_status_change",
                        "matched_copper_id": candidate["copper_id"],
                        "evidence": "incoming person update would change lifecycle status to inactive",
                        "reviewer_action": "Approve lifecycle/status change explicitly before update.",
                    }
                )
                continue
            accepted.append(
                {
                    "event_id": event_id,
                    "decision": "update_existing",
                    "matched_copper_id": candidate["copper_id"],
                    "write_mode": "dry_run_update",
                    "fields_to_write": "stage",
                    "blocked_fields": "owner",
                    "evidence": f"matched by {'external_key' if row['external_key'] else 'natural key'}; existing_stage={candidate['stage']} incoming_stage={row['stage']}",
                }
            )
            continue

        accepted.append(
            {
                "event_id": event_id,
                "decision": "create_new",
                "matched_copper_id": "",
                "write_mode": "dry_run_create",
                "fields_to_write": "company,person_email,opportunity_name,stage",
                "blocked_fields": "owner",
                "evidence": f"no existing Copper record matched external_key={row['external_key'] or 'missing'} email={row['person_email']}",
            }
        )

    write_csv(
        "upsert-ledger.csv",
        accepted,
        ["event_id", "decision", "matched_copper_id", "write_mode", "fields_to_write", "blocked_fields", "evidence"],
    )
    write_csv(
        "conflict-queue.csv",
        conflicts,
        ["event_id", "decision", "matched_copper_id", "evidence", "reviewer_action"],
    )
    write_csv("error-log.csv", errors, ["event_id", "error", "evidence", "blocked_at"])

    print(f"accepted_rows={len(accepted)}")
    print(f"conflict_rows={len(conflicts)}")
    print(f"error_rows={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
