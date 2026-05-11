#!/usr/bin/env python3
"""Generate the WorkflowPatch GTM signal routing proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    event_rows = read_rows("source-events.csv")
    policy_rows = read_rows("scoring-policy.csv")
    ledger_rows = read_rows("gtm-signal-ledger.csv")
    review_rows = read_rows("owner-review-queue.csv")
    crm_preview_rows = read_rows("crm-update-preview.csv")
    blocked_rows = read_rows("blocked-action-queue.csv")
    error_rows = read_rows("error-log.csv")

    print(f"event_rows={len(event_rows)}")
    print(f"policy_rows={len(policy_rows)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"crm_preview_rows={len(crm_preview_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
