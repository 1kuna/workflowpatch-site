#!/usr/bin/env python3
"""Generate the WorkflowPatch staffing order-intake proof outputs."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T07:15:00Z"
MIN_CONFIDENCE = 0.85


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-")


def boolish(value: str) -> bool:
    return value.strip().lower() == "true"


def block_row(email: dict[str, str], reason: str, next_step: str) -> dict[str, str]:
    return {
        "email_id": email["email_id"] or "missing",
        "queue": "staffing_order_review",
        "reason": reason,
        "reviewer": "orders-lead@sample.test",
        "next_step": next_step,
        "source_subject": email["subject"] or "missing subject",
    }


def main() -> int:
    clients = {slug(row["client_name"]): row for row in read_csv("client-map.csv")}
    required_fields = [
        row["field"]
        for row in read_csv("extraction-policy.csv")
        if boolish(row["required"]) and row["field"] != "confidence"
    ]
    seen_order_keys: set[tuple[str, str, str, str, str]] = set()

    draft_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for email in read_csv("order-emails.csv"):
        email_id = email["email_id"].strip()
        if not email_id:
            error_rows.append(
                {
                    "email_id": "missing",
                    "error_code": "missing_email_id",
                    "error_detail": "Cannot process a forwarded order without a stable source email id.",
                }
            )
            continue

        if email["body_quality"] == "empty_body":
            error_rows.append(
                {
                    "email_id": email_id,
                    "error_code": "empty_forwarded_body",
                    "error_detail": "Forwarded thread did not include enough body text to extract order fields.",
                }
            )
            continue

        missing_fields = [field for field in required_fields if not email[field].strip()]
        if missing_fields:
            blocked_rows.append(
                block_row(
                    email,
                    "missing_required_field",
                    f"Ask for the missing order fields before drafting: {', '.join(missing_fields)}.",
                )
            )
            continue

        try:
            confidence = float(email["confidence"])
        except ValueError:
            error_rows.append(
                {
                    "email_id": email_id,
                    "error_code": "invalid_confidence",
                    "error_detail": f"Confidence value {email['confidence']!r} is not numeric.",
                }
            )
            continue

        if confidence < MIN_CONFIDENCE:
            blocked_rows.append(
                block_row(
                    email,
                    "low_confidence_extraction",
                    "Review the source email and field extraction before any Monday item draft.",
                )
            )
            continue

        client_key = slug(email["client_name"])
        client = clients.get(client_key)
        if client is None:
            blocked_rows.append(
                block_row(
                    email,
                    "unknown_client",
                    "Match or create the client record before any AutoFlow item draft.",
                )
            )
            continue

        if client["account_status"] != "active":
            blocked_rows.append(
                block_row(
                    email,
                    "inactive_client",
                    "Confirm the account should receive new order drafts before routing.",
                )
            )
            continue

        if client["billing_status"] != "current":
            blocked_rows.append(
                block_row(
                    email,
                    "billing_hold",
                    "Resolve or override billing hold before creating an order draft.",
                )
            )
            continue

        order_key = (
            client_key,
            slug(email["role"]),
            email["shift_date"].strip(),
            email["shift_time"].strip(),
            slug(email["location"]),
        )
        if order_key in seen_order_keys:
            blocked_rows.append(
                block_row(
                    email,
                    "duplicate_order_replay",
                    "Confirm this is not a forwarded replay before creating a second draft.",
                )
            )
            continue
        seen_order_keys.add(order_key)

        draft_rows.append(
            {
                "email_id": email_id,
                "client_key": client_key,
                "monday_client_id": client["monday_client_id"],
                "role": email["role"],
                "shift_date": email["shift_date"],
                "shift_time": email["shift_time"],
                "location": email["location"],
                "headcount": email["headcount"],
                "pay_rate": email["pay_rate"],
                "draft_status": "draft_only",
                "accepted_at": GENERATED_AT,
                "proof": f"{email['client_name']} -> {client['default_board']} via {client['monday_client_id']}",
            }
        )

    write_csv(
        "order-draft-ledger.csv",
        draft_rows,
        [
            "email_id",
            "client_key",
            "monday_client_id",
            "role",
            "shift_date",
            "shift_time",
            "location",
            "headcount",
            "pay_rate",
            "draft_status",
            "accepted_at",
            "proof",
        ],
    )
    write_csv(
        "blocked-alert-queue.csv",
        blocked_rows,
        ["email_id", "queue", "reason", "reviewer", "next_step", "source_subject"],
    )
    write_csv("extraction-error-log.csv", error_rows, ["email_id", "error_code", "error_detail"])

    print(f"email_rows={len(read_csv('order-emails.csv'))}")
    print(f"accepted_rows={len(draft_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
