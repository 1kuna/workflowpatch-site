# WorkflowPatch Job Scoring Ledger Demo Runbook

This is a synthetic dry-run proof for an n8n job-search workflow. It starts from approved exported rows, scores fit, blocks duplicates and unsafe source scope, drafts Telegram review items, and writes a Sheets/Airtable-style ledger.

It does not scrape LinkedIn, log in to LinkedIn, send Telegram messages, write to Google Sheets, write to Airtable, use credentials, or touch a production account.

## Regenerate

```bash
python3 demo/job-scoring-ledger/process_job_scoring_demo.py
```

Expected output:

- `job-scoring-ledger.csv`
- `telegram-review-queue.csv`
- `blocked-job-queue.csv`
- `error-log.csv`

## QA Checks

- Every accepted row must come from `approved_export_only`.
- Duplicate `duplicate_key` rows must land in `blocked-job-queue.csv`.
- Any live-source or scraping-like row must be blocked before scoring.
- Telegram rows must be `draft_only_not_sent`.
- Missing required fields must land in `error-log.csv`.

## First Client Boundary

Use this for a first paid dry-run proof only. Live LinkedIn automation, scraping, credentials, Telegram sends, Google Sheets writes, Airtable writes, and production monitoring stay out of scope until separately approved and documented.
