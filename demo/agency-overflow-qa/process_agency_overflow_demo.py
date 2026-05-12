#!/usr/bin/env python3
"""Generate the WorkflowPatch agency overflow QA proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def classify(row: dict[str, str]) -> tuple[str, str]:
    required = ("request_id", "partner", "source_type", "target_destination", "requested_action")
    missing = [field for field in required if not row.get(field)]
    if missing:
        return "error", f"missing required fields: {', '.join(missing)}"

    action = row["requested_action"].lower()
    sensitivity = row.get("sensitivity", "").lower()
    client_visible = row.get("client_visible", "").lower() == "yes"

    if sensitivity in {"secret", "credential"}:
        return "blocked", "secret or credential appears in sample"
    if sensitivity == "scope" or "take over" in action or "support bench" in action:
        return "blocked", "request is broad retainer or bench availability"
    if client_visible or "update live" in action or "production" in action:
        return "review", "client-visible or live-system action needs partner approval"
    return "accepted", "internal QA artifact can be drafted"


def main() -> None:
    requests = read_csv("agency-requests.csv")
    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in requests:
        decision, reason = classify(row)
        if decision == "error":
            error_rows.append({"request_id": row.get("request_id", ""), "error": reason})
            continue

        ledger_rows.append(
            {
                "request_id": row["request_id"],
                "partner": row["partner"],
                "source_type": row["source_type"],
                "target_destination": row["target_destination"],
                "qa_decision": decision,
                "reason": reason,
                "next_artifact": "qa ledger" if decision == "accepted" else "approval or block queue",
            }
        )

        if decision == "review":
            review_rows.append(
                {
                    "request_id": row["request_id"],
                    "review_reason": reason,
                    "safe_next_step": "produce dry-run output only",
                    "approval_needed": "partner approval before client-facing output or live write",
                }
            )
        elif decision == "blocked":
            blocked_rows.append(
                {
                    "request_id": row["request_id"],
                    "block_reason": reason,
                    "safe_boundary": "rescope to one redacted source, one transformation, one review destination",
                }
            )

    write_csv(
        "qa-ledger.csv",
        ["request_id", "partner", "source_type", "target_destination", "qa_decision", "reason", "next_artifact"],
        ledger_rows,
    )
    write_csv("review-queue.csv", ["request_id", "review_reason", "safe_next_step", "approval_needed"], review_rows)
    write_csv("blocked-scope.csv", ["request_id", "block_reason", "safe_boundary"], blocked_rows)
    write_csv("error-log.csv", ["request_id", "error"], error_rows)
    print(
        f"ledger_rows={len(ledger_rows)} "
        f"review_rows={len(review_rows)} "
        f"blocked_rows={len(blocked_rows)} "
        f"error_rows={len(error_rows)}"
    )


if __name__ == "__main__":
    main()
