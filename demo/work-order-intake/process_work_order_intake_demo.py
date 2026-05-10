#!/usr/bin/env python3
"""Generate the WorkflowPatch work-order intake demo outputs."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T10:45:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def boolish(value: str) -> bool:
    return value.strip().lower() == "true"


def block_row(email: dict[str, str], reason: str, evidence: str, next_step: str) -> dict[str, str]:
    return {
        "email_id": email["email_id"] or "missing",
        "queue": "blocked_work_order_review",
        "reason": reason,
        "evidence": evidence,
        "next_step": next_step,
    }


def resolve_site(
    email: dict[str, str],
    site_by_id: dict[str, dict[str, str]],
    sites_by_location: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    store_id = email["store_id"].strip()
    if store_id:
        site = site_by_id.get(store_id)
        if site is None:
            return None, block_row(
                email,
                "unknown_store_id",
                f"store_id={store_id}",
                "Confirm the FACIL-IT site id before any work-order write plan.",
            )
        return site, None

    location_name = email["location_name"].strip()
    location_key = key(location_name)
    matches = sites_by_location.get(location_key, [])
    if not matches and location_key:
        matches = [site for site in site_by_id.values() if location_key in key(site["location_name"])]
    if len(matches) == 1:
        return matches[0], None
    if len(matches) > 1:
        return None, block_row(
            email,
            "ambiguous_location",
            f"location_name={location_name} matched {len(matches)} mapped sites",
            "Confirm the exact store or FACIL-IT site before planning a create or update.",
        )
    return None, block_row(
        email,
        "missing_store_match",
        f"location_name={location_name or 'missing'}",
        "Provide a store id or buyer-approved site map before any write plan.",
    )


def main() -> int:
    policies = {row["rule"]: row["value"] for row in read_csv("intake-policy.csv")}
    min_confidence = float(policies["min_confidence"])
    required_fields = [
        row["source_field"]
        for row in read_csv("facil-it-field-map.csv")
        if boolish(row["required"]) and row["source_field"] != "store_id"
    ]
    sites = read_csv("location-map.csv")
    site_by_id = {row["store_id"]: row for row in sites}
    sites_by_location: dict[str, list[dict[str, str]]] = {}
    for row in sites:
        sites_by_location.setdefault(key(row["location_name"]), []).append(row)

    seen_work_orders: set[tuple[str, str]] = set()
    ledger_rows: list[dict[str, str]] = []
    write_plan_rows: list[dict[str, str]] = []
    chat_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for email in read_csv("source-emails.csv"):
        email_id = email["email_id"].strip()
        if not email_id:
            error_rows.append(
                {
                    "email_id": "missing",
                    "error_code": "missing_email_id",
                    "error_detail": "Cannot process a work-order email without a stable source id.",
                }
            )
            continue

        if email["body_quality"] == "empty_body":
            error_rows.append(
                {
                    "email_id": email_id,
                    "error_code": "empty_forwarded_body",
                    "error_detail": "Forwarded thread did not include enough body text for work-order parsing.",
                }
            )
            continue

        missing_fields = [field for field in required_fields if not email[field].strip()]
        if missing_fields:
            blocked_rows.append(
                block_row(
                    email,
                    "missing_required_field",
                    ", ".join(missing_fields),
                    "Ask for the missing work-order fields before planning any FACIL-IT create or update.",
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

        if confidence < min_confidence:
            blocked_rows.append(
                block_row(
                    email,
                    "low_confidence_parse",
                    f"confidence={confidence:.2f}",
                    "Review the email and field extraction before any write-plan row.",
                )
            )
            continue

        site, site_block = resolve_site(email, site_by_id, sites_by_location)
        if site_block is not None:
            blocked_rows.append(site_block)
            continue
        assert site is not None

        if site["site_status"] != "active":
            blocked_rows.append(
                block_row(
                    email,
                    "inactive_site",
                    f"site_status={site['site_status']}",
                    "Confirm the site is active in FACIL-IT before planning a write.",
                )
            )
            continue

        if email["attachment_status"] == "fetch_failed":
            blocked_rows.append(
                block_row(
                    email,
                    "attachment_fetch_failed",
                    f"attachment_count={email['attachment_count']}",
                    "Retry or exclude attachments before a live FACIL-IT work-order create.",
                )
            )
            continue

        duplicate_key = (email["work_order_number"].strip(), site["facil_it_site_id"])
        if duplicate_key in seen_work_orders:
            blocked_rows.append(
                block_row(
                    email,
                    "duplicate_work_order",
                    f"{duplicate_key[0]} at {duplicate_key[1]}",
                    "Attach the forwarded replay to the existing review item instead of creating another candidate.",
                )
            )
            continue
        seen_work_orders.add(duplicate_key)

        ledger_rows.append(
            {
                "email_id": email_id,
                "work_order_number": email["work_order_number"],
                "facil_it_site_id": site["facil_it_site_id"],
                "location_name": site["location_name"],
                "priority": email["priority"],
                "trade": email["trade"],
                "issue_summary": email["issue_summary"],
                "requested_window": email["requested_window"],
                "attachment_count": email["attachment_count"],
                "intake_status": "write_plan_ready",
                "accepted_at": GENERATED_AT,
            }
        )
        write_plan_rows.append(
            {
                "plan_id": f"plan-{email_id}",
                "email_id": email_id,
                "operation": "create_or_update_work_order",
                "endpoint_label": "FACIL-IT work-order endpoint",
                "idempotency_key": f"{email['work_order_number']}:{site['facil_it_site_id']}",
                "payload_summary": f"{email['trade']} | {email['priority']} | {site['location_name']} | {email['requested_window']}",
                "write_status": "dry_run_only",
                "approval_required": "true",
                "note": "No live FACIL-IT write is attempted in this proof.",
            }
        )
        chat_rows.append(
            {
                "summary_id": f"chat-{email_id}",
                "email_id": email_id,
                "google_chat_room": site["google_chat_room"],
                "summary_text": f"{email['work_order_number']} {email['priority']} {email['trade']} at {site['location_name']}: {email['issue_summary']}",
                "send_status": "queued_not_sent",
                "next_step": "Send only after buyer approval of Chat destination and live workflow scope.",
            }
        )

    write_csv(
        "work-order-ledger.csv",
        ledger_rows,
        [
            "email_id",
            "work_order_number",
            "facil_it_site_id",
            "location_name",
            "priority",
            "trade",
            "issue_summary",
            "requested_window",
            "attachment_count",
            "intake_status",
            "accepted_at",
        ],
    )
    write_csv(
        "facil-it-write-plan.csv",
        write_plan_rows,
        [
            "plan_id",
            "email_id",
            "operation",
            "endpoint_label",
            "idempotency_key",
            "payload_summary",
            "write_status",
            "approval_required",
            "note",
        ],
    )
    write_csv(
        "google-chat-summary-queue.csv",
        chat_rows,
        ["summary_id", "email_id", "google_chat_room", "summary_text", "send_status", "next_step"],
    )
    write_csv(
        "blocked-review-queue.csv",
        blocked_rows,
        ["email_id", "queue", "reason", "evidence", "next_step"],
    )
    write_csv("error-log.csv", error_rows, ["email_id", "error_code", "error_detail"])

    print(f"email_rows={len(read_csv('source-emails.csv'))}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"write_plan_rows={len(write_plan_rows)}")
    print(f"chat_rows={len(chat_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
