#!/usr/bin/env python3
"""Generate the WorkflowPatch invoice exception proof outputs.

This demo uses mock data only. It models a small finance-ops safety pattern:
accept rows only when the invoice id is stable, the SKU is known, the unit
price matches the pricebook, the line total reconciles, and the PO prefix fits.
Everything else goes to a visible exception queue or error log.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INVOICES = ROOT / "mock-invoices.csv"
PRICEBOOK = ROOT / "pricebook.csv"
ACCEPTED_LEDGER = ROOT / "accepted-ledger.csv"
EXCEPTION_QUEUE = ROOT / "exception-queue.csv"
ERROR_LOG = ROOT / "error-log.csv"
PROCESSED_AT = "2026-05-09T02:05:00-04:00"

ACCEPTED_FIELDS = [
    "invoice_id",
    "vendor_name",
    "vendor_sku",
    "quantity",
    "unit_price",
    "expected_unit_price",
    "invoice_total",
    "decision",
    "evidence",
    "processed_at",
]

EXCEPTION_FIELDS = [
    "invoice_id",
    "vendor_name",
    "vendor_sku",
    "issue_type",
    "review_reason",
    "evidence",
    "processed_at",
]

ERROR_FIELDS = [
    "invoice_id",
    "status",
    "error_message",
    "manual_review_reason",
    "processed_at",
]


@dataclass(frozen=True)
class PricebookRow:
    vendor_name: str
    expected_unit_price: Decimal
    required_po_prefix: str


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def money(value: str) -> Decimal:
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError(f"invalid money value: {value}") from exc


def quantity(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"invalid quantity value: {value}") from exc


def load_pricebook(path: Path) -> dict[str, PricebookRow]:
    rows: dict[str, PricebookRow] = {}
    for row in read_rows(path):
        rows[row["vendor_sku"]] = PricebookRow(
            vendor_name=row["vendor_name"],
            expected_unit_price=money(row["expected_unit_price"]),
            required_po_prefix=row["required_po_prefix"],
        )
    return rows


def exception(row: dict[str, str], issue_type: str, reason: str, evidence: str) -> dict[str, str]:
    return {
        "invoice_id": row["invoice_id"].strip(),
        "vendor_name": row["vendor_name"].strip(),
        "vendor_sku": row["vendor_sku"].strip(),
        "issue_type": issue_type,
        "review_reason": reason,
        "evidence": evidence,
        "processed_at": PROCESSED_AT,
    }


def process(
    invoice_rows: list[dict[str, str]],
    pricebook: dict[str, PricebookRow],
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    accepted: list[dict[str, str]] = []
    exceptions: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    seen: set[str] = set()

    for row in invoice_rows:
        invoice_id = row["invoice_id"].strip()
        if not invoice_id:
            errors.append(
                {
                    "invoice_id": "",
                    "status": "error",
                    "error_message": "missing invoice_id",
                    "manual_review_reason": "Row blocked because finance records need a stable invoice id for dedupe and audit.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        if invoice_id in seen:
            errors.append(
                {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "error_message": "duplicate invoice_id",
                    "manual_review_reason": "Duplicate invoice row blocked so the same vendor document is not processed twice.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        seen.add(invoice_id)

        sku = row["vendor_sku"].strip()
        pricebook_row = pricebook.get(sku)
        if pricebook_row is None:
            exceptions.append(
                exception(
                    row,
                    "unknown_sku",
                    "SKU is not in the approved pricebook.",
                    f"vendor_sku={sku}",
                )
            )
            continue

        try:
            invoice_quantity = quantity(row["quantity"])
            invoice_unit_price = money(row["unit_price"])
            invoice_total = money(row["invoice_total"])
        except ValueError as exc:
            errors.append(
                {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "error_message": str(exc),
                    "manual_review_reason": "Row blocked because numeric fields could not be parsed safely.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue

        expected_total = (invoice_quantity * invoice_unit_price).quantize(Decimal("0.01"))
        if invoice_unit_price != pricebook_row.expected_unit_price:
            exceptions.append(
                exception(
                    row,
                    "unit_price_mismatch",
                    "Invoice unit price differs from the approved pricebook.",
                    f"invoice={invoice_unit_price} expected={pricebook_row.expected_unit_price}",
                )
            )
            continue
        if invoice_total != expected_total:
            exceptions.append(
                exception(
                    row,
                    "line_total_mismatch",
                    "Invoice total does not equal quantity times unit price.",
                    f"invoice_total={invoice_total} expected_total={expected_total}",
                )
            )
            continue
        if not row["po_number"].startswith(pricebook_row.required_po_prefix):
            exceptions.append(
                exception(
                    row,
                    "po_prefix_mismatch",
                    "Purchase order prefix does not match the vendor's approved prefix.",
                    f"po_number={row['po_number']} required_prefix={pricebook_row.required_po_prefix}",
                )
            )
            continue

        accepted.append(
            {
                "invoice_id": invoice_id,
                "vendor_name": row["vendor_name"].strip(),
                "vendor_sku": sku,
                "quantity": str(invoice_quantity),
                "unit_price": f"{invoice_unit_price:.2f}",
                "expected_unit_price": f"{pricebook_row.expected_unit_price:.2f}",
                "invoice_total": f"{invoice_total:.2f}",
                "decision": "ready_for_human_review",
                "evidence": f"price_match=true total_match=true po_prefix={pricebook_row.required_po_prefix}",
                "processed_at": PROCESSED_AT,
            }
        )

    return accepted, exceptions, errors


def main() -> int:
    datetime.fromisoformat(PROCESSED_AT)
    accepted, exceptions, errors = process(read_rows(INVOICES), load_pricebook(PRICEBOOK))
    write_rows(ACCEPTED_LEDGER, ACCEPTED_FIELDS, accepted)
    write_rows(EXCEPTION_QUEUE, EXCEPTION_FIELDS, exceptions)
    write_rows(ERROR_LOG, ERROR_FIELDS, errors)
    print(f"accepted_rows={len(accepted)}")
    print(f"exception_rows={len(exceptions)}")
    print(f"error_rows={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
