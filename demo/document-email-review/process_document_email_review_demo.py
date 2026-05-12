#!/usr/bin/env python3
"""Generate the WorkflowPatch document/email review proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = ("item_id", "source_type", "source_label", "destination", "requested_output", "duplicate_key")


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def confidence(row: dict[str, str]) -> float:
    try:
        return float(row.get("confidence", "0") or "0")
    except ValueError:
        return 0.0


def classify(row: dict[str, str], seen_keys: set[str]) -> tuple[str, str]:
    missing = [field for field in REQUIRED if not row.get(field)]
    if missing:
        return "error", f"missing required fields: {', '.join(missing)}"

    duplicate_key = row["duplicate_key"]
    if duplicate_key in seen_keys:
        return "blocked", "duplicate source key already processed"
    seen_keys.add(duplicate_key)

    if row.get("approved_source", "").lower() != "yes":
        return "blocked", "source is not approved for first proof"
    if row.get("contains_sensitive_data", "").lower() == "yes":
        return "blocked", "sensitive customer or client data present"
    if row.get("external_action_requested", "").lower() == "yes":
        return "review", "live write or external send requires approval"
    if confidence(row) < 0.80:
        return "review", "low extraction confidence"
    if row.get("required_fields_present", "").lower() != "yes":
        return "review", "required extraction fields missing"
    return "accepted", "destination-ready review artifact"


def main() -> None:
    items = read_csv("source-items.csv")
    seen_keys: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    destination_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in items:
        decision, reason = classify(row, seen_keys)
        if decision == "error":
            error_rows.append({"item_id": row.get("item_id", ""), "error": reason})
            continue

        ledger = {
            "item_id": row["item_id"],
            "source_type": row["source_type"],
            "destination": row["destination"],
            "decision": decision,
            "reason": reason,
            "requested_output": row["requested_output"],
        }
        ledger_rows.append(ledger)

        if decision == "accepted":
            destination_rows.append(
                {
                    "item_id": row["item_id"],
                    "destination": row["destination"],
                    "artifact": "review-ready structured row",
                    "approval_state": "ready_for_human_review",
                    "evidence_packet": row["source_label"],
                    "allowed_next_action": "owner can approve destination write after inspection",
                }
            )
        elif decision == "review":
            review_rows.append(
                {
                    "item_id": row["item_id"],
                    "evidence_packet": row["source_label"],
                    "review_reason": reason,
                    "safe_next_step": "inspect source evidence and approve, revise, or block",
                    "decision_options": "approve | revise | block",
                    "no_live_action": "true",
                }
            )
        elif decision == "blocked":
            blocked_rows.append(
                {
                    "item_id": row["item_id"],
                    "block_reason": reason,
                    "safe_boundary": "replace with approved redacted source or keep out of first proof",
                }
            )

    write_csv(
        "extraction-ledger.csv",
        ["item_id", "source_type", "destination", "decision", "reason", "requested_output"],
        ledger_rows,
    )
    write_csv(
        "destination-ready.csv",
        ["item_id", "destination", "artifact", "approval_state", "evidence_packet", "allowed_next_action"],
        destination_rows,
    )
    write_csv(
        "human-review-queue.csv",
        ["item_id", "evidence_packet", "review_reason", "safe_next_step", "decision_options", "no_live_action"],
        review_rows,
    )
    write_csv("blocked-item-queue.csv", ["item_id", "block_reason", "safe_boundary"], blocked_rows)
    write_csv("error-log.csv", ["item_id", "error"], error_rows)
    print(
        f"source_rows={len(items)} "
        f"ledger_rows={len(ledger_rows)} "
        f"destination_rows={len(destination_rows)} "
        f"review_rows={len(review_rows)} "
        f"blocked_rows={len(blocked_rows)} "
        f"error_rows={len(error_rows)}"
    )


if __name__ == "__main__":
    main()
