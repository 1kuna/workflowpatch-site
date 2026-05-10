#!/usr/bin/env python3
"""Generate the WorkflowPatch workflow reliability ledger demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "event_id",
    "workflow_name",
    "client_context",
    "source_system",
    "trigger_type",
    "destination",
    "duplicate_key",
)


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_yes(row: dict[str, str], field: str) -> bool:
    return row.get(field, "").strip().lower() == "yes"


def confidence(row: dict[str, str]) -> float:
    try:
        return float(row.get("confidence", "0") or "0")
    except ValueError:
        return 0.0


def classify(row: dict[str, str], seen_keys: set[str]) -> tuple[str, str, str]:
    missing = [field for field in REQUIRED if not row.get(field)]
    if missing:
        return "error", "hard_error", f"missing required fields: {', '.join(missing)}"

    duplicate_key = row["duplicate_key"]
    if duplicate_key in seen_keys:
        return "blocked", "duplicate", "duplicate retry event already processed"
    seen_keys.add(duplicate_key)

    if not is_yes(row, "approved_source"):
        return "blocked", "source_boundary", "source is not approved for first proof"
    if is_yes(row, "contains_sensitive_data"):
        return "blocked", "sensitive_data", "sensitive customer or client data present"
    if is_yes(row, "external_message") or is_yes(row, "production_write"):
        return "blocked", "live_action", "live customer message or production write requested"
    if confidence(row) < 0.80:
        return "review", "low_confidence", "low reliability confidence"

    missing_reliability = [
        label
        for field, label in (
            ("has_input_contract", "input contract"),
            ("has_retry_policy", "retry policy"),
            ("has_error_notification", "error notification"),
            ("has_monitoring_field", "monitoring field"),
        )
        if not is_yes(row, field)
    ]
    if missing_reliability:
        return "review", "reliability_gap", "missing " + ", ".join(missing_reliability)

    return "accepted", "ready", "ready for reliability proof"


def main() -> None:
    events = read_csv("workflow-events.csv")
    seen_keys: set[str] = set()
    reliability_rows: list[dict[str, str]] = []
    monitoring_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in events:
        decision, reason_code, reason = classify(row, seen_keys)
        if decision == "error":
            error_rows.append({"event_id": row.get("event_id", ""), "error": reason})
            continue

        reliability_rows.append(
            {
                "event_id": row["event_id"],
                "workflow_name": row["workflow_name"],
                "source_system": row["source_system"],
                "destination": row["destination"],
                "decision": decision,
                "reason_code": reason_code,
                "reason": reason,
            }
        )

        if decision == "accepted":
            monitoring_rows.append(
                {
                    "event_id": row["event_id"],
                    "workflow_name": row["workflow_name"],
                    "monitoring_status": "ready_for_dry_run_monitoring",
                    "alert_owner": "human operator",
                    "handoff": "include input contract, retry policy, error notification, and rollback note",
                }
            )
        elif decision == "review":
            review_rows.append(
                {
                    "event_id": row["event_id"],
                    "review_reason": reason,
                    "safe_next_step": "fill reliability gap before any client workflow goes live",
                    "no_live_action": "true",
                }
            )
        elif decision == "blocked":
            blocked_rows.append(
                {
                    "event_id": row["event_id"],
                    "block_reason": reason,
                    "safe_boundary": "use redacted data and written approval before promotion",
                }
            )

    write_csv(
        "reliability-ledger.csv",
        ["event_id", "workflow_name", "source_system", "destination", "decision", "reason_code", "reason"],
        reliability_rows,
    )
    write_csv(
        "monitoring-ledger.csv",
        ["event_id", "workflow_name", "monitoring_status", "alert_owner", "handoff"],
        monitoring_rows,
    )
    write_csv(
        "fallback-review-queue.csv",
        ["event_id", "review_reason", "safe_next_step", "no_live_action"],
        review_rows,
    )
    write_csv("blocked-action-queue.csv", ["event_id", "block_reason", "safe_boundary"], blocked_rows)
    write_csv("error-log.csv", ["event_id", "error"], error_rows)
    print(
        f"event_rows={len(events)} "
        f"ledger_rows={len(reliability_rows)} "
        f"monitoring_rows={len(monitoring_rows)} "
        f"review_rows={len(review_rows)} "
        f"blocked_rows={len(blocked_rows)} "
        f"error_rows={len(error_rows)}"
    )


if __name__ == "__main__":
    main()
