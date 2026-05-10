#!/usr/bin/env python3
"""Generate the WorkflowPatch HubSpot/ClickUp stabilization demo outputs."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T07:58:00Z"
MIN_CONFIDENCE = 0.88


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


def split_set(value: str) -> set[str]:
    return {part.strip() for part in value.split("|") if part.strip()}


def yes(value: str) -> bool:
    return value.strip().lower() == "yes"


def conflict(event: dict[str, str], reason: str, next_step: str, queue: str) -> dict[str, str]:
    return {
        "event_id": event["event_id"] or "missing",
        "deal_id": event["deal_id"] or "missing",
        "queue": queue,
        "reason": reason,
        "next_step": next_step,
        "source_summary": event["change_summary"] or "missing summary",
    }


def main() -> int:
    accounts = {slug(row["company_name"]): row for row in read_csv("clickup-map.csv")}
    policies = {row["risk_hint"]: row for row in read_csv("sync-policy.csv")}
    seen_deals: set[tuple[str, str, str]] = set()

    task_rows: list[dict[str, str]] = []
    writeback_rows: list[dict[str, str]] = []
    conflict_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for event in read_csv("hubspot-events.csv"):
        event_id = event["event_id"].strip()
        company_key = slug(event["company_name"])
        pipeline = event["pipeline"].strip()
        deal_id = event["deal_id"].strip()
        stage = event["stage"].strip()
        clickup_list = event["clickup_list"].strip()
        writeback_field = event["writeback_field"].strip()

        if not event_id or not company_key or not pipeline or not deal_id or not stage or not clickup_list or not writeback_field:
            error_rows.append(
                {
                    "event_id": event_id or "missing",
                    "error_code": "missing_required_hubspot_field",
                    "error_detail": (
                        f"company={event['company_name'] or 'missing'} "
                        f"pipeline={pipeline or 'missing'} deal_id={deal_id or 'missing'} "
                        f"stage={stage or 'missing'} list={clickup_list or 'missing'}"
                    ),
                }
            )
            continue

        account = accounts.get(company_key)
        if account is None or account["account_status"] != "active":
            conflict_rows.append(
                conflict(
                    event,
                    "unknown_or_inactive_company",
                    "Map the company workspace before creating a task or write-back preview.",
                    "company_mapping_review",
                )
            )
            continue

        if pipeline not in split_set(account["allowed_pipelines"]):
            conflict_rows.append(
                conflict(
                    event,
                    "unapproved_pipeline",
                    "Approve this HubSpot pipeline before creating a ClickUp task preview.",
                    account["review_queue"],
                )
            )
            continue

        if clickup_list not in split_set(account["allowed_clickup_lists"]):
            conflict_rows.append(
                conflict(
                    event,
                    "unapproved_clickup_list",
                    "Approve the ClickUp list before routing any task candidate there.",
                    account["review_queue"],
                )
            )
            continue

        if writeback_field not in split_set(account["allowed_writeback_fields"]):
            conflict_rows.append(
                conflict(
                    event,
                    "unapproved_writeback_field",
                    "Approve the HubSpot write-back field before producing a dry-run update.",
                    account["review_queue"],
                )
            )
            continue

        if yes(event["sensitive_flag"]):
            conflict_rows.append(
                conflict(
                    event,
                    "sensitive_site_detail",
                    "Redact access notes or sensitive site details before task handoff.",
                    "sensitive_review",
                )
            )
            continue

        if yes(event["destructive_flag"]):
            conflict_rows.append(
                conflict(
                    event,
                    "destructive_hubspot_change",
                    "Require owner approval before any destructive or revenue-state write-back.",
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
            conflict_rows.append(
                conflict(
                    event,
                    "low_confidence_stage_map",
                    "Review the HubSpot stage and ClickUp status mapping before task preview.",
                    account["review_queue"],
                )
            )
            continue

        fingerprint = (company_key, pipeline, deal_id)
        if fingerprint in seen_deals:
            conflict_rows.append(
                conflict(
                    event,
                    "duplicate_deal_stage_event",
                    "Confirm this is not a replay before another task candidate is created.",
                    account["review_queue"],
                )
            )
            continue
        seen_deals.add(fingerprint)

        action = "update_existing_task" if event["existing_task_id"].strip() else "create_task_candidate"
        policy_key = "status_update" if action == "update_existing_task" else "new_task"
        policy = policies.get(policy_key, policies["handoff"])
        task_id_preview = event["existing_task_id"].strip() or f"dryrun-{deal_id}"

        task_rows.append(
            {
                "event_id": event_id,
                "company_key": company_key,
                "deal_id": deal_id,
                "deal_name": event["deal_name"],
                "hubspot_stage": stage,
                "clickup_list": clickup_list,
                "task_action": action,
                "task_id_preview": task_id_preview,
                "decision": "accepted_for_owner_review",
                "owner": account["owner"],
                "accepted_at": GENERATED_AT,
            }
        )
        writeback_rows.append(
            {
                "event_id": event_id,
                "deal_id": deal_id,
                "writeback_field": writeback_field,
                "writeback_value_preview": task_id_preview,
                "draft_status": "approval_required",
                "draft_summary": policy["accepted_summary"],
                "review_reason": policy["review_reason"],
                "next_action": policy["next_action"],
            }
        )

    write_csv(
        "task-ledger.csv",
        task_rows,
        [
            "event_id",
            "company_key",
            "deal_id",
            "deal_name",
            "hubspot_stage",
            "clickup_list",
            "task_action",
            "task_id_preview",
            "decision",
            "owner",
            "accepted_at",
        ],
    )
    write_csv(
        "writeback-preview.csv",
        writeback_rows,
        [
            "event_id",
            "deal_id",
            "writeback_field",
            "writeback_value_preview",
            "draft_status",
            "draft_summary",
            "review_reason",
            "next_action",
        ],
    )
    write_csv(
        "conflict-queue.csv",
        conflict_rows,
        ["event_id", "deal_id", "queue", "reason", "next_step", "source_summary"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "error_code", "error_detail"])

    print(f"event_rows={len(read_csv('hubspot-events.csv'))}")
    print(f"task_rows={len(task_rows)}")
    print(f"writeback_rows={len(writeback_rows)}")
    print(f"conflict_rows={len(conflict_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
