#!/usr/bin/env python3
"""Generate the WorkflowPatch RevOps integration QA demo outputs."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T07:40:00Z"
MIN_CONFIDENCE = 0.86


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


def allowed_systems(client: dict[str, str]) -> set[str]:
    return {system.strip() for system in client["allowed_systems"].split("|") if system.strip()}


def blocked_row(event: dict[str, str], reason: str, next_step: str, queue: str) -> dict[str, str]:
    return {
        "event_id": event["event_id"] or "missing",
        "queue": queue,
        "reason": reason,
        "reviewer": event["owner_email"] or "revops-owner@sample.test",
        "next_step": next_step,
        "source_summary": event["change_summary"] or "missing summary",
    }


def main() -> int:
    clients = {row["client_key"]: row for row in read_csv("client-map.csv")}
    policies = {row["risk_hint"]: row for row in read_csv("qa-policy.csv")}
    seen_fingerprints: set[tuple[str, str, str, str, str]] = set()

    ledger_rows: list[dict[str, str]] = []
    handoff_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in read_csv("integration-events.csv"):
        event_id = event["event_id"].strip()
        client_key = slug(event["client_name"])
        source_system = event["source_system"].strip()
        destination_system = event["destination_system"].strip()
        record_type = event["record_type"].strip()
        record_key = event["record_key"].strip()
        summary = event["change_summary"].strip()
        risk_hint = event["risk_hint"].strip()

        if not event_id or not client_key or not source_system or not destination_system or not record_type or not record_key or not summary:
            error_rows.append(
                {
                    "event_id": event_id or "missing",
                    "error_code": "missing_required_integration_field",
                    "error_detail": (
                        f"client={event['client_name'] or 'missing'} "
                        f"source={source_system or 'missing'} "
                        f"destination={destination_system or 'missing'} "
                        f"record_key={record_key or 'missing'} "
                        f"summary_present={'yes' if summary else 'no'}"
                    ),
                }
            )
            continue

        client = clients.get(client_key)
        if client is None:
            blocked_rows.append(
                blocked_row(
                    event,
                    "unknown_client",
                    "Map the client workspace before creating owner-review output.",
                    "client_lookup_review",
                )
            )
            continue

        if client["account_status"] != "active":
            blocked_rows.append(
                blocked_row(
                    event,
                    "client_not_active",
                    "Resolve onboarding or account hold before QA output enters a delivery queue.",
                    client["review_queue"],
                )
            )
            continue

        if source_system not in allowed_systems(client) or destination_system not in allowed_systems(client):
            blocked_rows.append(
                blocked_row(
                    event,
                    "unapproved_system_boundary",
                    "Approve the source and destination boundary before any sync-ready output exists.",
                    client["review_queue"],
                )
            )
            continue

        if yes(event["sensitive_flag"]):
            blocked_rows.append(
                blocked_row(
                    event,
                    "sensitive_client_detail",
                    "Redact sensitive details before creating summaries, CRM notes, or client-facing rows.",
                    "sensitive_review",
                )
            )
            continue

        if yes(event["destructive_flag"]):
            blocked_rows.append(
                blocked_row(
                    event,
                    "destructive_or_policy_change",
                    "Require explicit owner approval before a consent, delete, overwrite, or policy-affecting change.",
                    "scope_review",
                )
            )
            continue

        try:
            confidence = float(event["confidence"])
        except ValueError:
            error_rows.append(
                {
                    "event_id": event_id,
                    "error_code": "invalid_confidence",
                    "error_detail": f"Confidence value {event['confidence']!r} is not numeric.",
                }
            )
            continue

        if confidence < MIN_CONFIDENCE:
            blocked_rows.append(
                blocked_row(
                    event,
                    "low_confidence_qa",
                    "Have the implementation owner review the source row before it enters an owner queue.",
                    client["review_queue"],
                )
            )
            continue

        fingerprint = (client_key, source_system, destination_system, record_type, record_key)
        if fingerprint in seen_fingerprints:
            blocked_rows.append(
                blocked_row(
                    event,
                    "duplicate_integration_event",
                    "Confirm this is not a replay before creating another owner-review row.",
                    client["review_queue"],
                )
            )
            continue
        seen_fingerprints.add(fingerprint)

        policy = policies.get(risk_hint, policies["handoff"])
        ledger_rows.append(
            {
                "event_id": event_id,
                "client_key": client_key,
                "source_system": source_system,
                "destination_system": destination_system,
                "record_type": record_type,
                "record_key": record_key,
                "decision": "accepted_for_owner_review",
                "review_queue": client["review_queue"],
                "owner": client["owner"],
                "accepted_at": GENERATED_AT,
                "proof": f"{source_system} -> {destination_system} review for {client['owner']}",
            }
        )

        if yes(event["client_facing_candidate"]):
            handoff_rows.append(
                {
                    "event_id": event_id,
                    "client_key": client_key,
                    "owner": client["owner"],
                    "draft_status": "approval_required",
                    "draft_summary": policy["accepted_summary"],
                    "review_reason": policy["review_reason"],
                    "next_action": policy["next_action"],
                }
            )

    write_csv(
        "qa-ledger.csv",
        ledger_rows,
        [
            "event_id",
            "client_key",
            "source_system",
            "destination_system",
            "record_type",
            "record_key",
            "decision",
            "review_queue",
            "owner",
            "accepted_at",
            "proof",
        ],
    )
    write_csv(
        "owner-handoff-queue.csv",
        handoff_rows,
        [
            "event_id",
            "client_key",
            "owner",
            "draft_status",
            "draft_summary",
            "review_reason",
            "next_action",
        ],
    )
    write_csv(
        "blocked-record-queue.csv",
        blocked_rows,
        ["event_id", "queue", "reason", "reviewer", "next_step", "source_summary"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"event_rows={len(read_csv('integration-events.csv'))}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"handoff_rows={len(handoff_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
