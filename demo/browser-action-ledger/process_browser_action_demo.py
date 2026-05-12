#!/usr/bin/env python3
"""Generate the WorkflowPatch browser action ledger proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T09:32:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def block(row: dict[str, str], reason: str, detail: str) -> dict[str, str]:
    return {
        "action_id": row["action_id"] or "missing",
        "target_flow": row["target_flow"] or "missing",
        "blocked_reason": reason,
        "detail": detail,
        "next_step": "review_before_any_live_browser_api_or_form_action",
    }


def failure(row: dict[str, str], failure_type: str, detail: str, alert_rule: str) -> dict[str, str]:
    return {
        "action_id": row["action_id"],
        "target_flow": row["target_flow"],
        "failure_type": failure_type,
        "detail": detail,
        "alert_rule": alert_rule,
    }


def main() -> int:
    rows = read_csv("source-actions.csv")
    seen_keys: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    taxonomy_rows: list[dict[str, str]] = []
    alert_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in rows:
        required = ("action_id", "target_flow", "action_type", "entity_ref", "source_boundary", "duplicate_key")
        missing = [field for field in required if not row[field].strip()]
        if missing:
            error_rows.append(
                {
                    "action_id": row["action_id"] or "missing",
                    "error_code": "missing_required_action_field",
                    "error_detail": ",".join(missing),
                }
            )
            continue

        if row["source_boundary"] != "approved_source_only":
            blocked_rows.append(block(row, "unapproved_source_scope", "Use approved rows or exports before action planning."))
            continue
        if row["credential_required"] == "true":
            blocked_rows.append(block(row, "credential_scope", "Credential handling is excluded from first proof."))
            continue
        if row["anti_bot_or_proxy_requested"] == "true":
            blocked_rows.append(block(row, "antibot_proxy_scope", "Anti-bot bypass and proxy work are excluded."))
            continue
        if row["live_form_submit"] == "true":
            blocked_rows.append(block(row, "live_form_submission_scope", "External form submissions are excluded."))
            continue

        duplicate_key = row["duplicate_key"].strip()
        if duplicate_key in seen_keys:
            blocked_rows.append(block(row, "duplicate_action_key", f"duplicate_key={duplicate_key}"))
            continue
        seen_keys.add(duplicate_key)

        if row["selector_state"] == "selector_missing":
            taxonomy_rows.append(failure(row, "selector_drift", "selector_state=selector_missing", "pause_flow_and_review_selector"))
            continue
        if row["api_state"] not in {"ok", "not_needed"}:
            taxonomy_rows.append(failure(row, "api_failure", f"api_state={row['api_state']}", "retry_once_then_alert_owner"))
            continue
        if row["rate_limit_state"] == "rate_limited":
            alert_rows.append(failure(row, "rate_limit", "rate_limit_state=rate_limited", "hold_queue_until_window_resets"))
            continue

        ledger_rows.append(
            {
                "action_id": row["action_id"],
                "target_flow": row["target_flow"],
                "action_type": row["action_type"],
                "entity_ref": row["entity_ref"],
                "dry_run_decision": "action_plan_ready",
                "live_boundary": "no_live_browser_api_or_form_action",
                "processed_at": GENERATED_AT,
            }
        )

    write_csv(
        "dry-run-action-ledger.csv",
        ledger_rows,
        ["action_id", "target_flow", "action_type", "entity_ref", "dry_run_decision", "live_boundary", "processed_at"],
    )
    write_csv(
        "blocked-action-queue.csv",
        blocked_rows,
        ["action_id", "target_flow", "blocked_reason", "detail", "next_step"],
    )
    write_csv(
        "failure-taxonomy.csv",
        taxonomy_rows,
        ["action_id", "target_flow", "failure_type", "detail", "alert_rule"],
    )
    write_csv(
        "alert-rules.csv",
        alert_rows,
        ["action_id", "target_flow", "failure_type", "detail", "alert_rule"],
    )
    write_csv("error-log.csv", error_rows, ["action_id", "error_code", "error_detail"])

    print(f"source_rows={len(rows)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"taxonomy_rows={len(taxonomy_rows)}")
    print(f"alert_rows={len(alert_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
