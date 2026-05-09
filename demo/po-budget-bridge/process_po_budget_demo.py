#!/usr/bin/env python3
"""Generate the WorkflowPatch PO/budget bridge demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-09T14:25:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def money(value: str) -> int:
    try:
        return int(float(value))
    except ValueError:
        return 0


def main() -> None:
    projects = {row["project_code"]: row for row in read_csv("projects.csv")}
    purchase_orders = {row["po_id"]: row for row in read_csv("airtable-purchase-orders.csv")}
    expenses = read_csv("sheet-expense-rows.csv")

    bridge_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for expense in expenses:
        row_id = expense["row_id"]
        project = projects.get(expense["project_code"])
        if project is None:
            error_rows.append(
                {
                    "row_id": row_id,
                    "error_code": "unknown_project",
                    "error_detail": "Budget sheet row references a project that is not in the Airtable project table.",
                }
            )
            continue
        if project["budget_sheet_id"] != expense["sheet_id"]:
            exception_rows.append(
                {
                    "row_id": row_id,
                    "project_code": expense["project_code"],
                    "po_id": expense["entered_po_id"],
                    "reason": "wrong_budget_sheet",
                    "review_action": "Confirm the project sheet before syncing this expense.",
                }
            )
            continue
        if project["project_status"] != "active":
            exception_rows.append(
                {
                    "row_id": row_id,
                    "project_code": expense["project_code"],
                    "po_id": expense["entered_po_id"],
                    "reason": "project_not_active",
                    "review_action": "Review paused project before accepting new budget activity.",
                }
            )
            continue

        po = purchase_orders.get(expense["entered_po_id"])
        if po is None:
            exception_rows.append(
                {
                    "row_id": row_id,
                    "project_code": expense["project_code"],
                    "po_id": expense["entered_po_id"],
                    "reason": "po_not_found",
                    "review_action": "Create, correct, or reject the PO reference before syncing.",
                }
            )
            continue
        if po["project_code"] != expense["project_code"]:
            exception_rows.append(
                {
                    "row_id": row_id,
                    "project_code": expense["project_code"],
                    "po_id": expense["entered_po_id"],
                    "reason": "po_project_mismatch",
                    "review_action": "PO belongs to another project; block sync until corrected.",
                }
            )
            continue
        if po["po_status"] != "approved":
            exception_rows.append(
                {
                    "row_id": row_id,
                    "project_code": expense["project_code"],
                    "po_id": expense["entered_po_id"],
                    "reason": "po_not_approved",
                    "review_action": "Do not sync expense against cancelled or unapproved PO.",
                }
            )
            continue
        if po["budget_code"] != expense["budget_code"]:
            exception_rows.append(
                {
                    "row_id": row_id,
                    "project_code": expense["project_code"],
                    "po_id": expense["entered_po_id"],
                    "reason": "budget_code_mismatch",
                    "review_action": "Confirm whether the budget code or PO coding is wrong.",
                }
            )
            continue
        if money(expense["expense_amount"]) > money(po["approved_amount"]):
            exception_rows.append(
                {
                    "row_id": row_id,
                    "project_code": expense["project_code"],
                    "po_id": expense["entered_po_id"],
                    "reason": "expense_over_po_amount",
                    "review_action": "Approve change order or reduce expense before syncing.",
                }
            )
            continue

        bridge_rows.append(
            {
                "row_id": row_id,
                "project_code": expense["project_code"],
                "sheet_id": expense["sheet_id"],
                "po_id": expense["entered_po_id"],
                "vendor": po["vendor"],
                "budget_code": expense["budget_code"],
                "expense_amount": expense["expense_amount"],
                "decision": "sync_ready",
                "destination_update": "Airtable expense ledger and budget-sheet status cell",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "bridge-ledger.csv",
        bridge_rows,
        [
            "row_id",
            "project_code",
            "sheet_id",
            "po_id",
            "vendor",
            "budget_code",
            "expense_amount",
            "decision",
            "destination_update",
            "processed_at",
        ],
    )
    write_csv(
        "exception-queue.csv",
        exception_rows,
        ["row_id", "project_code", "po_id", "reason", "review_action"],
    )
    write_csv("error-log.csv", error_rows, ["row_id", "error_code", "error_detail"])

    print(f"project_rows={len(projects)}")
    print(f"po_rows={len(purchase_orders)}")
    print(f"expense_rows={len(expenses)}")
    print(f"bridge_rows={len(bridge_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
