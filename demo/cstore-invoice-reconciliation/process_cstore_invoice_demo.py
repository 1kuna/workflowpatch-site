#!/usr/bin/env python3
"""Generate the WorkflowPatch c-store invoice reconciliation demo outputs.

This demo uses mock data only. It models a convenience-store invoice control
path: normalize vendor names, match line items to a pricebook, block mismatches
to an exception queue, summarize invoice/store reconciliation, and keep hard
parsing or duplicate errors visible.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INVOICE_LINES = ROOT / "mock-invoice-lines.csv"
PRICEBOOK = ROOT / "pricebook.csv"
VENDOR_MAP = ROOT / "vendor-map.csv"
ACCEPTED_LEDGER = ROOT / "accepted-ledger.csv"
EXCEPTION_QUEUE = ROOT / "exception-queue.csv"
RECONCILIATION_SUMMARY = ROOT / "reconciliation-summary.csv"
ERROR_LOG = ROOT / "error-log.csv"
PROCESSED_AT = "2026-05-09T12:18:00-04:00"

ACCEPTED_FIELDS = [
    "invoice_id",
    "store_id",
    "canonical_vendor",
    "vendor_sku",
    "category",
    "quantity",
    "unit_price",
    "approved_unit_price",
    "line_total",
    "decision",
    "evidence",
    "processed_at",
]

EXCEPTION_FIELDS = [
    "invoice_id",
    "store_id",
    "observed_vendor",
    "vendor_sku",
    "issue_type",
    "review_reason",
    "evidence",
    "processed_at",
]

SUMMARY_FIELDS = [
    "invoice_id",
    "store_id",
    "canonical_vendor",
    "accepted_lines",
    "exception_lines",
    "accepted_amount",
    "exception_amount",
    "decision",
    "next_step",
    "processed_at",
]

ERROR_FIELDS = [
    "invoice_id",
    "store_id",
    "status",
    "error_message",
    "manual_review_reason",
    "processed_at",
]


@dataclass(frozen=True)
class PricebookRow:
    canonical_vendor: str
    approved_unit_price: Decimal
    category: str
    max_variance: Decimal


@dataclass(frozen=True)
class VendorRow:
    canonical_vendor: str
    account_status: str


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


def quantity_value(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid quantity: {value}") from exc


def load_pricebook(path: Path) -> dict[str, PricebookRow]:
    rows: dict[str, PricebookRow] = {}
    for row in read_rows(path):
        rows[row["vendor_sku"]] = PricebookRow(
            canonical_vendor=row["canonical_vendor"],
            approved_unit_price=decimal_value(row["approved_unit_price"], "approved_unit_price"),
            category=row["category"],
            max_variance=Decimal(row["max_variance_cents"]) / Decimal("100"),
        )
    return rows


def load_vendor_map(path: Path) -> dict[str, VendorRow]:
    rows: dict[str, VendorRow] = {}
    for row in read_rows(path):
        rows[row["observed_vendor"]] = VendorRow(
            canonical_vendor=row["canonical_vendor"],
            account_status=row["account_status"],
        )
    return rows


def exception(row: dict[str, str], issue_type: str, reason: str, evidence: str) -> dict[str, str]:
    return {
        "invoice_id": row["invoice_id"].strip(),
        "store_id": row["store_id"].strip(),
        "observed_vendor": row["observed_vendor"].strip(),
        "vendor_sku": row["vendor_sku"].strip(),
        "issue_type": issue_type,
        "review_reason": reason,
        "evidence": evidence,
        "processed_at": PROCESSED_AT,
    }


def add_summary(
    summary: dict[tuple[str, str, str], dict[str, Decimal | int]],
    row: dict[str, str],
    canonical_vendor: str,
    amount: Decimal,
    *,
    accepted: bool,
) -> None:
    key = (row["invoice_id"].strip(), row["store_id"].strip(), canonical_vendor)
    bucket = summary.setdefault(
        key,
        {
            "accepted_lines": 0,
            "exception_lines": 0,
            "accepted_amount": Decimal("0.00"),
            "exception_amount": Decimal("0.00"),
        },
    )
    if accepted:
        bucket["accepted_lines"] = int(bucket["accepted_lines"]) + 1
        bucket["accepted_amount"] = Decimal(bucket["accepted_amount"]) + amount
    else:
        bucket["exception_lines"] = int(bucket["exception_lines"]) + 1
        bucket["exception_amount"] = Decimal(bucket["exception_amount"]) + amount


def process(
    line_rows: list[dict[str, str]],
    pricebook: dict[str, PricebookRow],
    vendor_map: dict[str, VendorRow],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    accepted: list[dict[str, str]] = []
    exceptions: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    summary: dict[tuple[str, str, str], dict[str, Decimal | int]] = {}
    seen_keys: set[str] = set()

    for row in line_rows:
        invoice_id = row["invoice_id"].strip()
        store_id = row["store_id"].strip()
        sku = row["vendor_sku"].strip()
        row_key = f"{invoice_id}|{store_id}|{sku}"

        if not invoice_id or not store_id or not sku:
            errors.append(
                {
                    "invoice_id": invoice_id,
                    "store_id": store_id,
                    "status": "error",
                    "error_message": "missing invoice_id, store_id, or vendor_sku",
                    "manual_review_reason": "Row blocked because reconciliation needs a stable invoice, store, and SKU key.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        if row_key in seen_keys:
            errors.append(
                {
                    "invoice_id": invoice_id,
                    "store_id": store_id,
                    "status": "error",
                    "error_message": "duplicate invoice/store/SKU line",
                    "manual_review_reason": "Duplicate line blocked before it can double-count vendor spend.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        seen_keys.add(row_key)

        try:
            qty = quantity_value(row["quantity"])
            unit_price = decimal_value(row["unit_price"], "unit_price")
            line_total = decimal_value(row["line_total"], "line_total")
        except ValueError as exc:
            errors.append(
                {
                    "invoice_id": invoice_id,
                    "store_id": store_id,
                    "status": "error",
                    "error_message": str(exc),
                    "manual_review_reason": "Row blocked because numeric invoice fields could not be parsed safely.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue

        observed_vendor = row["observed_vendor"].strip()
        vendor = vendor_map.get(observed_vendor)
        if vendor is None or vendor.account_status == "unapproved" or not vendor.canonical_vendor:
            exceptions.append(
                exception(
                    row,
                    "unapproved_vendor",
                    "Observed vendor is not mapped to an approved canonical vendor.",
                    f"observed_vendor={observed_vendor}",
                )
            )
            add_summary(summary, row, observed_vendor or "unmapped", line_total, accepted=False)
            continue

        pricebook_row = pricebook.get(sku)
        if pricebook_row is None:
            exceptions.append(
                exception(row, "unknown_sku", "SKU is missing from the approved pricebook.", f"vendor_sku={sku}")
            )
            add_summary(summary, row, vendor.canonical_vendor, line_total, accepted=False)
            continue

        if pricebook_row.canonical_vendor != vendor.canonical_vendor:
            exceptions.append(
                exception(
                    row,
                    "vendor_sku_mismatch",
                    "SKU belongs to a different canonical vendor in the pricebook.",
                    f"observed_vendor={vendor.canonical_vendor} pricebook_vendor={pricebook_row.canonical_vendor}",
                )
            )
            add_summary(summary, row, vendor.canonical_vendor, line_total, accepted=False)
            continue

        price_delta = abs(unit_price - pricebook_row.approved_unit_price)
        if price_delta > pricebook_row.max_variance:
            exceptions.append(
                exception(
                    row,
                    "pricebook_mismatch",
                    "Invoice unit price is outside the approved variance.",
                    f"invoice={unit_price} approved={pricebook_row.approved_unit_price} variance_allowed={pricebook_row.max_variance}",
                )
            )
            add_summary(summary, row, vendor.canonical_vendor, line_total, accepted=False)
            continue

        expected_total = (qty * unit_price).quantize(Decimal("0.01"))
        if line_total != expected_total:
            exceptions.append(
                exception(
                    row,
                    "line_total_mismatch",
                    "Line total does not equal quantity times unit price.",
                    f"line_total={line_total} expected_total={expected_total}",
                )
            )
            add_summary(summary, row, vendor.canonical_vendor, line_total, accepted=False)
            continue

        accepted.append(
            {
                "invoice_id": invoice_id,
                "store_id": store_id,
                "canonical_vendor": vendor.canonical_vendor,
                "vendor_sku": sku,
                "category": pricebook_row.category,
                "quantity": str(qty),
                "unit_price": f"{unit_price:.2f}",
                "approved_unit_price": f"{pricebook_row.approved_unit_price:.2f}",
                "line_total": f"{line_total:.2f}",
                "decision": "ready_for_human_review",
                "evidence": (
                    f"vendor={vendor.canonical_vendor} price_match=true "
                    f"total_match=true source_file={row['source_file']}"
                ),
                "processed_at": PROCESSED_AT,
            }
        )
        add_summary(summary, row, vendor.canonical_vendor, line_total, accepted=True)

    summary_rows = []
    for (invoice_id, store_id, canonical_vendor), bucket in sorted(summary.items()):
        exception_lines = int(bucket["exception_lines"])
        decision = "review_exceptions_before_payment" if exception_lines else "ready_for_human_review"
        next_step = "Resolve blocked rows before payment/export." if exception_lines else "Reviewer can approve or reject."
        summary_rows.append(
            {
                "invoice_id": invoice_id,
                "store_id": store_id,
                "canonical_vendor": canonical_vendor,
                "accepted_lines": str(bucket["accepted_lines"]),
                "exception_lines": str(exception_lines),
                "accepted_amount": f"{Decimal(bucket['accepted_amount']):.2f}",
                "exception_amount": f"{Decimal(bucket['exception_amount']):.2f}",
                "decision": decision,
                "next_step": next_step,
                "processed_at": PROCESSED_AT,
            }
        )

    return accepted, exceptions, summary_rows, errors


def main() -> int:
    datetime.fromisoformat(PROCESSED_AT)
    accepted, exceptions, summary_rows, errors = process(
        read_rows(INVOICE_LINES),
        load_pricebook(PRICEBOOK),
        load_vendor_map(VENDOR_MAP),
    )
    write_rows(ACCEPTED_LEDGER, ACCEPTED_FIELDS, accepted)
    write_rows(EXCEPTION_QUEUE, EXCEPTION_FIELDS, exceptions)
    write_rows(RECONCILIATION_SUMMARY, SUMMARY_FIELDS, summary_rows)
    write_rows(ERROR_LOG, ERROR_FIELDS, errors)
    print(f"accepted_rows={len(accepted)}")
    print(f"exception_rows={len(exceptions)}")
    print(f"summary_rows={len(summary_rows)}")
    print(f"error_rows={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
