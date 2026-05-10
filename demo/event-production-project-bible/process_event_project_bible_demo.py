#!/usr/bin/env python3
"""Generate the WorkflowPatch event-production Project Bible demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T08:18:00Z"
BUDGET_WARN_RATIO = 0.85
MILESTONE_WARN_DAYS = 10


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def money(value: str) -> int:
    return int(float(value))


def budget_health(total: int, committed: int) -> str:
    ratio = committed / total if total else 1
    if ratio >= 0.95:
        return "blocked_budget_overrun"
    if ratio >= BUDGET_WARN_RATIO:
        return "budget_review"
    return "on_track"


def block(project: dict[str, str], reason: str, owner_action: str) -> dict[str, str]:
    return {
        "project_id": project["project_id"] or "missing",
        "project_name": project["project_name"] or "missing",
        "reason": reason,
        "producer_owner": project["producer_owner"] or "producer-owner@sample.test",
        "production_manager": project["production_manager"] or "production-manager@sample.test",
        "owner_action": owner_action,
    }


def main() -> int:
    projects = read_csv("project-records.csv")
    roles = read_csv("role-policy.csv")
    policy = {row["policy_key"]: row for row in read_csv("readiness-policy.csv")}
    seen_fingerprints: set[tuple[str, str, str]] = set()

    review_rows: list[dict[str, str]] = []
    visibility_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for project in projects:
        project_id = project["project_id"].strip()
        project_name = project["project_name"].strip()
        producer_owner = project["producer_owner"].strip()
        production_manager = project["production_manager"].strip()

        if not project_id or not project_name or not producer_owner or not production_manager:
            error_rows.append(
                {
                    "project_id": project_id or "missing",
                    "error_code": "missing_required_project_field",
                    "error_detail": (
                        f"project_name={project_name or 'missing'} "
                        f"producer_owner={producer_owner or 'missing'} "
                        f"production_manager={production_manager or 'missing'}"
                    ),
                }
            )
            continue

        try:
            total = money(project["budget_total"])
            committed = money(project["committed_spend"])
            days_to_milestone = int(project["days_to_milestone"])
        except ValueError as exc:
            error_rows.append(
                {
                    "project_id": project_id,
                    "error_code": "invalid_project_metric",
                    "error_detail": str(exc),
                }
            )
            continue

        fingerprint = (project_name.replace("Duplicate ", ""), project["next_milestone"], project["project_phase"])
        if fingerprint in seen_fingerprints:
            exception_rows.append(block(project, "duplicate_project_control_row", "Confirm whether this is a duplicate project row or a separate event."))
            continue
        seen_fingerprints.add(fingerprint)

        if project["sensitivity"] != "non_sensitive_ops":
            exception_rows.append(block(project, "sensitive_project_scope", "Use redacted client-safe fields before any proof or visibility automation."))
            continue

        if project["project_phase"] == "complete":
            exception_rows.append(block(project, "completed_project_archive_review", "Confirm closeout/archive policy before routing historical rows."))
            continue

        budget_state = budget_health(total, committed)
        milestone_state = "milestone_review" if days_to_milestone <= MILESTONE_WARN_DAYS or project["milestone_status"] != "on_track" else "on_track"
        vendor_state = "vendor_ready" if project["vendor_status"] == policy["vendor_ready"]["threshold"] else "vendor_review"
        rigging_state = "rigging_ready" if project["rigging_status"] in {"review_ready", "not_required"} else "rigging_review"
        client_state = "client_ready" if project["client_visibility"] == policy["client_visible"]["threshold"] else "client_summary_review"

        states = [budget_state, milestone_state, vendor_state, rigging_state, client_state]
        if any(state.startswith("blocked") for state in states) or "milestone_review" in states or "vendor_review" in states or "rigging_review" in states or "client_summary_review" in states:
            exception_rows.append(
                block(
                    project,
                    ";".join(state for state in states if state != "on_track" and state != "vendor_ready" and state != "rigging_ready" and state != "client_ready"),
                    "Resolve the flagged budget, milestone, vendor, rigging, or client-summary item before Phase 2 build scope.",
                )
            )
            continue

        review_rows.append(
            {
                "project_id": project_id,
                "project_name": project_name,
                "budget_total": str(total),
                "committed_spend": str(committed),
                "budget_health": budget_state,
                "milestone_health": milestone_state,
                "vendor_readiness": vendor_state,
                "rigging_readiness": rigging_state,
                "client_visibility": client_state,
                "producer_owner": producer_owner,
                "production_manager": production_manager,
                "accepted_at": GENERATED_AT,
            }
        )

        for role in roles:
            visibility_rows.append(
                {
                    "project_id": project_id,
                    "project_name": project_name,
                    "role": role["role"],
                    "visible_fields": role["visible_fields"],
                    "review_focus": role["review_focus"],
                    "blocked_fields": role["blocked_fields"],
                    "draft_status": "approval_required",
                }
            )

    write_csv(
        "review-ledger.csv",
        review_rows,
        [
            "project_id",
            "project_name",
            "budget_total",
            "committed_spend",
            "budget_health",
            "milestone_health",
            "vendor_readiness",
            "rigging_readiness",
            "client_visibility",
            "producer_owner",
            "production_manager",
            "accepted_at",
        ],
    )
    write_csv(
        "role-visibility-map.csv",
        visibility_rows,
        ["project_id", "project_name", "role", "visible_fields", "review_focus", "blocked_fields", "draft_status"],
    )
    write_csv(
        "exception-queue.csv",
        exception_rows,
        ["project_id", "project_name", "reason", "producer_owner", "production_manager", "owner_action"],
    )
    write_csv("error-log.csv", error_rows, ["project_id", "error_code", "error_detail"])

    print(f"project_rows={len(projects)}")
    print(f"review_rows={len(review_rows)}")
    print(f"visibility_rows={len(visibility_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
