#!/usr/bin/env python3
"""Generate the WorkflowPatch Airtable source-of-truth audit demo outputs."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T08:05:00Z"
HIGH_VOLUME_THRESHOLD = 100_000


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


def block(row: dict[str, str], reason: str, next_step: str) -> dict[str, str]:
    return {
        "object_id": row["object_id"] or "missing",
        "object_name": row["object_name"] or "missing",
        "reason": reason,
        "owner": row["decision_owner"] or "architecture-owner@sample.test",
        "next_step": next_step,
    }


def main() -> int:
    objects = read_csv("object-inventory.csv")
    writers = read_csv("writer-map.csv")
    policies = {row["risk_hint"]: row for row in read_csv("audit-policy.csv")}
    writer_lookup: dict[str, list[dict[str, str]]] = {}
    seen_objects: set[tuple[str, str, str]] = set()

    for writer in writers:
        writer_lookup.setdefault(slug(writer["object_name"]), []).append(writer)

    decision_rows: list[dict[str, str]] = []
    write_policy_rows: list[dict[str, str]] = []
    archive_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in objects:
        object_id = row["object_id"].strip()
        object_name = row["object_name"].strip()
        current_system = row["current_system"].strip()
        proposed_truth = row["proposed_source_of_truth"].strip()
        owner = row["decision_owner"].strip()

        if not object_id or not object_name or not current_system or not owner:
            error_rows.append(
                {
                    "object_id": object_id or "missing",
                    "error_code": "missing_required_object_field",
                    "error_detail": (
                        f"object_name={object_name or 'missing'} "
                        f"current_system={current_system or 'missing'} owner={owner or 'missing'}"
                    ),
                }
            )
            continue

        try:
            record_count = int(row["record_count"])
        except ValueError:
            error_rows.append(
                {
                    "object_id": object_id,
                    "error_code": "invalid_record_count",
                    "error_detail": f"Record count {row['record_count']!r} is not numeric.",
                }
            )
            continue

        if not proposed_truth:
            blocked_rows.append(block(row, "missing_source_of_truth", "Choose a canonical owner before implementation planning."))
            continue

        fingerprint = (slug(object_name), current_system, proposed_truth)
        if fingerprint in seen_objects:
            blocked_rows.append(block(row, "duplicate_object_decision", "Confirm whether this is a duplicate object or a separate mirror."))
            continue
        seen_objects.add(fingerprint)

        object_writers = writer_lookup.get(slug(object_name), [])
        if not object_writers:
            blocked_rows.append(block(row, "missing_writer_policy", "Map allowed writers and readers before sync design."))
            continue

        if yes(row["sensitive_flag"]):
            blocked_rows.append(block(row, "sensitive_object_policy", "Resolve access and audit requirements before build scope."))
            continue

        volume_class = "high_volume" if record_count >= HIGH_VOLUME_THRESHOLD else "standard_volume"
        policy = policies["canonical"]
        decision_rows.append(
            {
                "object_id": object_id,
                "object_name": object_name,
                "record_count": str(record_count),
                "volume_class": volume_class,
                "current_system": current_system,
                "proposed_source_of_truth": proposed_truth,
                "decision": "ready_for_architecture_review",
                "owner": owner,
                "accepted_at": GENERATED_AT,
                "review_note": policy["accepted_summary"],
            }
        )

        if yes(row["archive_candidate"]):
            archive_policy = policies["archive"]
            archive_rows.append(
                {
                    "object_id": object_id,
                    "object_name": object_name,
                    "record_count": str(record_count),
                    "archive_status": "approval_required",
                    "owner": owner,
                    "review_reason": archive_policy["review_reason"],
                    "next_action": archive_policy["next_action"],
                }
            )

        write_policy = policies["write_policy"]
        for writer in object_writers:
            write_policy_rows.append(
                {
                    "object_id": object_id,
                    "object_name": object_name,
                    "system": writer["system"],
                    "allowed_write": writer["allowed_write"],
                    "allowed_read": writer["allowed_read"],
                    "write_scope": writer["write_scope"],
                    "risk_level": writer["risk_level"],
                    "draft_status": "approval_required",
                    "review_reason": write_policy["review_reason"],
                }
            )

    write_csv(
        "decision-pack.csv",
        decision_rows,
        [
            "object_id",
            "object_name",
            "record_count",
            "volume_class",
            "current_system",
            "proposed_source_of_truth",
            "decision",
            "owner",
            "accepted_at",
            "review_note",
        ],
    )
    write_csv(
        "write-policy-map.csv",
        write_policy_rows,
        [
            "object_id",
            "object_name",
            "system",
            "allowed_write",
            "allowed_read",
            "write_scope",
            "risk_level",
            "draft_status",
            "review_reason",
        ],
    )
    write_csv(
        "archive-review-queue.csv",
        archive_rows,
        ["object_id", "object_name", "record_count", "archive_status", "owner", "review_reason", "next_action"],
    )
    write_csv("blocked-decision-queue.csv", blocked_rows, ["object_id", "object_name", "reason", "owner", "next_step"])
    write_csv("error-log.csv", error_rows, ["object_id", "error_code", "error_detail"])

    print(f"object_rows={len(objects)}")
    print(f"decision_rows={len(decision_rows)}")
    print(f"write_policy_rows={len(write_policy_rows)}")
    print(f"archive_rows={len(archive_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
