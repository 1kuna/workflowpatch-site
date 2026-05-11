#!/usr/bin/env python3
"""Generate the WorkflowPatch care intake review demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_rows(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    ledger_rows = read_rows("intake-ledger.csv")
    review_rows = read_rows("scheduling-review-queue.csv")
    blocked_rows = read_rows("blocked-sensitive-queue.csv")
    error_rows = read_rows("error-log.csv")

    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
