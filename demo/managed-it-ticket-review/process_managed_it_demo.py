#!/usr/bin/env python3
"""Generate the WorkflowPatch managed IT ticket-review proof outputs."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T07:30:00Z"
MIN_CONFIDENCE = 0.85


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-")


def yes(value: str) -> bool:
    return value.strip().lower() == "yes"


def blocked_row(ticket: dict[str, str], reason: str, next_step: str, queue: str = "manual_review") -> dict[str, str]:
    return {
        "ticket_id": ticket["ticket_id"] or "missing",
        "queue": queue,
        "reason": reason,
        "reviewer": ticket["owner_email"] or "service-lead@sample.test",
        "next_step": next_step,
        "source_summary": ticket["summary"] or "missing summary",
    }


def main() -> int:
    clients = {row["client_key"]: row for row in read_csv("client-map.csv")}
    policies = {row["category"]: row for row in read_csv("review-policy.csv")}
    seen_ticket_fingerprints: set[tuple[str, str, str]] = set()

    ledger_rows: list[dict[str, str]] = []
    draft_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for ticket in read_csv("ticket-events.csv"):
        ticket_id = ticket["ticket_id"].strip()
        client_key = slug(ticket["client_name"])
        summary = ticket["summary"].strip()
        category = ticket["category_hint"].strip().lower()

        if not ticket_id or not client_key or not summary:
            error_rows.append(
                {
                    "ticket_id": ticket_id or "missing",
                    "error_code": "missing_required_ticket_field",
                    "error_detail": (
                        f"client={ticket['client_name'] or 'missing'} "
                        f"summary_present={'yes' if summary else 'no'}"
                    ),
                }
            )
            continue

        client = clients.get(client_key)
        if client is None:
            blocked_rows.append(
                blocked_row(
                    ticket,
                    "unknown_client",
                    "Map the client before creating account-manager or client-status output.",
                    "client_lookup_review",
                )
            )
            continue

        if client["account_status"] != "active":
            blocked_rows.append(
                blocked_row(
                    ticket,
                    "client_not_active",
                    "Resolve onboarding or account hold before summarizing this row.",
                    client["review_queue"],
                )
            )
            continue

        if yes(ticket["sensitive_flag"]):
            blocked_rows.append(
                blocked_row(
                    ticket,
                    "security_sensitive_content",
                    "Redact security-sensitive evidence before any summary or client note exists.",
                    "security_review",
                )
            )
            continue

        try:
            confidence = float(ticket["confidence"])
        except ValueError:
            error_rows.append(
                {
                    "ticket_id": ticket_id,
                    "error_code": "invalid_confidence",
                    "error_detail": f"Confidence value {ticket['confidence']!r} is not numeric.",
                }
            )
            continue

        if confidence < MIN_CONFIDENCE:
            blocked_rows.append(
                blocked_row(
                    ticket,
                    "low_confidence_summary",
                    "Have the service lead review the source row before it enters any summary queue.",
                    client["review_queue"],
                )
            )
            continue

        fingerprint = (client_key, category, slug(summary))
        if fingerprint in seen_ticket_fingerprints:
            blocked_rows.append(
                blocked_row(
                    ticket,
                    "duplicate_ticket_pattern",
                    "Confirm whether this is a true repeat before creating another review item.",
                    client["review_queue"],
                )
            )
            continue
        seen_ticket_fingerprints.add(fingerprint)

        policy = policies.get(category, policies["support"])
        ledger_rows.append(
            {
                "ticket_id": ticket_id,
                "client_key": client_key,
                "account_manager": client["account_manager"],
                "category": category,
                "priority": ticket["priority"],
                "sla_state": ticket["sla_state"],
                "decision": "accepted_for_internal_review",
                "review_queue": client["review_queue"],
                "accepted_at": GENERATED_AT,
                "proof": f"{ticket['source_system']} -> {client['review_queue']} for {client['account_manager']}",
            }
        )

        if yes(ticket["client_facing_candidate"]):
            draft_rows.append(
                {
                    "ticket_id": ticket_id,
                    "client_key": client_key,
                    "account_manager": client["account_manager"],
                    "draft_status": "approval_required",
                    "draft_summary": policy["accepted_summary"],
                    "review_reason": policy["review_reason"],
                    "next_action": policy["next_action"],
                }
            )

    write_csv(
        "ticket-review-ledger.csv",
        ledger_rows,
        [
            "ticket_id",
            "client_key",
            "account_manager",
            "category",
            "priority",
            "sla_state",
            "decision",
            "review_queue",
            "accepted_at",
            "proof",
        ],
    )
    write_csv(
        "client-summary-draft-queue.csv",
        draft_rows,
        [
            "ticket_id",
            "client_key",
            "account_manager",
            "draft_status",
            "draft_summary",
            "review_reason",
            "next_action",
        ],
    )
    write_csv(
        "blocked-escalation-queue.csv",
        blocked_rows,
        ["ticket_id", "queue", "reason", "reviewer", "next_step", "source_summary"],
    )
    write_csv("error-log.csv", error_rows, ["ticket_id", "error_code", "error_detail"])

    print(f"ticket_rows={len(read_csv('ticket-events.csv'))}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"draft_rows={len(draft_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
