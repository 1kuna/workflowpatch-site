#!/usr/bin/env python3
"""Generate the WorkflowPatch automation-builder audit proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T06:24:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def has_all_required(submission: dict[str, str], required_contract: str) -> bool:
    provided = set(submission["input_contract"].split())
    required = set(required_contract.split())
    return required.issubset(provided)


def main() -> None:
    slices = {row["slice_id"]: row for row in read_csv("workflow-slices.csv")}
    submissions = read_csv("builder-submissions.csv")
    audit_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    test_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for submission in submissions:
        submission_id = submission["submission_id"]
        workflow = slices.get(submission["slice_id"])
        if workflow is None:
            error_rows.append(
                {
                    "submission_id": submission_id,
                    "error_code": "unknown_workflow_slice",
                    "error_detail": "Submitted builder artifact references a workflow slice that is not registered.",
                }
            )
            continue

        findings: list[str] = []
        score = 100

        if not has_all_required(submission, workflow["required_contract"]):
            findings.append("input_contract_incomplete")
            score -= 20
        if submission["dedupe_key"] != workflow["dedupe_key"]:
            findings.append("dedupe_key_missing_or_mismatched")
            score -= 20
        if not submission["retry_policy"] or "rerunning whole scenario" in submission["retry_policy"]:
            findings.append("unsafe_retry_policy")
            score -= 15
        if submission["conflict_queue"].lower() != "yes":
            findings.append("missing_conflict_queue")
            score -= 15
        if int(submission["test_cases"]) < 3:
            findings.append("thin_test_matrix")
            score -= 15
        if submission["source_links"].lower() != "yes" or float(submission["confidence"]) < 0.80:
            findings.append("weak_source_evidence_or_confidence")
            score -= 15

        verdict = "ready_for_paid_proof" if not findings else "needs_review_before_production"
        audit_rows.append(
            {
                "submission_id": submission_id,
                "slice_id": workflow["slice_id"],
                "workflow_name": workflow["workflow_name"],
                "score": str(max(score, 0)),
                "verdict": verdict,
                "review_summary": "ok" if not findings else ";".join(findings),
                "processed_at": GENERATED_AT,
            }
        )

        if findings:
            review_rows.append(
                {
                    "submission_id": submission_id,
                    "workflow_name": workflow["workflow_name"],
                    "risk_flags": ";".join(findings),
                    "review_action": "Ask for missing contract, dedupe, retry, conflict, test, or source evidence before trusting the build.",
                }
            )

        test_rows.extend(
            [
                {
                    "submission_id": submission_id,
                    "workflow_name": workflow["workflow_name"],
                    "test_case": "happy_path",
                    "expected": "Valid source row reaches reviewed destination ledger.",
                },
                {
                    "submission_id": submission_id,
                    "workflow_name": workflow["workflow_name"],
                    "test_case": "duplicate_replay",
                    "expected": "Duplicate key is blocked or idempotently ignored.",
                },
                {
                    "submission_id": submission_id,
                    "workflow_name": workflow["workflow_name"],
                    "test_case": "bad_payload",
                    "expected": "Missing required field routes to review or error, not live write.",
                },
                {
                    "submission_id": submission_id,
                    "workflow_name": workflow["workflow_name"],
                    "test_case": "partial_destination_failure",
                    "expected": "Retry is bounded and leaves a visible error ledger.",
                },
            ]
        )

    write_csv(
        "audit-ledger.csv",
        audit_rows,
        ["submission_id", "slice_id", "workflow_name", "score", "verdict", "review_summary", "processed_at"],
    )
    write_csv(
        "risk-review-queue.csv",
        review_rows,
        ["submission_id", "workflow_name", "risk_flags", "review_action"],
    )
    write_csv(
        "reusable-test-matrix.csv",
        test_rows,
        ["submission_id", "workflow_name", "test_case", "expected"],
    )
    write_csv("error-log.csv", error_rows, ["submission_id", "error_code", "error_detail"])

    handoff = [
        "# Builder Quality Handoff",
        "",
        f"Generated: {GENERATED_AT}",
        "",
        f"- Builder submissions audited: {len(submissions)}",
        f"- Audit ledger rows: {len(audit_rows)}",
        f"- Risk review rows: {len(review_rows)}",
        f"- Reusable test rows: {len(test_rows)}",
        f"- Hard errors: {len(error_rows)}",
        "",
        "Use this handoff to evaluate workflow artifacts, not people. The audit checks whether the build evidence names the input contract, dedupe key, retry/error behavior, conflict queue, reusable tests, and source evidence before any production trust.",
    ]
    (ROOT / "builder-quality-handoff.md").write_text("\n".join(handoff) + "\n", encoding="utf-8")

    print(f"submission_rows={len(submissions)}")
    print(f"audit_rows={len(audit_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"test_rows={len(test_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
