#!/usr/bin/env python3
"""Generate the WorkflowPatch listing ROI scan proof outputs."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parent
TODAY = date(2026, 5, 9)


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def parse_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except ValueError:
        return None


def load_rules() -> dict[str, int]:
    rules: dict[str, int] = {}
    for row in read_csv("roi-rules.csv"):
        rules[row["rule_name"]] = int(row["value"])
    return rules


def comp_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        row["district"].strip().lower(),
        row["property_type"].strip().lower(),
        row["bedrooms"].strip(),
    )


def main() -> int:
    rules = load_rules()
    listings = read_csv("listing-snapshots.csv")
    sales = read_csv("historical-sales.csv")

    comps_by_key: dict[tuple[str, str, str], list[int]] = {}
    for row in sales:
        sale_date = parse_date(row["sale_date"])
        sale_price = parse_int(row["sale_price_aed"])
        if sale_date is None or sale_price is None:
            continue
        if (TODAY - sale_date).days > rules["recent_sale_days"]:
            continue
        comps_by_key.setdefault(comp_key(row), []).append(sale_price)

    ledger_rows: list[dict[str, str]] = []
    opportunity_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in listings:
        listing_id = row["listing_id"].strip()
        asking_price = parse_int(row["asking_price_aed"])
        listed_at = parse_date(row["listed_at"])

        if not listing_id or asking_price is None or listed_at is None:
            error_rows.append(
                {
                    "listing_id": listing_id or "missing",
                    "source": row["source"],
                    "error": "missing listing id, asking price, or valid listed date",
                    "evidence": f"asking_price_aed={row['asking_price_aed'] or 'missing'} listed_at={row['listed_at'] or 'missing'}",
                }
            )
            continue

        age_days = (TODAY - listed_at).days
        key = comp_key(row)
        comps = comps_by_key.get(key, [])
        comp_count = len(comps)
        median_comp = int(median(comps)) if comps else 0
        delta_pct = round(((median_comp - asking_price) / median_comp) * 100, 1) if median_comp else 0.0

        if age_days > rules["stale_listing_days"]:
            decision = "review"
            reason = "stale listing"
        elif comp_count < rules["min_recent_comps"]:
            decision = "review"
            reason = "insufficient recent comps"
        elif delta_pct >= rules["opportunity_discount_pct"]:
            decision = "opportunity"
            reason = "priced below recent median"
        elif delta_pct <= -rules["premium_review_pct"]:
            decision = "review"
            reason = "premium above recent median"
        else:
            decision = "ledger"
            reason = "near recent median"

        ledger_rows.append(
            {
                "listing_id": listing_id,
                "district": row["district"],
                "property_type": row["property_type"],
                "bedrooms": row["bedrooms"],
                "asking_price_aed": str(asking_price),
                "recent_comp_count": str(comp_count),
                "median_comp_price_aed": str(median_comp),
                "delta_vs_median_pct": str(delta_pct),
                "decision": decision,
                "evidence": reason,
            }
        )

        if decision == "opportunity":
            opportunity_rows.append(
                {
                    "listing_id": listing_id,
                    "district": row["district"],
                    "asking_price_aed": str(asking_price),
                    "median_comp_price_aed": str(median_comp),
                    "discount_pct": str(delta_pct),
                    "next_check": "Verify source permission, duplicate listing risk, fees, and current availability before investor review.",
                }
            )
        elif decision == "review":
            review_rows.append(
                {
                    "listing_id": listing_id,
                    "issue": reason,
                    "recent_comp_count": str(comp_count),
                    "evidence": f"age_days={age_days} delta_vs_median_pct={delta_pct}",
                    "reviewer_action": "Do not present as ROI evidence until the data issue is resolved.",
                }
            )

    write_csv(
        "comparison-ledger.csv",
        ledger_rows,
        [
            "listing_id",
            "district",
            "property_type",
            "bedrooms",
            "asking_price_aed",
            "recent_comp_count",
            "median_comp_price_aed",
            "delta_vs_median_pct",
            "decision",
            "evidence",
        ],
    )
    write_csv(
        "opportunity-queue.csv",
        opportunity_rows,
        ["listing_id", "district", "asking_price_aed", "median_comp_price_aed", "discount_pct", "next_check"],
    )
    write_csv(
        "review-queue.csv",
        review_rows,
        ["listing_id", "issue", "recent_comp_count", "evidence", "reviewer_action"],
    )
    write_csv(
        "error-log.csv",
        error_rows,
        ["listing_id", "source", "error", "evidence"],
    )

    print(f"comparison_rows={len(ledger_rows)}")
    print(f"opportunity_rows={len(opportunity_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
