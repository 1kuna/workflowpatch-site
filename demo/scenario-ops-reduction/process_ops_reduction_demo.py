#!/usr/bin/env python3
"""Generate the WorkflowPatch scenario ops-reduction proof outputs."""

from __future__ import annotations

import csv
from collections import defaultdict
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


def index_rules() -> dict[str, list[dict[str, str]]]:
    rules: dict[str, list[dict[str, str]]] = defaultdict(list)
    for rule in read_csv("patch-rules.csv"):
        rules[rule["scenario_name"]].append(rule)
    return rules


def main() -> int:
    rules_by_scenario = index_rules()
    seen_success: dict[tuple[str, str, str], dict[str, str]] = {}
    first_digest_trigger: set[tuple[str, str]] = set()
    reduction_rows: list[dict[str, str]] = []
    patch_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in read_csv("scenario-runs.csv"):
        scenario = row["scenario_name"]
        run_id = row["run_id"]
        status = row["status"]
        trigger_key = row["trigger_key"]
        source_record_id = row["source_record_id"]
        output_hash = row["output_hash"]
        operations = int(row["module_operations"])
        matched_rule = ""
        decision = "keep_baseline"
        evidence = "first useful run for this source"
        ops_saved = 0

        if status == "success" and output_hash:
            success_key = (scenario, source_record_id, output_hash)
            if success_key in seen_success:
                matched_rule = "RULE-01" if "lead" in scenario else "RULE-05"
                decision = "skip_duplicate"
                evidence = f"same source/output as {seen_success[success_key]['run_id']}"
                ops_saved = operations
            else:
                seen_success[success_key] = row

        if scenario == "company-research-digest" and status == "success":
            digest_key = (scenario, trigger_key)
            if digest_key in first_digest_trigger:
                matched_rule = "RULE-03"
                decision = "skip_overlapping_scheduler_run"
                evidence = "same digest trigger already processed in this window"
                ops_saved = operations
            else:
                first_digest_trigger.add(digest_key)

        if status == "error":
            code = row["error_code"]
            if code == "429":
                matched_rule = "RULE-02"
                decision = "retry_after_queue"
                evidence = "rate-limit error should not be retried immediately"
                ops_saved = operations
            elif code == "MISSING_FIELD":
                matched_rule = "RULE-04"
                decision = "block_before_expensive_modules"
                evidence = "missing filter should stop before research/LLM work"
                ops_saved = operations
            elif code == "MAP_MISSING":
                matched_rule = "RULE-06"
                decision = "block_until_mapping_exists"
                evidence = "vendor mapping missing before reconciliation"
                ops_saved = operations
            else:
                error_rows.append(
                    {
                        "run_id": run_id,
                        "status": "error",
                        "reason": f"unmapped error code {code}",
                        "evidence": row["notes"],
                    }
                )

        reduction_rows.append(
            {
                "run_id": run_id,
                "scenario_name": scenario,
                "decision": decision,
                "matched_rule": matched_rule or "baseline",
                "operations_observed": str(operations),
                "estimated_operations_saved": str(ops_saved),
                "evidence": evidence,
            }
        )

    for rule in read_csv("patch-rules.csv"):
        impacted = [row for row in reduction_rows if row["matched_rule"] == rule["rule_id"]]
        patch_rows.append(
            {
                "rule_id": rule["rule_id"],
                "scenario_name": rule["scenario_name"],
                "patch_action": rule["patch_action"],
                "impacted_runs": str(len(impacted)),
                "estimated_operations_saved": str(sum(int(row["estimated_operations_saved"]) for row in impacted)),
                "reviewer_action": rule["reviewer_action"],
            }
        )

    write_csv(
        "ops-reduction-ledger.csv",
        reduction_rows,
        [
            "run_id",
            "scenario_name",
            "decision",
            "matched_rule",
            "operations_observed",
            "estimated_operations_saved",
            "evidence",
        ],
    )
    write_csv(
        "patch-plan.csv",
        patch_rows,
        [
            "rule_id",
            "scenario_name",
            "patch_action",
            "impacted_runs",
            "estimated_operations_saved",
            "reviewer_action",
        ],
    )
    write_csv("error-log.csv", error_rows, ["run_id", "status", "reason", "evidence"])

    print(f"scenario_rows={len(reduction_rows)}")
    print(f"patch_rows={len(patch_rows)}")
    print(f"ops_saved={sum(int(row['estimated_operations_saved']) for row in reduction_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
