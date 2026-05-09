# Research Digest Demo Runbook

This is a mock WorkflowPatch demo. It uses no live scraping, no client data, no credentials, and no connected accounts.

## Inputs

- `source-items.csv`: mock source rows from forums, directories, and public market signals.
- `watchlist.csv`: deterministic keyword weights used to classify fit.

## Command

```bash
python3 demo/research-digest/process_research_demo.py
```

## Outputs

- `digest-queue.csv`: high-fit items that are ready for a human teardown note.
- `review-queue.csv`: duplicate, stale, medium-fit, or low-fit items that need a decision before outreach.
- `source-ledger.csv`: one decision row per valid source item, with score and matched keywords.
- `error-log.csv`: malformed source rows that are blocked immediately.

## Acceptance Checks

- High-fit, recent items with buyer-intent and workflow keywords land in the digest queue.
- Duplicate source URLs are blocked for review.
- Stale items are not treated as current opportunities.
- Low-fit generic automation requests are not added directly to outreach.
- Rows missing a required source URL, title, or valid date go to the error log.

## Non-Goals

- No outbound email is sent.
- No forum reply is posted.
- No live web source is scraped.
- No claim is made that scoring is a substitute for human judgment.
