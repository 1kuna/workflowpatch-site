#!/usr/bin/env python3
"""Generate the WorkflowPatch public proof outputs from mock input.

This demo is intentionally small and deterministic. It shows the delivery
shape WorkflowPatch cares about: validate first, block unsafe rows visibly,
and keep customer-facing text in a human review queue.
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "mock-input.csv"
REVIEW_QUEUE = ROOT / "review-queue.csv"
ERROR_LOG = ROOT / "error-log.csv"
PROCESSED_AT = "2026-05-08T12:35:00-04:00"

REVIEW_FIELDS = [
    "request_id",
    "status",
    "request_type",
    "urgency",
    "suggested_owner",
    "draft_next_step",
    "approval_required",
    "error_message",
    "processed_at",
]

ERROR_FIELDS = [
    "request_id",
    "status",
    "error_message",
    "manual_review_reason",
    "processed_at",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def classify(message: str) -> tuple[str, str, str]:
    text = message.lower()
    if "salesforce" in text or "handoff" in text:
        return "operations_request", "revenue_ops", "Draft a Salesforce handoff note with the missing next step and route it to the deal owner for review."
    if "lead" in text or "sales" in text:
        return "sales_inquiry", "sales_ops", "Review the managed-services lead, confirm fit, and draft the first async reply from the website-form details."
    if "ticket" in text or "summary" in text or "report" in text:
        return "reporting_request", "service_ops", "Prepare the monthly ticket-summary note, list unresolved exceptions, and send to the account owner for approval."
    if "invoice" in text or "account" in text:
        return "operations_request", "finance_ops", "Create a manual-review item for the unmatched invoice email and ask the owner to confirm account mapping before any outbound note."
    return "unclear", "manual_review", "Route to manual review because the request type is unclear."


def urgency_for(row: dict[str, str]) -> str:
    message = row["message"].lower()
    if row["priority_hint"].lower() == "high" or "urgent" in message or "before noon" in message:
        return "high"
    return "normal"


def process(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    review_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for row in rows:
        request_id = row["request_id"].strip()
        if not request_id:
            error_rows.append(
                {
                    "request_id": "",
                    "status": "error",
                    "error_message": "missing request_id",
                    "manual_review_reason": "Row blocked because it has no stable id for dedupe or audit.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        if request_id in seen:
            error_rows.append(
                {
                    "request_id": request_id,
                    "status": "error",
                    "error_message": "duplicate request_id",
                    "manual_review_reason": "Duplicate export row blocked so the same request is not processed twice.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        seen.add(request_id)

        if not row["requester_email"].strip():
            error_rows.append(
                {
                    "request_id": request_id,
                    "status": "error",
                    "error_message": "missing requester_email",
                    "manual_review_reason": "Customer-facing draft blocked because the row has no requester email.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue
        if not row["message"].strip():
            error_rows.append(
                {
                    "request_id": request_id,
                    "status": "error",
                    "error_message": "missing message",
                    "manual_review_reason": "Row blocked because there is no message to classify or summarize.",
                    "processed_at": PROCESSED_AT,
                }
            )
            continue

        request_type, owner, next_step = classify(row["message"])
        review_rows.append(
            {
                "request_id": request_id,
                "status": "ready",
                "request_type": request_type,
                "urgency": urgency_for(row),
                "suggested_owner": owner,
                "draft_next_step": next_step,
                "approval_required": "true",
                "error_message": "",
                "processed_at": PROCESSED_AT,
            }
        )

    return review_rows, error_rows


def main() -> int:
    # Validate timestamp shape so the demo fails loudly if edited carelessly.
    datetime.fromisoformat(PROCESSED_AT)
    review_rows, error_rows = process(read_rows(INPUT))
    write_rows(REVIEW_QUEUE, REVIEW_FIELDS, review_rows)
    write_rows(ERROR_LOG, ERROR_FIELDS, error_rows)
    print(f"review_rows={len(review_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
