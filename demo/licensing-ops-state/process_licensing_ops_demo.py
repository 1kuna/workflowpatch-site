#!/usr/bin/env python3
"""Generate the WorkflowPatch licensing ops state proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T23:18:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    events = read_csv("client-events.csv")
    policies = {row["requested_action"]: row for row in read_csv("system-policy.csv")}
    seen_correlations: set[str] = set()

    state_rows: list[dict[str, str]] = []
    approval_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    def block(row: dict[str, str], reason: str, next_step: str) -> None:
        blocked_rows.append(
            {
                "event_id": row["event_id"],
                "source_system": row["source_system"],
                "client_id": row["client_id"],
                "requested_action": row["requested_action"],
                "reason": reason,
                "next_step": next_step,
                "processed_at": GENERATED_AT,
            }
        )

    for event in events:
        event_id = event["event_id"]
        correlation_id = event["correlation_id"]

        if not event["client_id"]:
            error_rows.append(
                {
                    "event_id": event_id,
                    "source_system": event["source_system"],
                    "error_code": "missing_client_id",
                    "error_detail": "A licensing state row needs a stable client id before it can be matched or written.",
                }
            )
            continue

        if correlation_id in seen_correlations:
            block(event, "duplicate_correlation_id", "Confirm replay intent before creating another status row.")
            continue
        seen_correlations.add(correlation_id)

        policy = policies.get(event["requested_action"])
        if policy is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "source_system": event["source_system"],
                    "error_code": "unknown_action_policy",
                    "error_detail": f"No policy exists for {event['requested_action']}.",
                }
            )
            continue

        if policy["decision"] == "blocked":
            block(event, "blocked_by_policy", policy["review_reason"])
            continue

        if policy["decision"] == "review_required":
            approval_rows.append(
                {
                    "event_id": event_id,
                    "source_system": event["source_system"],
                    "client_id": event["client_id"],
                    "client_email": event["client_email"],
                    "client_name": event["client_name"],
                    "requested_action": event["requested_action"],
                    "review_reason": policy["review_reason"],
                    "operator_note": event["operator_note"],
                    "processed_at": GENERATED_AT,
                }
            )
            continue

        state_rows.append(
            {
                "event_id": event_id,
                "client_id": event["client_id"],
                "client_email": event["client_email"],
                "client_name": event["client_name"],
                "source_system": event["source_system"],
                "event_type": event["event_type"],
                "license_status": event["license_status"],
                "destination": policy["destination_queue"],
                "decision": "ready_for_reviewed_status_update",
                "decision_detail": f"Prepare {event['license_status']} licensing state from {event['source_system']} signal.",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "licensing-state-ledger.csv",
        state_rows,
        [
            "event_id",
            "client_id",
            "client_email",
            "client_name",
            "source_system",
            "event_type",
            "license_status",
            "destination",
            "decision",
            "decision_detail",
            "processed_at",
        ],
    )
    write_csv(
        "approval-review-queue.csv",
        approval_rows,
        [
            "event_id",
            "source_system",
            "client_id",
            "client_email",
            "client_name",
            "requested_action",
            "review_reason",
            "operator_note",
            "processed_at",
        ],
    )
    write_csv(
        "blocked-action-queue.csv",
        blocked_rows,
        ["event_id", "source_system", "client_id", "requested_action", "reason", "next_step", "processed_at"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "source_system", "error_code", "error_detail"])

    handoff = [
        "# Licensing Ops State Handoff",
        "",
        f"Generated: {GENERATED_AT}",
        "",
        f"- Source events: {len(events)}",
        f"- Status ledger rows: {len(state_rows)}",
        f"- Approval review rows: {len(approval_rows)}",
        f"- Blocked action rows: {len(blocked_rows)}",
        f"- Hard errors: {len(error_rows)}",
        "",
        "This proof treats licensing operations as a state-control problem. GHL, Whop, Gusto, Testimonial.io, and operator-sheet signals are normalized into reviewed ledger rows. Money movement, payroll changes, customer messages, duplicate replays, and missing client ids are held before any live account is touched.",
    ]
    (ROOT / "handoff.md").write_text("\n".join(handoff) + "\n", encoding="utf-8")

    runbook = [
        "# Licensing Ops State Runbook",
        "",
        "1. Export or receive the redacted source events.",
        "2. Confirm each event has a stable client id, email, action, and correlation id.",
        "3. Run `python3 process_licensing_ops_demo.py`.",
        "4. Review `licensing-state-ledger.csv` for status rows that are safe to prepare.",
        "5. Review `approval-review-queue.csv` before any payout, payroll, or customer-message action.",
        "6. Resolve `blocked-action-queue.csv` and `error-log.csv` before connecting live accounts.",
        "",
        "Proof boundary: no live GHL, Whop, Gusto, Testimonial.io, Sheets, email, payroll, payout, or customer-facing action is performed by this demo.",
    ]
    (ROOT / "runbook.md").write_text("\n".join(runbook) + "\n", encoding="utf-8")

    print(f"source_rows={len(events)}")
    print(f"state_rows={len(state_rows)}")
    print(f"approval_rows={len(approval_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
