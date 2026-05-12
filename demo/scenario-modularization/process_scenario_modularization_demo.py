#!/usr/bin/env python3
"""Generate the WorkflowPatch scenario modularization proof outputs."""

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


def index_scenarios() -> dict[str, dict[str, str]]:
    return {row["scenario_id"]: row for row in read_csv("scenario-inventory.csv")}


def refactor_decision(boundary: dict[str, str]) -> tuple[str, str, str]:
    policy = boundary["side_effect_policy"].lower()
    risk = boundary["risk_level"].lower()
    reason = boundary["extraction_reason"]

    if "not reused" in reason.lower() or "single-scenario" in policy:
        return (
            "document_inline",
            "Keep inline for now; add naming and runbook standard only.",
            "Avoid extracting a module that is not reused yet.",
        )
    if "no side effects" in policy or "read and cache" in policy:
        return (
            "extract_first",
            "Extract before changing downstream writes.",
            "Low write-risk boundary makes a safe first proof.",
        )
    if "blocks before" in policy:
        return (
            "extract_with_review_gate",
            "Extract behind a reviewable blocked-row ledger.",
            "Boundary reduces side effects by stopping bad rows earlier.",
        )
    if risk == "high":
        return (
            "dry_run_before_live",
            "Run as a dry-run module until usage and ledger counts match.",
            "High-cost vendor or LLM work needs proof before live writes.",
        )
    return (
        "extract_after_idempotency_gate",
        "Extract only after the idempotency key is enforced.",
        "Side effects need a replay-safe key before reuse.",
    )


def build_refactor_ledger() -> list[dict[str, str]]:
    scenarios = index_scenarios()
    rows: list[dict[str, str]] = []

    for boundary in read_csv("module-boundaries.csv"):
        scenario = scenarios[boundary["scenario_id"]]
        decision, first_action, evidence = refactor_decision(boundary)
        rows.append(
            {
                "boundary_id": boundary["boundary_id"],
                "scenario_name": scenario["scenario_name"],
                "boundary_name": boundary["boundary_name"],
                "decision": decision,
                "first_action": first_action,
                "idempotency_key": boundary["idempotency_key"],
                "risk_level": boundary["risk_level"],
                "evidence": evidence,
                "reviewer_action": boundary["reviewer_action"],
            }
        )

    return rows


def build_error_paths() -> list[dict[str, str]]:
    plans = {row["boundary_id"]: row for row in read_csv("idempotency-plan.csv")}
    rows: list[dict[str, str]] = []

    for boundary in read_csv("module-boundaries.csv"):
        plan = plans[boundary["boundary_id"]]
        policy = boundary["side_effect_policy"].lower()
        if "no side effects" in policy:
            failure_class = "schema_or_payload_mismatch"
            queue = "normalization_review"
            action = "Hold row before any downstream module sees it."
        elif "blocks before" in policy:
            failure_class = "missing_required_mapping"
            queue = "blocked_preflight_queue"
            action = "Write blocked reason and require reviewer fix before replay."
        elif "cache" in policy:
            failure_class = "cache_key_missing_or_stale"
            queue = "cache_review_queue"
            action = "Skip vendor call until cache policy is clear."
        elif "single-scenario" in policy:
            failure_class = "delivery_window_conflict"
            queue = "report_delivery_review"
            action = "Rebuild report draft before delivery, then log final send."
        else:
            failure_class = "vendor_or_llm_limit"
            queue = "retry_after_queue"
            action = "Stop immediate retries and wait for cooldown or approval."

        rows.append(
            {
                "boundary_id": boundary["boundary_id"],
                "boundary_name": boundary["boundary_name"],
                "failure_class": failure_class,
                "queue_or_ledger": queue,
                "duplicate_behavior": plan["duplicate_behavior"],
                "review_signal": plan["review_signal"],
                "operator_action": action,
            }
        )

    return rows


def main() -> int:
    refactor_rows = build_refactor_ledger()
    error_rows = build_error_paths()

    write_csv(
        "refactor-ledger.csv",
        refactor_rows,
        [
            "boundary_id",
            "scenario_name",
            "boundary_name",
            "decision",
            "first_action",
            "idempotency_key",
            "risk_level",
            "evidence",
            "reviewer_action",
        ],
    )
    write_csv(
        "error-paths.csv",
        error_rows,
        [
            "boundary_id",
            "boundary_name",
            "failure_class",
            "queue_or_ledger",
            "duplicate_behavior",
            "review_signal",
            "operator_action",
        ],
    )

    extract_rows = [row for row in refactor_rows if row["decision"] != "document_inline"]
    review_rows = [row for row in error_rows if "review" in row["queue_or_ledger"]]

    print(f"boundary_rows={len(refactor_rows)}")
    print(f"extract_rows={len(extract_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"error_path_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
