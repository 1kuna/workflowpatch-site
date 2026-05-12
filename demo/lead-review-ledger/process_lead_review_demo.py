#!/usr/bin/env python3
"""Generate the WorkflowPatch lead review ledger proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T09:26:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def blocked(row: dict[str, str], reason: str, detail: str) -> dict[str, str]:
    return {
        "event_id": row["event_id"] or "missing",
        "lead_ref": row["lead_ref"] or "missing",
        "blocked_action": reason,
        "detail": detail,
        "next_step": "review_before_any_whatsapp_review_request_or_crm_write",
    }


def review(row: dict[str, str], review_type: str, detail: str) -> dict[str, str]:
    return {
        "event_id": row["event_id"],
        "lead_ref": row["lead_ref"],
        "review_type": review_type,
        "draft_status": "internal_review_only",
        "detail": detail,
        "approval_needed": "approval_required_before_external_message_or_live_write",
    }


def main() -> int:
    rows = read_csv("lead-events.csv")
    seen_keys: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in rows:
        required = ("event_id", "lead_ref", "course_interest", "lead_stage", "duplicate_key", "source_boundary")
        missing = [field for field in required if not row[field].strip()]
        if missing:
            error_rows.append(
                {
                    "event_id": row["event_id"] or "missing",
                    "error_code": "missing_required_lead_field",
                    "error_detail": ",".join(missing),
                }
            )
            continue

        if row["source_boundary"] != "synthetic_or_redacted":
            blocked_rows.append(blocked(row, "live_customer_channel_source", "Use synthetic or redacted rows for the first proof."))
            continue

        duplicate_key = row["duplicate_key"].strip()
        if duplicate_key in seen_keys:
            blocked_rows.append(blocked(row, "duplicate_lead_key", f"duplicate_key={duplicate_key}"))
            continue
        seen_keys.add(duplicate_key)

        if row["preferred_channel"] == "whatsapp" and row["phone_consent"] != "true":
            blocked_rows.append(blocked(row, "missing_whatsapp_consent", "phone_consent is not true."))
            continue

        if row["crm_match_status"] != "matched":
            review_rows.append(review(row, "crm_match_review", "Confirm CRM identity before ledger or follow-up action."))
            continue

        action = {
            "new_inquiry": "lead_intake_review",
            "follow_up_due": "followup_review",
            "post_service": "review_request_review",
        }.get(row["lead_stage"], "manual_review")

        ledger_rows.append(
            {
                "event_id": row["event_id"],
                "lead_ref": row["lead_ref"],
                "course_interest": row["course_interest"],
                "crm_action": action,
                "channel_boundary": "draft_only_no_message",
                "processed_at": GENERATED_AT,
            }
        )

        review_detail = "Review lead response draft before any external message."
        if row["review_request_eligible"] == "true":
            review_detail = "Review request timing must be approved before any Google Reviews action."
        review_rows.append(review(row, action, review_detail))

    write_csv(
        "crm-lead-ledger.csv",
        ledger_rows,
        ["event_id", "lead_ref", "course_interest", "crm_action", "channel_boundary", "processed_at"],
    )
    write_csv(
        "internal-review-queue.csv",
        review_rows,
        ["event_id", "lead_ref", "review_type", "draft_status", "detail", "approval_needed"],
    )
    write_csv(
        "blocked-action-queue.csv",
        blocked_rows,
        ["event_id", "lead_ref", "blocked_action", "detail", "next_step"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"source_rows={len(rows)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
