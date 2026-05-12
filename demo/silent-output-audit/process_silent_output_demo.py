#!/usr/bin/env python3
"""Generate the WorkflowPatch silent-output audit proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = (
    "run_id",
    "workflow_family",
    "client_context",
    "source_trigger",
    "expected_action",
    "observed_action",
    "expected_context_key",
    "observed_context_key",
    "expected_metric_min",
    "expected_metric_max",
    "observed_metric",
    "duplicate_key",
)


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_yes(row: dict[str, str], field: str) -> bool:
    return row.get(field, "").strip().lower() == "yes"


def metric(row: dict[str, str], field: str) -> float:
    return float(row.get(field, "") or "nan")


def violation_codes(row: dict[str, str]) -> list[str]:
    violations: list[str] = []
    if row["expected_action"] != row["observed_action"]:
        violations.append("wrong_tool_or_action")
    if row["expected_context_key"] != row["observed_context_key"]:
        violations.append("context_drift")
    if row.get("expected_tone") != row.get("observed_tone"):
        violations.append("tone_drift")

    observed = metric(row, "observed_metric")
    low = metric(row, "expected_metric_min")
    high = metric(row, "expected_metric_max")
    if observed < low or observed > high:
        violations.append("business_metric_out_of_bounds")
    return violations


def classify(row: dict[str, str], seen_keys: set[str]) -> tuple[str, str, str]:
    missing = [field for field in REQUIRED if not row.get(field)]
    if missing:
        return "error", "hard_error", f"missing required fields: {', '.join(missing)}"

    try:
        metric(row, "expected_metric_min")
        metric(row, "expected_metric_max")
        metric(row, "observed_metric")
    except ValueError as exc:
        return "error", "hard_error", f"metric parse failed: {exc}"

    duplicate_key = row["duplicate_key"]
    if duplicate_key in seen_keys:
        return "blocked", "duplicate", "duplicate replay key already audited"
    seen_keys.add(duplicate_key)

    if not is_yes(row, "approved_source"):
        return "blocked", "unapproved_source", "source is not approved for first proof"
    if is_yes(row, "contains_sensitive_data"):
        return "blocked", "sensitive_data", "sensitive client or customer data present"

    violations = violation_codes(row)
    if violations and is_yes(row, "client_visible"):
        return "blocked", "client_visible_bad_output", "bad output reached a client-visible path: " + "; ".join(violations)
    if violations and not is_yes(row, "alert_generated"):
        return "review", "silent_bad_output", "workflow looked successful but violated: " + "; ".join(violations)
    if violations:
        return "review", "flagged_bad_output", "alerted run still needs review: " + "; ".join(violations)

    return "accepted", "ready", "expected action, context, tone, and metric checks passed"


def client_summary(row: dict[str, str], decision: str, reason_code: str) -> str:
    if decision == "accepted":
        return "No action needed from the client-facing view."
    if reason_code == "silent_bad_output":
        return "Needs attention: output looked successful but failed an internal expectation check."
    if reason_code == "flagged_bad_output":
        return "Needs attention: an alert fired and the output needs review before trust is restored."
    return "Needs attention: output is held before any client-facing action."


def main() -> None:
    runs = read_csv("workflow-runs.csv")
    seen_keys: set[str] = set()
    audit_rows: list[dict[str, str]] = []
    client_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in runs:
        decision, reason_code, reason = classify(row, seen_keys)
        if decision == "error":
            error_rows.append({"run_id": row.get("run_id", ""), "error": reason})
            continue

        audit_rows.append(
            {
                "run_id": row["run_id"],
                "workflow_family": row["workflow_family"],
                "source_trigger": row["source_trigger"],
                "decision": decision,
                "reason_code": reason_code,
                "reason": reason,
                "client_visibility": "safe_summary_only",
            }
        )

        if decision in {"accepted", "review"}:
            client_rows.append(
                {
                    "run_id": row["run_id"],
                    "workflow_family": row["workflow_family"],
                    "status": "ok" if decision == "accepted" else "needs_attention",
                    "client_safe_summary": client_summary(row, decision, reason_code),
                }
            )

        if decision == "review":
            review_rows.append(
                {
                    "run_id": row["run_id"],
                    "review_reason": reason,
                    "expected_action": row["expected_action"],
                    "observed_action": row["observed_action"],
                    "expected_context_key": row["expected_context_key"],
                    "observed_context_key": row["observed_context_key"],
                    "safe_next_step": "review with redacted evidence before changing production workflow behavior",
                }
            )
        elif decision == "blocked":
            blocked_rows.append(
                {
                    "run_id": row["run_id"],
                    "block_reason": reason,
                    "safe_boundary": "hold before live workflow edits, customer messages, or client-visible publication",
                }
            )

    write_csv(
        "internal-audit-ledger.csv",
        ["run_id", "workflow_family", "source_trigger", "decision", "reason_code", "reason", "client_visibility"],
        audit_rows,
    )
    write_csv(
        "client-status-view.csv",
        ["run_id", "workflow_family", "status", "client_safe_summary"],
        client_rows,
    )
    write_csv(
        "review-queue.csv",
        [
            "run_id",
            "review_reason",
            "expected_action",
            "observed_action",
            "expected_context_key",
            "observed_context_key",
            "safe_next_step",
        ],
        review_rows,
    )
    write_csv("blocked-action-queue.csv", ["run_id", "block_reason", "safe_boundary"], blocked_rows)
    write_csv("error-log.csv", ["run_id", "error"], error_rows)
    print(
        f"run_rows={len(runs)} "
        f"audit_rows={len(audit_rows)} "
        f"client_view_rows={len(client_rows)} "
        f"review_rows={len(review_rows)} "
        f"blocked_rows={len(blocked_rows)} "
        f"error_rows={len(error_rows)}"
    )


if __name__ == "__main__":
    main()
