#!/usr/bin/env python3
"""Generate a mock CRM sync ledger, conflict queue, and error log."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalize_email(value: str) -> str:
    return value.strip().lower()


def normalize_phone(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit() or ch == "+")


def main() -> int:
    contact_map = read_csv("contact-map.csv")
    close_events = read_csv("close-appointments.csv")
    ghl_changes = read_csv("ghl-contact-changes.csv")
    activity_events = read_csv("activity-events.csv")

    by_email = {normalize_email(row["email"]): row for row in contact_map}
    by_phone = {normalize_phone(row["phone"]): row for row in contact_map if row.get("phone", "").strip()}
    by_close = {row["close_contact_id"]: row for row in contact_map}
    by_ghl = {row["ghl_contact_id"]: row for row in contact_map}

    accepted: list[dict[str, str]] = []
    conflicts: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for row in close_events:
        event_id = row["appointment_id"]
        email = normalize_email(row["email"])
        close_id = row["close_contact_id"].strip()
        if not email or not close_id or not row["start_at"].strip():
            errors.append(
                {
                    "event_id": event_id,
                    "source": "close appointment",
                    "error": "missing required identity or appointment field",
                    "evidence": f"close_contact_id={close_id or 'missing'} email={email or 'missing'} start_at={row['start_at'] or 'missing'}",
                    "blocked_at": row["updated_at"],
                }
            )
            continue

        mapped = by_email.get(email)
        if mapped and mapped["close_contact_id"] != close_id:
            conflicts.append(
                {
                    "event_id": event_id,
                    "source": "close appointment",
                    "issue": "email maps to a different Close contact",
                    "evidence": f"event_close={close_id} mapped_close={mapped['close_contact_id']} mapped_ghl={mapped['ghl_contact_id']}",
                    "reviewer_action": "Confirm the correct Close contact before creating or updating the GHL appointment.",
                }
            )
            continue

        if not mapped:
            conflicts.append(
                {
                    "event_id": event_id,
                    "source": "close appointment",
                    "issue": "contact not mapped to GHL",
                    "evidence": f"close_contact_id={close_id} email={email}",
                    "reviewer_action": "Approve a new GHL contact mapping or merge with an existing contact first.",
                }
            )
            continue

        accepted.append(
            {
                "event_id": event_id,
                "source": "close appointment",
                "target": "ghl appointment",
                "contact_key": f"{close_id}/{mapped['ghl_contact_id']}",
                "action": "upsert appointment",
                "status": "ready for sync",
                "evidence": f"start_at={row['start_at']} title={row['title']} status={row['status']}",
            }
        )

    for row in ghl_changes:
        event_id = row["change_id"]
        email = normalize_email(row["email"])
        close_id = row["close_contact_id"].strip()
        ghl_id = row["ghl_contact_id"].strip()
        if not email and not close_id and not ghl_id:
            errors.append(
                {
                    "event_id": event_id,
                    "source": "ghl contact change",
                    "error": "missing contact identity",
                    "evidence": "email=missing close_contact_id=missing ghl_contact_id=missing",
                    "blocked_at": row["updated_at"],
                }
            )
            continue

        mapped = by_email.get(email) or by_close.get(close_id) or by_ghl.get(ghl_id)
        if mapped and (
            (email and mapped["email"] != email)
            or (close_id and mapped["close_contact_id"] != close_id)
            or (ghl_id and mapped["ghl_contact_id"] != ghl_id)
        ):
            conflicts.append(
                {
                    "event_id": event_id,
                    "source": "ghl contact change",
                    "issue": "provided identifiers disagree with contact map",
                    "evidence": f"event={close_id or 'missing'}/{ghl_id or 'missing'}/{email or 'missing'} mapped={mapped['close_contact_id']}/{mapped['ghl_contact_id']}/{mapped['email']}",
                    "reviewer_action": "Resolve the identity conflict before writing the change back to Close.",
                }
            )
            continue

        if not mapped:
            conflicts.append(
                {
                    "event_id": event_id,
                    "source": "ghl contact change",
                    "issue": "contact not mapped to Close",
                    "evidence": f"close_contact_id={close_id or 'missing'} ghl_contact_id={ghl_id or 'missing'} email={email or 'missing'}",
                    "reviewer_action": "Map or create the Close contact before syncing this field change.",
                }
            )
            continue

        accepted.append(
            {
                "event_id": event_id,
                "source": "ghl contact change",
                "target": "close contact",
                "contact_key": f"{mapped['close_contact_id']}/{mapped['ghl_contact_id']}",
                "action": f"update {row['field']}",
                "status": "ready for sync",
                "evidence": f"{row['field']}={row['new_value']} updated_at={row['updated_at']}",
            }
        )

    for row in activity_events:
        event_id = row["activity_id"]
        email = normalize_email(row["email"])
        phone = normalize_phone(row["phone"])
        if not email and not phone:
            errors.append(
                {
                    "event_id": event_id,
                    "source": f"{row['channel']} activity",
                    "error": "missing activity identity",
                    "evidence": "email=missing phone=missing",
                    "blocked_at": row["occurred_at"],
                }
            )
            continue

        email_match = by_email.get(email) if email else None
        phone_match = by_phone.get(phone) if phone else None
        if email_match and phone_match and email_match["ghl_contact_id"] != phone_match["ghl_contact_id"]:
            conflicts.append(
                {
                    "event_id": event_id,
                    "source": f"{row['channel']} activity",
                    "issue": "email and phone map to different contacts",
                    "evidence": (
                        f"email maps {email_match['close_contact_id']}/{email_match['ghl_contact_id']} "
                        f"phone maps {phone_match['close_contact_id']}/{phone_match['ghl_contact_id']}"
                    ),
                    "reviewer_action": "Pick the correct contact before appending the activity to GHL.",
                }
            )
            continue

        mapped = email_match or phone_match
        if not mapped:
            conflicts.append(
                {
                    "event_id": event_id,
                    "source": f"{row['channel']} activity",
                    "issue": "activity not mapped to GHL contact",
                    "evidence": f"email={email or 'missing'} phone={phone or 'missing'}",
                    "reviewer_action": "Map or create the contact before syncing the activity.",
                }
            )
            continue

        accepted.append(
            {
                "event_id": event_id,
                "source": f"{row['channel']} activity",
                "target": "ghl activity",
                "contact_key": f"{mapped['close_contact_id']}/{mapped['ghl_contact_id']}",
                "action": row["desired_ghl_action"],
                "status": "ready for review",
                "evidence": f"{row['activity_type']} at {row['occurred_at']} summary={row['summary']}",
            }
        )

    write_csv(
        "sync-ledger.csv",
        accepted,
        ["event_id", "source", "target", "contact_key", "action", "status", "evidence"],
    )
    write_csv(
        "conflict-queue.csv",
        conflicts,
        ["event_id", "source", "issue", "evidence", "reviewer_action"],
    )
    write_csv(
        "error-log.csv",
        errors,
        ["event_id", "source", "error", "evidence", "blocked_at"],
    )
    print(f"accepted_rows={len(accepted)}")
    print(f"conflict_rows={len(conflicts)}")
    print(f"error_rows={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
