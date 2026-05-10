#!/usr/bin/env python3
"""Generate the WorkflowPatch program ops KPI demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T09:08:00Z"


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
        "site_key": row["site_key"] or "missing",
        "program_week": row["program_week"] or "missing",
        "reason": reason,
        "review_owner": "program-ops",
        "next_step": next_step,
    }


def exception(row: dict[str, str], reason: str, detail: str, next_step: str) -> dict[str, str]:
    return {
        "event_id": row["event_id"],
        "site_key": row["site_key"],
        "program_week": row["program_week"],
        "exception_type": reason,
        "detail": detail,
        "next_step": next_step,
    }


def main() -> int:
    events = read_csv("source-events.csv")
    policies = {row["event_type"]: row for row in read_csv("program-policy.csv")}
    seen_replay_keys: set[str] = set()

    ledger_rows: list[dict[str, str]] = []
    kpi_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"].strip()
        site_key = event["site_key"].strip()
        program_week = event["program_week"].strip()
        event_type = event["event_type"].strip()
        replay_key = event["replay_key"].strip()

        if not event_id or not site_key or not program_week or not event_type or not replay_key:
            error_rows.append(
                {
                    "event_id": event_id or "missing",
                    "error_code": "missing_required_program_field",
                    "error_detail": (
                        f"site_key={site_key or 'missing'} "
                        f"program_week={program_week or 'missing'} "
                        f"event_type={event_type or 'missing'} "
                        f"replay_key={replay_key or 'missing'}"
                    ),
                }
            )
            continue

        if replay_key in seen_replay_keys:
            blocked_rows.append(block(event, "duplicate_replay_key", "Confirm whether this site-week row already created a program ledger entry."))
            continue
        seen_replay_keys.add(replay_key)

        if event["sensitivity"] != "non_sensitive_ops":
            blocked_rows.append(block(event, "child_family_scope", "Use synthetic or redacted non-sensitive rows before any first proof."))
            continue

        policy = policies.get(event_type)
        if policy is None:
            blocked_rows.append(block(event, "unknown_program_event_type", "Define the attendance, staffing, or KPI rule before routing this source."))
            continue

        if event["identity_match_status"] != "matched":
            blocked_rows.append(block(event, "site_week_unmapped", "Map the source row to one site and program week before KPI output."))
            continue

        if event["manual_override"] == "true":
            exception_rows.append(exception(event, "manual_override_required", "manual_override=true", "Confirm the intended program-ops handling before ledger output."))
            continue

        if yes(policy["requires_attendance_present"]) and event["attendance_state"] != "attendance_present":
            exception_rows.append(
                exception(
                    event,
                    "missing_attendance_rows",
                    f"attendance_state={event['attendance_state']}",
                    "Confirm attendance source completeness before KPI output.",
                )
            )
            continue

        if yes(policy["requires_staffing_clear"]) and event["staffing_state"] != "staffing_clear":
            exception_rows.append(
                exception(
                    event,
                    "staffing_coverage_gap",
                    f"staffing_state={event['staffing_state']}",
                    "Route coverage gap to program ops before reporting.",
                )
            )
            continue

        ledger_rows.append(
            {
                "event_id": event_id,
                "site_key": site_key,
                "program_week": program_week,
                "source_system": event["source_system"],
                "ledger_decision": policy["ledger_decision"],
                "row_owner": event["row_owner"],
                "processed_at": GENERATED_AT,
            }
        )
        kpi_rows.append(
            {
                "event_id": event_id,
                "site_key": site_key,
                "program_week": program_week,
                "kpi_action": policy["kpi_action"],
                "kpi_status": "dry_run_ready",
                "reporting_boundary": "internal_review_only",
            }
        )

    write_csv(
        "program-ledger.csv",
        ledger_rows,
        ["event_id", "site_key", "program_week", "source_system", "ledger_decision", "row_owner", "processed_at"],
    )
    write_csv(
        "kpi-output.csv",
        kpi_rows,
        ["event_id", "site_key", "program_week", "kpi_action", "kpi_status", "reporting_boundary"],
    )
    write_csv(
        "exception-queue.csv",
        exception_rows,
        ["event_id", "site_key", "program_week", "exception_type", "detail", "next_step"],
    )
    write_csv(
        "blocked-event-queue.csv",
        blocked_rows,
        ["event_id", "site_key", "program_week", "reason", "review_owner", "next_step"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"event_rows={len(events)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"kpi_rows={len(kpi_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
