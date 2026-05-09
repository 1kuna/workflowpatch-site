# Listing ROI Scan Demo Runbook

This is a mock WorkflowPatch proof surface. It shows a small real-estate research workflow without live scraping, portal credentials, investor data, or investment advice.

## Inputs

- `listing-snapshots.csv`: mock rows captured from approved listing sources or exported by the buyer.
- `historical-sales.csv`: mock comparable sales rows.
- `roi-rules.csv`: simple thresholds for recency, discount, stale listings, and minimum comps.

## Output Artifacts

- `comparison-ledger.csv`: one scored row per valid listing with comp count, median comp price, discount/premium, decision, and evidence.
- `opportunity-queue.csv`: only listings that pass the first proof threshold.
- `review-queue.csv`: stale listings, thin comp sets, and premium/outlier rows that need manual review.
- `error-log.csv`: malformed rows that should not disappear silently.

## First Paid Sprint Shape

1. Confirm the buyer has permission to use the listing and sales data sources.
2. Pick one or two sources, not the whole market.
3. Load a small exported sample into the same ledger shape.
4. Produce 2-3 concrete opportunity or false-positive cases for investor review.
5. Document what must change before this becomes production: data provider, scraping limits, storage, dedupe, update frequency, and reviewer ownership.

No live portal scraping, legal advice, or investment recommendation belongs in the first proof.
