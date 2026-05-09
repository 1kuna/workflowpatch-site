#!/usr/bin/env python3
"""Generate the WorkflowPatch booking/payment state demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-09T09:40:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def open_seats(slot: dict[str, str], holds: dict[tuple[str, str], int]) -> int:
    key = (slot["class_type"], slot["start_at"])
    return int(slot["capacity"]) - int(slot["confirmed_count"]) - holds.get(key, 0)


def find_slot(
    submission: dict[str, str],
    inventory: dict[tuple[str, str], dict[str, str]],
    holds: dict[tuple[str, str], int],
) -> tuple[dict[str, str] | None, str, str]:
    for preference in ("preferred_date_1", "preferred_date_2"):
        key = (submission["class_type"], submission[preference])
        slot = inventory.get(key)
        if slot is None:
            continue
        if slot["ridercoach_available"].lower() != "true":
            continue
        if open_seats(slot, holds) <= 0:
            continue
        return slot, preference, "available"
    return None, "", "no_available_preference"


def main() -> None:
    submissions = read_csv("form-submissions.csv")
    payments = {row["submission_id"]: row for row in read_csv("payment-notifications.csv")}
    inventory = {
        (row["class_type"], row["start_at"]): row for row in read_csv("class-inventory.csv")
    }

    booking_rows: list[dict[str, str]] = []
    followup_rows: list[dict[str, str]] = []
    conflict_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []
    holds: dict[tuple[str, str], int] = {}

    for submission in submissions:
        submission_id = submission["submission_id"]
        if not submission["email"].strip():
            error_rows.append(
                {
                    "submission_id": submission_id,
                    "error_code": "missing_email",
                    "error_detail": "Cannot send booking or payment follow-up without an email address.",
                }
            )
            continue

        payment = payments.get(submission_id, {})
        payment_status = payment.get("status", "missing")
        slot, preference, reason = find_slot(submission, inventory, holds)
        if slot is None:
            conflict_rows.append(
                {
                    "submission_id": submission_id,
                    "class_type": submission["class_type"],
                    "reason": reason,
                    "next_step": "Send alternate-date request before creating a hold or confirmation.",
                }
            )
            continue

        slot_key = (slot["class_type"], slot["start_at"])
        if payment_status == "paid":
            booking_rows.append(
                {
                    "submission_id": submission_id,
                    "class_type": submission["class_type"],
                    "selected_start_at": slot["start_at"],
                    "state": "confirmed_paid",
                    "payment_status": "paid",
                    "message_queue": "confirmation_required",
                    "source_preference": preference,
                    "enrollment_link": slot["enrollment_link"],
                    "accepted_at": GENERATED_AT,
                }
            )
            holds[slot_key] = holds.get(slot_key, 0) + 1
            continue

        booking_rows.append(
            {
                "submission_id": submission_id,
                "class_type": submission["class_type"],
                "selected_start_at": slot["start_at"],
                "state": "tentative_unpaid_hold",
                "payment_status": payment_status,
                "message_queue": "payment_reminder_required",
                "source_preference": preference,
                "enrollment_link": slot["enrollment_link"],
                "accepted_at": GENERATED_AT,
            }
        )
        holds[slot_key] = holds.get(slot_key, 0) + 1
        followup_rows.append(
            {
                "submission_id": submission_id,
                "recipient": submission["email"],
                "message_type": "payment_required",
                "draft": "Your requested time is tentatively held, but the slot is not secure until payment is received.",
                "approval": "required",
            }
        )

    write_csv(
        "booking-ledger.csv",
        booking_rows,
        [
            "submission_id",
            "class_type",
            "selected_start_at",
            "state",
            "payment_status",
            "message_queue",
            "source_preference",
            "enrollment_link",
            "accepted_at",
        ],
    )
    write_csv(
        "followup-queue.csv",
        followup_rows,
        ["submission_id", "recipient", "message_type", "draft", "approval"],
    )
    write_csv("conflict-queue.csv", conflict_rows, ["submission_id", "class_type", "reason", "next_step"])
    write_csv("error-log.csv", error_rows, ["submission_id", "error_code", "error_detail"])

    print(f"submission_rows={len(submissions)}")
    print(f"booking_rows={len(booking_rows)}")
    print(f"followup_rows={len(followup_rows)}")
    print(f"conflict_rows={len(conflict_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
