#!/usr/bin/env python3
"""Generate the WorkflowPatch billing compliance ops proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    event_rows = read_rows("source-events.csv")
    policy_rows = read_rows("control-policy.csv")
    ledger_rows = read_rows("ops-control-ledger.csv")
    follow_up_rows = read_rows("follow-up-queue.csv")
    evidence_rows = read_rows("evidence-request-queue.csv")
    blocked_rows = read_rows("blocked-action-queue.csv")
    error_rows = read_rows("error-log.csv")

    print(f"event_rows={len(event_rows)}")
    print(f"policy_rows={len(policy_rows)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"follow_up_rows={len(follow_up_rows)}")
    print(f"evidence_rows={len(evidence_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
