#!/usr/bin/env python3
"""Generate the WorkflowPatch MVP governance review demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T08:54:00Z"
ALLOWED_REVIEW_STATES = {"ready", "legal_review_ready"}


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def yes(value: str) -> bool:
    return value.strip().lower() == "true"


def block(row: dict[str, str], reason: str, next_step: str) -> dict[str, str]:
    return {
        "item_id": row["item_id"] or "missing",
        "source_key": row["source_key"] or "missing",
        "reason": reason,
        "review_owner": "founder-review",
        "next_step": next_step,
    }


def main() -> int:
    items = read_csv("source-items.csv")
    policies = {row["update_type"]: row for row in read_csv("governance-policy.csv")}
    seen_replay_keys: set[str] = set()

    state_rows: list[dict[str, str]] = []
    draft_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for item in items:
        item_id = item["item_id"].strip()
        source_key = item["source_key"].strip()
        update_type = item["update_type"].strip()
        replay_key = item["replay_key"].strip()

        if not item_id or not source_key or not update_type or not replay_key:
            error_rows.append(
                {
                    "item_id": item_id or "missing",
                    "error_code": "missing_required_governance_field",
                    "error_detail": (
                        f"source_key={source_key or 'missing'} "
                        f"update_type={update_type or 'missing'} replay_key={replay_key or 'missing'}"
                    ),
                }
            )
            continue

        if replay_key in seen_replay_keys:
            blocked_rows.append(block(item, "duplicate_replay_key", "Confirm whether this source already produced a review row."))
            continue
        seen_replay_keys.add(replay_key)

        if item["sensitivity"] != "non_sensitive_ops":
            blocked_rows.append(block(item, "sensitive_investor_scope", "Use synthetic or redacted non-sensitive rows before any first proof."))
            continue

        policy = policies.get(update_type)
        if policy is None:
            blocked_rows.append(block(item, "unknown_update_type", "Define the review and draft rule before routing this source."))
            continue

        if item["review_state"] not in ALLOWED_REVIEW_STATES:
            blocked_rows.append(block(item, "review_state_unclear", "Clarify the Airtable or Softr review state before a draft row is created."))
            continue

        if yes(policy["requires_claim_basis"]) and item["claim_basis"] != "source_present":
            blocked_rows.append(block(item, "unsupported_claim", "Attach source evidence before any investor-facing draft is created."))
            continue

        if yes(policy["requires_brand_approved"]) and item["brand_state"] != "approved":
            blocked_rows.append(block(item, "brand_review_required", "Route off-brand text to founder review before a draft leaves the system."))
            continue

        if yes(policy["blocks_external_send"]) and yes(item["requires_external_send"]):
            blocked_rows.append(block(item, "external_send_blocked", "Keep the first proof to draft/review artifacts only."))
            continue

        state_rows.append(
            {
                "item_id": item_id,
                "source_key": source_key,
                "update_type": update_type,
                "source_system": item["source_system"],
                "review_state": policy["required_review_state"],
                "evidence_status": "source_backed" if item["claim_basis"] == "source_present" else "internal_only",
                "processed_at": GENERATED_AT,
            }
        )
        draft_rows.append(
            {
                "item_id": item_id,
                "source_key": source_key,
                "recipient_segment": item["recipient_segment"],
                "draft_action": policy["draft_action"],
                "send_status": "approval_required",
                "draft_status": "dry_run_only",
            }
        )

    write_csv(
        "review-state-ledger.csv",
        state_rows,
        ["item_id", "source_key", "update_type", "source_system", "review_state", "evidence_status", "processed_at"],
    )
    write_csv(
        "approved-draft-queue.csv",
        draft_rows,
        ["item_id", "source_key", "recipient_segment", "draft_action", "send_status", "draft_status"],
    )
    write_csv("blocked-communication-queue.csv", blocked_rows, ["item_id", "source_key", "reason", "review_owner", "next_step"])
    write_csv("error-log.csv", error_rows, ["item_id", "error_code", "error_detail"])

    print(f"item_rows={len(items)}")
    print(f"state_rows={len(state_rows)}")
    print(f"draft_rows={len(draft_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
