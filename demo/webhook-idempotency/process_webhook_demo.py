#!/usr/bin/env python3
"""Generate the WorkflowPatch webhook idempotency proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    tenants = {row["tenant_id"]: row for row in read_csv("tenant-registry.csv")}
    accepted_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []
    seen_event_ids: set[str] = set()

    for row in read_csv("webhook-events.csv"):
        event_id = row["event_id"].strip()
        tenant_id = row["tenant_id"].strip()
        event_type = row["event_type"].strip()
        payload_restaurant_id = row["payload_restaurant_id"].strip()

        if not event_id or not tenant_id or not event_type:
            error_rows.append(
                {
                    "event_id": event_id or "missing",
                    "status": "error",
                    "reason": "missing event id, tenant id, or event type",
                    "evidence": f"tenant_id={tenant_id or 'missing'} event_type={event_type or 'missing'}",
                }
            )
            continue

        if event_id in seen_event_ids:
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "tenant_id": tenant_id,
                    "status": "blocked",
                    "reason": "duplicate idempotency key",
                    "evidence": "event_id was already claimed earlier in this run",
                    "reviewer_action": "Ignore duplicate side effects; inspect only if payload differs.",
                }
            )
            continue
        seen_event_ids.add(event_id)

        tenant = tenants.get(tenant_id)
        if tenant is None:
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "tenant_id": tenant_id,
                    "status": "blocked",
                    "reason": "unknown tenant",
                    "evidence": "tenant_id is not present in tenant-registry.csv",
                    "reviewer_action": "Create or map tenant before replaying the event.",
                }
            )
            continue

        if tenant["status"] != "active":
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "tenant_id": tenant_id,
                    "status": "blocked",
                    "reason": "inactive tenant",
                    "evidence": f"tenant_status={tenant['status']}",
                    "reviewer_action": "Reactivate tenant or reject the event before replay.",
                }
            )
            continue

        if row["signature_valid"].strip().lower() != "true":
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "tenant_id": tenant_id,
                    "status": "blocked",
                    "reason": "invalid signature",
                    "evidence": "signature_valid=false in mock event source",
                    "reviewer_action": "Reject event and investigate source credentials.",
                }
            )
            continue

        allowed_events = set(tenant["allowed_event_types"].split(";"))
        if event_type not in allowed_events:
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "tenant_id": tenant_id,
                    "status": "blocked",
                    "reason": "unsupported event type for tenant",
                    "evidence": f"event_type={event_type} allowed={tenant['allowed_event_types']}",
                    "reviewer_action": "Add an explicit mapping or reject this event type.",
                }
            )
            continue

        if payload_restaurant_id != tenant_id:
            blocked_rows.append(
                {
                    "event_id": event_id,
                    "tenant_id": tenant_id,
                    "status": "blocked",
                    "reason": "tenant boundary mismatch",
                    "evidence": f"payload_restaurant_id={payload_restaurant_id} expected={tenant_id}",
                    "reviewer_action": "Do not write. Resolve source tenant mapping first.",
                }
            )
            continue

        accepted_rows.append(
            {
                "event_id": event_id,
                "tenant_id": tenant_id,
                "tenant_name": tenant["tenant_name"],
                "event_type": event_type,
                "decision": "ready_for_handler",
                "handler_input": f"{event_type} for {row['payload_customer_email']} amount={row['payload_amount']}",
                "evidence": f"signature=true idempotency_claimed=true tenant_match=true received_at={row['received_at']}",
            }
        )

    write_csv(
        "accepted-events.csv",
        accepted_rows,
        ["event_id", "tenant_id", "tenant_name", "event_type", "decision", "handler_input", "evidence"],
    )
    write_csv(
        "blocked-events.csv",
        blocked_rows,
        ["event_id", "tenant_id", "status", "reason", "evidence", "reviewer_action"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "status", "reason", "evidence"])

    print(f"accepted_rows={len(accepted_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
