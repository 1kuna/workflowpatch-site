#!/usr/bin/env python3
"""Generate the WorkflowPatch home-service selections demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def write_csv(name: str, rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError(f"{name} has no rows")
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ledger_rows = [
        {
            "ledger_id": "LED-1001",
            "submission_id": "SUB-1001",
            "project_id": "PRJ-501",
            "brand": "Watermark Design Build",
            "item_code": "TILE-12X24-OAK",
            "quantity": "180",
            "decision": "accepted",
            "status_after": "proposed",
            "reason": "catalog item active and room allowed",
            "next_queue": "selection approval review",
        },
        {
            "ledger_id": "LED-1002",
            "submission_id": "SUB-1002",
            "project_id": "PRJ-501",
            "brand": "Watermark Design Build",
            "item_code": "CAB-SHAKER-WHITE",
            "quantity": "22",
            "decision": "accepted",
            "status_after": "approved",
            "reason": "catalog item active and room allowed",
            "next_queue": "vendor order draft queue",
        },
        {
            "ledger_id": "LED-1004",
            "submission_id": "SUB-1004",
            "project_id": "PRJ-502",
            "brand": "Manolo Roofing",
            "item_code": "FIXTURE-MATTE-BLK",
            "quantity": "3",
            "decision": "accepted_with_warning",
            "status_after": "approved",
            "reason": "catalog item active but vendor lead time flagged",
            "next_queue": "vendor order draft queue",
        },
    ]

    order_rows = [
        {
            "draft_id": "ORD-2001",
            "submission_id": "SUB-1002",
            "project_id": "PRJ-501",
            "vendor": "Bay Cabinet Supply",
            "item_code": "CAB-SHAKER-WHITE",
            "quantity": "22",
            "unit": "linear_ft",
            "approval_required": "yes",
            "send_state": "draft_only",
        },
        {
            "draft_id": "ORD-2002",
            "submission_id": "SUB-1004",
            "project_id": "PRJ-502",
            "vendor": "Fixture House",
            "item_code": "FIXTURE-MATTE-BLK",
            "quantity": "3",
            "unit": "each",
            "approval_required": "yes",
            "send_state": "draft_only",
        },
    ]

    exception_rows = [
        {
            "error_id": "ERR-3001",
            "submission_id": "SUB-1003",
            "severity": "review",
            "blocked_reason": "catalog item is on phase 2 hold",
            "next_step": "confirm phase approval before vendor draft",
        },
        {
            "error_id": "ERR-3002",
            "submission_id": "SUB-1005",
            "severity": "error",
            "blocked_reason": "unknown project id",
            "next_step": "map or create project before ledger write",
        },
        {
            "error_id": "ERR-3003",
            "submission_id": "SUB-1006",
            "severity": "error",
            "blocked_reason": "unknown item code",
            "next_step": "add catalog item or choose an active approved item",
        },
        {
            "error_id": "ERR-3004",
            "submission_id": "SUB-1007",
            "severity": "review",
            "blocked_reason": "project is paused",
            "next_step": "unblock only after project returns to active state",
        },
    ]

    write_csv("project-selection-ledger.csv", ledger_rows)
    write_csv("vendor-order-draft-queue.csv", order_rows)
    write_csv("exception-log.csv", exception_rows)


if __name__ == "__main__":
    main()
