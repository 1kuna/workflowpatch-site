#!/usr/bin/env python3
"""Generate the WorkflowPatch signup/access state demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-09T13:30:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def main() -> None:
    events = read_csv("signup-events.csv")
    catalog = {row["tier"]: row for row in read_csv("content-access-catalog.csv")}

    onboarding_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    draft_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in events:
        event_id = event["event_id"]
        email = event["email"].strip()
        tier = event["requested_tier"].strip()
        access_rule = catalog.get(tier)

        if not email:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "missing_email",
                    "error_detail": "Cannot create a user or send onboarding steps without an email address.",
                }
            )
            continue
        if access_rule is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "unknown_tier",
                    "error_detail": f"Requested tier {tier!r} is not in the access catalog.",
                }
            )
            continue
        if not as_bool(event["consent_to_email"]):
            review_rows.append(
                {
                    "event_id": event_id,
                    "email": email,
                    "reason": "no_email_consent",
                    "next_step": "Do not send onboarding email; review consent/source before any follow-up.",
                    "review_owner": "operator",
                }
            )
            continue
        if event["existing_user_id"].strip():
            review_rows.append(
                {
                    "event_id": event_id,
                    "email": email,
                    "reason": "possible_existing_user",
                    "next_step": "Review existing user before creating another access record.",
                    "review_owner": "operator",
                }
            )
            continue
        if access_rule["requires_payment"] == "true" and event["paid_status"] != "paid":
            onboarding_rows.append(
                {
                    "event_id": event_id,
                    "email": email,
                    "requested_tier": tier,
                    "content_group": access_rule["content_group"],
                    "state": "pending_payment",
                    "access_decision": "not_granted",
                    "evidence": "Payment-required tier has no paid event.",
                    "processed_at": GENERATED_AT,
                }
            )
            draft_rows.append(
                {
                    "event_id": event_id,
                    "recipient": email,
                    "message_type": "payment_needed",
                    "draft": "Your signup is captured, but access will stay pending until payment is confirmed.",
                    "approval": "required",
                }
            )
            continue
        if not as_bool(event["email_verified"]):
            onboarding_rows.append(
                {
                    "event_id": event_id,
                    "email": email,
                    "requested_tier": tier,
                    "content_group": access_rule["content_group"],
                    "state": "pending_email_verification",
                    "access_decision": "not_granted",
                    "evidence": "Payment is present, but email verification is incomplete.",
                    "processed_at": GENERATED_AT,
                }
            )
            draft_rows.append(
                {
                    "event_id": event_id,
                    "recipient": email,
                    "message_type": "verify_email",
                    "draft": "Payment is received, but access will wait until the email address is verified.",
                    "approval": "required",
                }
            )
            continue
        if access_rule["requires_manual_approval"] == "true":
            review_rows.append(
                {
                    "event_id": event_id,
                    "email": email,
                    "reason": "manual_access_approval_required",
                    "next_step": "Review partner access before granting restricted content.",
                    "review_owner": "operator",
                }
            )
            continue

        onboarding_rows.append(
            {
                "event_id": event_id,
                "email": email,
                "requested_tier": tier,
                "content_group": access_rule["content_group"],
                "state": access_rule["default_onboarding_state"],
                "access_decision": "granted",
                "evidence": "Required payment and verification checks passed.",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "onboarding-ledger.csv",
        onboarding_rows,
        [
            "event_id",
            "email",
            "requested_tier",
            "content_group",
            "state",
            "access_decision",
            "evidence",
            "processed_at",
        ],
    )
    write_csv(
        "access-review-queue.csv",
        review_rows,
        ["event_id", "email", "reason", "next_step", "review_owner"],
    )
    write_csv(
        "email-draft-queue.csv",
        draft_rows,
        ["event_id", "recipient", "message_type", "draft", "approval"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"event_rows={len(events)}")
    print(f"onboarding_rows={len(onboarding_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"draft_rows={len(draft_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
