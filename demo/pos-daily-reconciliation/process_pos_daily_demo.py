#!/usr/bin/env python3
"""Generate the WorkflowPatch POS daily reconciliation proof outputs.

This demo uses mock data only. It models the first useful slice for a
restaurant POS reporting repair: group Toast item rows by business date,
revenue center, service window, and category; block unknown or malformed rows;
guard duplicate replays; and compare calculated totals with a daily summary.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ORDER_ITEMS = ROOT / "pos-order-items.csv"
CATEGORY_MAP = ROOT / "category-map.csv"
DAILY_SUMMARY = ROOT / "toast-daily-summary.csv"
SUMMARY_LEDGER = ROOT / "summary-ledger.csv"
RECONCILIATION_REPORT = ROOT / "reconciliation-report.csv"
BLOCKED_QUEUE = ROOT / "blocked-row-queue.csv"
ERROR_LOG = ROOT / "error-log.csv"
PROCESSED_AT = "2026-05-11T08:03:00-04:00"

SUMMARY_FIELDS = [
    "business_date",
    "revenue_center",
    "time_bucket",
    "reporting_category",
    "calculated_total",
    "item_count",
    "source_rows",
    "summary_key",
    "decision",
    "evidence",
    "processed_at",
]

RECONCILIATION_FIELDS = [
    "business_date",
    "revenue_center",
    "time_bucket",
    "reporting_category",
    "expected_total",
    "calculated_total",
    "variance",
    "decision",
    "next_step",
    "processed_at",
]

BLOCKED_FIELDS = [
    "order_item_id",
    "business_date",
    "revenue_center",
    "toast_guid",
    "issue_type",
    "review_reason",
    "evidence",
    "processed_at",
]

ERROR_FIELDS = [
    "order_item_id",
    "source_run_id",
    "status",
    "error_message",
    "manual_review_reason",
    "processed_at",
]


@dataclass(frozen=True)
class CategoryRule:
    sales_category: str
    reporting_category: str
    active: bool


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decimal_value(value: str, label: str) -> Decimal:
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"invalid {label}: {value}") from exc


def load_category_map(path: Path) -> dict[str, CategoryRule]:
    rules: dict[str, CategoryRule] = {}
    for row in read_rows(path):
        rules[row["toast_guid"]] = CategoryRule(
            sales_category=row["sales_category"],
            reporting_category=row["reporting_category"],
            active=row["active"].strip().lower() == "true",
        )
    return rules


def load_expected(path: Path) -> dict[tuple[str, str, str, str], Decimal]:
    expected: dict[tuple[str, str, str, str], Decimal] = {}
    for row in read_rows(path):
        key = (
            row["business_date"],
            row["revenue_center"],
            row["time_bucket"],
            row["reporting_category"],
        )
        expected[key] = decimal_value(row["expected_total"], "expected_total")
    return expected


def service_window(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp)
    return "Lunch" if parsed.timetz().replace(tzinfo=None) < time(16, 0) else "Dinner"


def blocked(row: dict[str, str], issue_type: str, reason: str, evidence: str) -> dict[str, str]:
    return {
        "order_item_id": row["order_item_id"].strip(),
        "business_date": row["business_date"].strip(),
        "revenue_center": row["revenue_center"].strip(),
        "toast_guid": row["toast_guid"].strip(),
        "issue_type": issue_type,
        "review_reason": reason,
        "evidence": evidence,
        "processed_at": PROCESSED_AT,
    }


def process(
    order_rows: list[dict[str, str]],
    category_rules: dict[str, CategoryRule],
    expected: dict[tuple[str, str, str, str], Decimal],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    groups: dict[tuple[str, str, str, str], dict[str, Decimal | int | list[str]]] = {}
    blocked_rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    seen_item_ids: set[str] = set()

    for row in order_rows:
        order_item_id = row["order_item_id"].strip()
        source_run_id = row["source_run_id"].strip()
        if not order_item_id or not row["business_date"].strip() or not row["revenue_center"].strip():
            errors.append(
                {
                    "order_item_id": order_item_id,
                    "source_run_id": source_run_id,
                    "status": "error",
                    "error_message": "missing order_item_id, business_date, or revenue_center",
                    "manual_review_reason": "Row blocked because daily reconciliation needs stable item, date, and revenue-center keys.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        if order_item_id in seen_item_ids:
            errors.append(
                {
                    "order_item_id": order_item_id,
                    "source_run_id": source_run_id,
                    "status": "error",
                    "error_message": "duplicate order_item_id from replay or partial run",
                    "manual_review_reason": "Duplicate item blocked before it can inflate a daily sales bucket.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        seen_item_ids.add(order_item_id)

        toast_guid = row["toast_guid"].strip()
        rule = category_rules.get(toast_guid)
        if rule is None or not rule.active:
            blocked_rows.append(
                blocked(
                    row,
                    "unknown_category_guid",
                    "Toast GUID is missing from the active category map.",
                    f"toast_guid={toast_guid} source_file={row['source_file']}",
                )
            )
            continue

        try:
            net_sales = decimal_value(row["net_sales"], "net_sales")
            bucket = service_window(row["ordered_at"].strip())
        except (ValueError, TypeError) as exc:
            errors.append(
                {
                    "order_item_id": order_item_id,
                    "source_run_id": source_run_id,
                    "status": "error",
                    "error_message": str(exc),
                    "manual_review_reason": "Row blocked because amount or timestamp could not be parsed safely.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue

        key = (row["business_date"].strip(), row["revenue_center"].strip(), bucket, rule.reporting_category)
        group = groups.setdefault(key, {"calculated_total": Decimal("0.00"), "item_count": 0, "source_rows": []})
        group["calculated_total"] = Decimal(group["calculated_total"]) + net_sales
        group["item_count"] = int(group["item_count"]) + 1
        source_rows = list(group["source_rows"])
        source_rows.append(order_item_id)
        group["source_rows"] = source_rows

    summary_rows: list[dict[str, str]] = []
    reconciliation_rows: list[dict[str, str]] = []
    for key, group in sorted(groups.items()):
        business_date, revenue_center, time_bucket, reporting_category = key
        calculated_total = Decimal(group["calculated_total"]).quantize(Decimal("0.01"))
        expected_total = expected.get(key)
        variance = calculated_total - expected_total if expected_total is not None else calculated_total
        decision = "ready_for_human_review" if expected_total is not None and variance == 0 else "review_variance"
        next_step = "Reviewer can approve the summary row." if decision == "ready_for_human_review" else "Compare source Toast summary and blocked rows before Sheets update."
        summary_key = "|".join(key)
        source_rows_text = ";".join(group["source_rows"])
        summary_rows.append(
            {
                "business_date": business_date,
                "revenue_center": revenue_center,
                "time_bucket": time_bucket,
                "reporting_category": reporting_category,
                "calculated_total": f"{calculated_total:.2f}",
                "item_count": str(group["item_count"]),
                "source_rows": source_rows_text,
                "summary_key": summary_key,
                "decision": decision,
                "evidence": f"source_rows={source_rows_text} duplicate_guard=true",
                "processed_at": PROCESSED_AT,
            }
        )
        reconciliation_rows.append(
            {
                "business_date": business_date,
                "revenue_center": revenue_center,
                "time_bucket": time_bucket,
                "reporting_category": reporting_category,
                "expected_total": f"{expected_total:.2f}" if expected_total is not None else "missing",
                "calculated_total": f"{calculated_total:.2f}",
                "variance": f"{variance:.2f}",
                "decision": decision,
                "next_step": next_step,
                "processed_at": PROCESSED_AT,
            }
        )

    for key, expected_total in sorted(expected.items()):
        if key in groups:
            continue
        business_date, revenue_center, time_bucket, reporting_category = key
        reconciliation_rows.append(
            {
                "business_date": business_date,
                "revenue_center": revenue_center,
                "time_bucket": time_bucket,
                "reporting_category": reporting_category,
                "expected_total": f"{expected_total:.2f}",
                "calculated_total": "0.00",
                "variance": f"{-expected_total:.2f}",
                "decision": "missing_source_rows",
                "next_step": "Investigate whether Toast export was partial or category mapping filtered rows out.",
                "processed_at": PROCESSED_AT,
            }
        )

    return summary_rows, reconciliation_rows, blocked_rows, errors


def main() -> int:
    datetime.fromisoformat(PROCESSED_AT)
    summary_rows, reconciliation_rows, blocked_rows, errors = process(
        read_rows(ORDER_ITEMS),
        load_category_map(CATEGORY_MAP),
        load_expected(DAILY_SUMMARY),
    )
    write_rows(SUMMARY_LEDGER, SUMMARY_FIELDS, summary_rows)
    write_rows(RECONCILIATION_REPORT, RECONCILIATION_FIELDS, reconciliation_rows)
    write_rows(BLOCKED_QUEUE, BLOCKED_FIELDS, blocked_rows)
    write_rows(ERROR_LOG, ERROR_FIELDS, errors)
    print(f"summary_rows={len(summary_rows)}")
    print(f"reconciliation_rows={len(reconciliation_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
