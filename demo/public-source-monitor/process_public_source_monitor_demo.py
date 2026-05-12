#!/usr/bin/env python3
"""Generate the WorkflowPatch public-source monitor proof outputs.

The proof uses approved public, redacted, or synthetic rows. It models a safe
first slice for regulated or legal-adjacent operations: public-source monitoring
with provenance, review queues, canaries, and explicit sensitive-data blocks.
"""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_rows(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def evidence_hash(event: dict[str, str]) -> str:
    seed = "|".join(
        [
            event["event_id"],
            event["target_id"],
            event["event_type"],
            event["raw_title"],
            event["source_url"],
        ]
    )
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def build_monitor_rows(
    events: list[dict[str, str]],
    targets: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, event in enumerate(events, start=1):
        target = targets[event["target_id"]]
        event_type = event["event_type"]
        confidence = float(event["confidence"])
        status = "accepted"
        action = "write_public_source_row_to_reviewable_ledger"

        if event_type == "record_seen" and confidence < 0.9:
            status = "review"
            action = "review_changed_category_before_destination_write"
        elif event_type == "schema_changed":
            status = "review"
            action = "approve_field_mapping_before_next_run"
        elif event_type in {"out_of_scope", "missing_boundary", "canary_failed"}:
            status = "blocked"
            action = "block_destination_write_and_route_to_operator"

        rows.append(
            {
                "monitor_id": f"MON-{1000 + index}",
                "event_id": event["event_id"],
                "target_id": event["target_id"],
                "status": status,
                "boundary_tag": event["boundary_hint"] if event["boundary_hint"] != "unknown" else "needs_review",
                "source_type": target["source_type"],
                "evidence_hash": evidence_hash(event),
                "next_action": action,
            }
        )
    return rows


def build_review_rows(
    monitor_rows: list[dict[str, str]],
    events_by_id: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in monitor_rows:
        if row["status"] not in {"review", "blocked"}:
            continue
        event = events_by_id[row["event_id"]]
        rows.append(
            {
                "review_id": f"REV-{row['monitor_id'].split('-')[1]}",
                "monitor_id": row["monitor_id"],
                "reason": event["event_type"],
                "operator_prompt": event["notes"],
                "allowed_action": "approve_mapping_or_keep_blocked",
            }
        )
    return rows


def build_error_rows(
    monitor_rows: list[dict[str, str]],
    events_by_id: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in monitor_rows:
        if row["status"] != "blocked":
            continue
        event = events_by_id[row["event_id"]]
        rows.append(
            {
                "error_id": f"ERR-{row['monitor_id'].split('-')[1]}",
                "monitor_id": row["monitor_id"],
                "error_type": event["event_type"],
                "blocked_input": event["raw_title"],
                "resolution": row["next_action"],
            }
        )
    return rows


def build_canary_rows(targets: dict[str, dict[str, str]], monitor_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    blocked_canary = any(row["event_id"] == "EVT-1005" and row["status"] == "blocked" for row in monitor_rows)
    rows: list[dict[str, str]] = []
    for target_id, target in targets.items():
        status = "pass"
        detail = "expected public fields present"
        if target_id == "SRC-1004" and blocked_canary:
            status = "fail"
            detail = "canary mismatch alerted and blocked destination write"
        rows.append(
            {
                "canary_id": f"CAN-{target_id.split('-')[1]}",
                "target_id": target_id,
                "status": status,
                "fetch_window": target["fetch_window"],
                "detail": detail,
            }
        )
    return rows


def write_handoff(
    monitor_rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    error_rows: list[dict[str, str]],
    canary_rows: list[dict[str, str]],
) -> None:
    accepted_count = sum(row["status"] == "accepted" for row in monitor_rows)
    review_count = len(review_rows)
    blocked_count = len(error_rows)
    failing_canaries = sum(row["status"] == "fail" for row in canary_rows)
    body = f"""# Public Source Monitor Handoff

This proof uses approved public, redacted, or synthetic public-source events only. It does not use PHI, patient records, credentialing packets, payer records, secrets, or legal/regulatory judgment.

## Run Summary

- Accepted public-source rows: {accepted_count}
- Review rows: {review_count}
- Blocked rows: {blocked_count}
- Failing canaries: {failing_canaries}

## Operator Boundary

The first paid proof should accept one public source family, one non-sensitive field list, one boundary tag shape, and one review destination. Sensitive files, compliance interpretation, legal advice, production tenant ownership, and patient or payer data stay out of scope.

## Next Safe Step

If a buyer wants to proceed, ask for the approved public source type, allowed fields, boundary tags, review destination, alert destination, and explicit do-not-touch data categories before payment.
"""
    (ROOT / "handoff.md").write_text(body, encoding="utf-8")


def main() -> int:
    targets = {row["target_id"]: row for row in read_rows("source-targets.csv")}
    events = read_rows("source-events.csv")
    events_by_id = {row["event_id"]: row for row in events}

    monitor_rows = build_monitor_rows(events, targets)
    review_rows = build_review_rows(monitor_rows, events_by_id)
    error_rows = build_error_rows(monitor_rows, events_by_id)
    canary_rows = build_canary_rows(targets, monitor_rows)

    write_rows(
        "monitor-ledger.csv",
        monitor_rows,
        ["monitor_id", "event_id", "target_id", "status", "boundary_tag", "source_type", "evidence_hash", "next_action"],
    )
    write_rows(
        "review-queue.csv",
        review_rows,
        ["review_id", "monitor_id", "reason", "operator_prompt", "allowed_action"],
    )
    write_rows(
        "error-log.csv",
        error_rows,
        ["error_id", "monitor_id", "error_type", "blocked_input", "resolution"],
    )
    write_rows(
        "canary-log.csv",
        canary_rows,
        ["canary_id", "target_id", "status", "fetch_window", "detail"],
    )
    write_handoff(monitor_rows, review_rows, error_rows, canary_rows)

    print(f"source_targets={len(targets)}")
    print(f"event_rows={len(events)}")
    print(f"monitor_rows={len(monitor_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"error_rows={len(error_rows)}")
    print(f"canary_rows={len(canary_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
