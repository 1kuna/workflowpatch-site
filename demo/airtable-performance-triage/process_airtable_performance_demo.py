#!/usr/bin/env python3
"""Generate the WorkflowPatch Airtable performance triage demo outputs."""

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


def build_base_index() -> dict[str, dict[str, str]]:
    return {row["base_id"]: row for row in read_csv("base-map.csv")}


def decide_path(path: dict[str, str]) -> tuple[str, str, str]:
    runtime = int(path["script_runtime_seconds"])
    delay = int(path["queue_delay_minutes"])
    downstream = int(path["downstream_automations"])
    touched = int(path["records_touched"])

    if runtime >= 180:
        return (
            "heavy_script_timeout",
            "profile reads and offload the expensive worker before live edits",
            "high",
        )
    if delay >= 45 and downstream >= 4:
        return (
            "queue_pressure_from_cascading_automations",
            "split validation from side effects and add a final-state gate",
            "medium",
        )
    if touched >= 2000:
        return (
            "full_base_scan_risk",
            "replace full scans with a changed-record ledger",
            "high",
        )
    return (
        "linked_record_write_fanout",
        "reduce linked writes and add a reviewable replay path",
        "medium",
    )


def build_triage_rows() -> list[dict[str, str]]:
    bases = build_base_index()
    rows: list[dict[str, str]] = []

    for path in read_csv("slow-paths.csv"):
        base = bases[path["base_id"]]
        diagnosis, first_action, risk = decide_path(path)
        rows.append(
            {
                "path_id": path["path_id"],
                "base_name": base["base_name"],
                "path_name": path["path_name"],
                "primary_symptom": base["primary_symptom"],
                "diagnosis": diagnosis,
                "first_action": first_action,
                "risk_level": risk,
                "evidence_needed": "run history, redacted path map, record counts, and failure examples",
            }
        )

    return rows


def build_offload_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for triage in build_triage_rows():
        if "timeout" in triage["diagnosis"] or "full_base" in triage["diagnosis"]:
            offload = "external worker with dry-run output ledger"
            keep = "trigger, approval state, and review UI"
        elif "cascading" in triage["diagnosis"]:
            offload = "notification or side-effect batching"
            keep = "intake validation and owner assignment"
        else:
            offload = "linked-record fanout only if replay tests fail"
            keep = "core status update and reviewer decision"

        rows.append(
            {
                "path_id": triage["path_id"],
                "keep_in_airtable": keep,
                "offload_candidate": offload,
                "review_queue": f"{triage['path_id'].lower()}_review",
                "blocked_reason_policy": "block ambiguous keys, duplicate rows, and missing owner fields",
                "next_check": "compare three dry-run outputs against current expected result",
            }
        )

    return rows


def main() -> int:
    triage_rows = build_triage_rows()
    offload_rows = build_offload_rows()

    write_csv(
        "triage-ledger.csv",
        triage_rows,
        [
            "path_id",
            "base_name",
            "path_name",
            "primary_symptom",
            "diagnosis",
            "first_action",
            "risk_level",
            "evidence_needed",
        ],
    )
    write_csv(
        "offload-plan.csv",
        offload_rows,
        [
            "path_id",
            "keep_in_airtable",
            "offload_candidate",
            "review_queue",
            "blocked_reason_policy",
            "next_check",
        ],
    )

    high_risk = [row for row in triage_rows if row["risk_level"] == "high"]
    offload = [row for row in offload_rows if "external worker" in row["offload_candidate"]]

    print(f"triage_rows={len(triage_rows)}")
    print(f"high_risk_rows={len(high_risk)}")
    print(f"offload_rows={len(offload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
