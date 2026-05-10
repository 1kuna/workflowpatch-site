#!/usr/bin/env python3
"""Generate the WorkflowPatch contract packet state demo outputs."""

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


def policy_index() -> dict[str, dict[str, str]]:
    return {row["template"]: row for row in read_csv("packet-policy.csv")}


def decide_state(row: dict[str, str], policy: dict[str, str]) -> tuple[str, str, str]:
    if row["required_fields_complete"] != "yes" or not row["candidate_email"]:
        return (
            "blocked_missing_fields",
            "recruiting_ops",
            "required fields or candidate email missing",
        )
    if row["approver_status"] != "approved":
        return (
            "waiting_on_internal_review",
            "manager",
            f"approver status is {row['approver_status']}",
        )
    if row["envelope_status"] == "signed":
        return ("ready_to_file", "hr_ops", "signed envelope is ready for filing")
    if row["envelope_status"] == "sent":
        waiting_days = int(row["last_candidate_touch_days"])
        if waiting_days >= int(policy["escalate_after_days"]):
            return ("escalation_due", "manager", f"sent envelope has waited {waiting_days} days")
        if waiting_days >= int(policy["reminder_after_days"]):
            return ("reminder_due", "recruiting_ops", f"sent envelope has waited {waiting_days} days")
        return ("waiting_on_candidate", "recruiting_ops", f"sent envelope has waited {waiting_days} days")
    return (
        "ready_for_internal_review",
        "manager",
        "approved hire has required fields and packet not created",
    )


def build_state_ledger() -> list[dict[str, str]]:
    policies = policy_index()
    rows: list[dict[str, str]] = []
    for event in read_csv("hire-events.csv"):
        policy = policies[event["template"]]
        next_state, owner, reason = decide_state(event, policy)
        rows.append(
            {
                "hire_id": event["hire_id"],
                "candidate": event["candidate"],
                "role": event["role"],
                "template": event["template"],
                "next_state": next_state,
                "owner": owner,
                "reason": reason,
                "legal_boundary": "no legal drafting or template edits",
            }
        )
    return rows


def build_reminder_queue(ledger_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    events = {row["hire_id"]: row for row in read_csv("hire-events.csv")}
    rows: list[dict[str, str]] = []
    for state in ledger_rows:
        if state["next_state"] not in {"reminder_due", "escalation_due"}:
            continue
        event = events[state["hire_id"]]
        queue_type = "manager_escalation" if state["next_state"] == "escalation_due" else "candidate_reminder"
        recipient = event["manager"] if queue_type == "manager_escalation" else event["candidate_email"]
        rows.append(
            {
                "hire_id": state["hire_id"],
                "candidate": state["candidate"],
                "queue_type": queue_type,
                "recipient": recipient,
                "reason": state["reason"],
                "send_gate": "approval_required_before_send",
            }
        )
    return rows


def build_filing_manifest(ledger_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    policies = policy_index()
    rows: list[dict[str, str]] = []
    for state in ledger_rows:
        if state["next_state"] != "ready_to_file":
            continue
        rows.append(
            {
                "hire_id": state["hire_id"],
                "candidate": state["candidate"],
                "source_status": "signed",
                "destination": policies[state["template"]]["filing_destination"],
                "ready_to_file": "yes",
                "blocked_reason": "",
            }
        )
    return rows


def build_error_log(ledger_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for state in ledger_rows:
        if not state["next_state"].startswith("blocked"):
            continue
        rows.append(
            {
                "hire_id": state["hire_id"],
                "error_type": "missing_candidate_email",
                "detail": "candidate email is blank",
                "next_action": "collect required candidate email before packet creation",
            }
        )
    return rows


def main() -> int:
    ledger_rows = build_state_ledger()
    reminder_rows = build_reminder_queue(ledger_rows)
    filing_rows = build_filing_manifest(ledger_rows)
    error_rows = build_error_log(ledger_rows)

    write_csv(
        "state-ledger.csv",
        ledger_rows,
        ["hire_id", "candidate", "role", "template", "next_state", "owner", "reason", "legal_boundary"],
    )
    write_csv(
        "reminder-queue.csv",
        reminder_rows,
        ["hire_id", "candidate", "queue_type", "recipient", "reason", "send_gate"],
    )
    write_csv(
        "filing-manifest.csv",
        filing_rows,
        ["hire_id", "candidate", "source_status", "destination", "ready_to_file", "blocked_reason"],
    )
    write_csv("error-log.csv", error_rows, ["hire_id", "error_type", "detail", "next_action"])

    print(f"state_rows={len(ledger_rows)}")
    print(f"reminder_rows={len(reminder_rows)}")
    print(f"filing_rows={len(filing_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
