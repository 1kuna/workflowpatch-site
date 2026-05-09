#!/usr/bin/env python3
"""Generate the WorkflowPatch commerce performance brief demo outputs."""

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


def money(value: float) -> str:
    return f"{value:.2f}"


def percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1%}"


def main() -> int:
    catalog = {row["asin"]: row for row in read_csv("product-catalog.csv")}
    market = {row["asin"]: row for row in read_csv("market-snapshots.csv")}
    royalties = {row["asin"]: row for row in read_csv("royalty-rows.csv")}
    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for ad_row in read_csv("ad-metrics.csv"):
        asin = ad_row["asin"]
        sales = float(ad_row["ad_sales"])
        spend = float(ad_row["ad_spend"])
        clicks = int(ad_row["clicks"])
        orders = int(ad_row["orders"])
        catalog_row = catalog.get(asin)
        market_row = market.get(asin)
        royalty_row = royalties.get(asin)

        if not catalog_row:
            error_rows.append({"asin": asin, "status": "error", "reason": "catalog row missing", "evidence": "cannot match ads row to product catalog"})
            continue
        if catalog_row["status"] != "active":
            blocked_rows.append({"asin": asin, "title": catalog_row["title"], "reason": "catalog status is not active", "reviewer_action": "confirm whether retired product should appear in weekly brief"})
            continue
        if not market_row:
            error_rows.append({"asin": asin, "status": "error", "reason": "market snapshot missing", "evidence": "cannot compare Ads row with BSR/price evidence"})
            continue
        if not royalty_row:
            error_rows.append({"asin": asin, "status": "error", "reason": "royalty row missing", "evidence": "cannot estimate net royalty after ad spend"})
            continue

        acos = None if sales == 0 else spend / sales
        conversion_rate = None if clicks == 0 else orders / clicks
        royalty_units = int(royalty_row["royalty_units"])
        royalty_net = float(royalty_row["royalty_net"])
        net_after_ads = royalty_net - spend
        bsr = int(market_row["best_seller_rank"])
        keepa_status = market_row["keepa_status"]
        decision = "monitor"
        reviewer_action = "No immediate action."

        if spend > 0 and orders == 0:
            decision = "pause_or_rebuild_ads"
            reviewer_action = "Review query/campaign fit before next spend."
        elif acos is not None and acos > 0.45:
            decision = "margin_review"
            reviewer_action = "Check bid, price, and product margin before scaling."
        elif keepa_status != "fresh":
            decision = "refresh_market_data"
            reviewer_action = "Refresh Keepa/BSR evidence before sending recommendation."
        elif acos is not None and acos < 0.25 and bsr < 3000:
            decision = "scale_candidate"
            reviewer_action = "Consider controlled budget increase after inventory check."

        evidence = f"ads={asin}; catalog={catalog_row['clickup_task_id']}; keepa={keepa_status}; royalty_units={royalty_units}"
        ledger_row = {
            "asin": asin,
            "title": catalog_row["title"],
            "week_start": ad_row["week_start"],
            "ad_sales": money(sales),
            "ad_spend": money(spend),
            "acos": percent(acos),
            "conversion_rate": percent(conversion_rate),
            "best_seller_rank": str(bsr),
            "royalty_net": money(royalty_net),
            "net_after_ads": money(net_after_ads),
            "decision": decision,
            "evidence": evidence,
        }
        ledger_rows.append(ledger_row)

        if decision != "monitor":
            review_rows.append(
                {
                    "asin": asin,
                    "title": catalog_row["title"],
                    "decision": decision,
                    "slack_draft": f"{catalog_row['title']}: {reviewer_action} Evidence: {evidence}.",
                    "reviewer_action": reviewer_action,
                }
            )

    write_csv(
        "performance-ledger.csv",
        ledger_rows,
        [
            "asin",
            "title",
            "week_start",
            "ad_sales",
            "ad_spend",
            "acos",
            "conversion_rate",
            "best_seller_rank",
            "royalty_net",
            "net_after_ads",
            "decision",
            "evidence",
        ],
    )
    write_csv("slack-review-queue.csv", review_rows, ["asin", "title", "decision", "slack_draft", "reviewer_action"])
    write_csv("blocked-rows.csv", blocked_rows, ["asin", "title", "reason", "reviewer_action"])
    write_csv("error-log.csv", error_rows, ["asin", "status", "reason", "evidence"])

    brief_lines = [
        "# Commerce performance brief draft",
        "",
        "Generated from mock Ads, catalog, market, and royalty rows. No client data, no connected accounts, and no outbound Slack post.",
        "",
        "## Review First",
    ]
    for row in review_rows:
        brief_lines.append(f"- {row['title']}: {row['reviewer_action']}")
    brief_lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "Claude-style narrative belongs after the ledger is validated. The brief should cite ASIN, ClickUp id, market snapshot freshness, and royalty row availability before it recommends a business action.",
            "",
            "## Blocked",
        ]
    )
    for row in blocked_rows:
        brief_lines.append(f"- {row['asin']}: {row['reason']}.")
    (ROOT / "brief-draft.md").write_text("\n".join(brief_lines) + "\n", encoding="utf-8")

    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
