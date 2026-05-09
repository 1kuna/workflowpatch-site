# Commerce Performance Brief Demo Runbook

This is a mock WorkflowPatch proof pack. It does not use client data, Amazon credentials, Keepa credentials, Slack credentials, or live connected accounts.

## Source

- `ad-metrics.csv`: weekly Amazon Ads-style metrics.
- `product-catalog.csv`: ClickUp-style product catalog rows and active/retired status.
- `market-snapshots.csv`: Keepa/BSR-style market evidence.
- `royalty-rows.csv`: weekly royalty rows.

## Transformation

`process_commerce_demo.py` joins the rows by ASIN, calculates ACOS, conversion rate, net royalty after ad spend, checks market freshness, blocks retired products, and writes evidence-backed decisions.

## Destination

- `performance-ledger.csv`: one row per active ASIN with metrics and evidence.
- `slack-review-queue.csv`: approval-required Slack draft rows for action candidates.
- `blocked-rows.csv`: products that should not enter the weekly brief.
- `error-log.csv`: missing evidence or structural failures.
- `brief-draft.md`: sample executive brief text that is grounded in ledger rows.

## Acceptance Checks

- Retired products are blocked before the brief.
- Products with spend and no orders are routed to review.
- Stale market data is routed to review before business recommendations.
- Every Slack draft cites row-level evidence.
- No Slack message, ad change, catalog write, or Amazon action happens automatically.
