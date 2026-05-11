#!/usr/bin/env python3
"""Generate the WorkflowPatch n8n crash triage proof outputs.

The proof is intentionally local and synthetic. It models the first safe proof
slice for a self-hosted n8n stability incident: triage evidence before any live
database migration or credential movement.
"""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_rows(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_triage_rows(signals: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, signal in enumerate(signals, start=1):
        metric = signal["metric"]
        status = "review"
        diagnosis = "Needs operator review"
        action = "Add evidence before changing production"

        if metric == "restarts":
            diagnosis = "Restart storm during webhook burst"
            action = "Freeze workflow edits and collect container logs before any migration"
        elif metric == "execution_table_rows":
            diagnosis = "Execution table bloat is a likely database-lock source"
            action = "Measure table sizes and slow queries; define pruning window"
        elif metric == "queue_mode":
            status = "ready"
            diagnosis = "Queue mode is missing from the current architecture"
            action = "Prepare main/webhook/worker split plan with Redis/Postgres dependencies"
        elif metric == "last_restore_test_days":
            status = "blocked"
            diagnosis = "Restore path is unproven"
            action = "Run a restore rehearsal on a disposable target before touching production"
        elif metric == "credential_export_requested":
            status = "blocked"
            diagnosis = "Credential export is not needed for first proof"
            action = "Keep credentials in owner-controlled account and document access boundaries"
        elif metric == "lost_workflow_changes_days":
            diagnosis = "Workflow-change loss already happened"
            action = "Add workflow JSON export and commit-style snapshot before cutover"
        elif metric == "avg_execution_insert_ms":
            diagnosis = "Slow execution inserts support the MySQL bottleneck hypothesis"
            action = "Verify with slow-query samples and execution retention counts"
        elif metric == "executions_pruning_age_days":
            status = "ready"
            diagnosis = "Execution retention is too long for high-volume workflows"
            action = "Propose save-on-error and max-age pruning after backup proof"

        rows.append(
            {
                "triage_id": f"TRI-{1000 + index}",
                "signal_id": signal["signal_id"],
                "status": status,
                "diagnosis": diagnosis,
                "next_action": action,
                "approval_required": "true",
            }
        )
    return rows


def main() -> int:
    signals = read_rows("incident-signals.csv")
    triage_rows = build_triage_rows(signals)
    write_rows(
        "triage-ledger.csv",
        triage_rows,
        ["triage_id", "signal_id", "status", "diagnosis", "next_action", "approval_required"],
    )

    blocked_rows = [row for row in triage_rows if row["status"] == "blocked"]
    review_rows = [row for row in triage_rows if row["status"] == "review"]
    print(f"signal_rows={len(signals)}")
    print(f"triage_rows={len(triage_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
