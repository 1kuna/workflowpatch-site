# WorkflowPatch Browser Action Ledger Demo Runbook

This is a synthetic dry-run proof for browser/API marketing workflows. It turns approved source rows into action plans, blocked scope rows, failure taxonomy rows, alert rules, and hard errors.

It does not perform live scraping, bypass anti-bot controls, manage proxies, handle credentials, submit forms, operate accounts, or touch production marketing tools.

## Regenerate

```bash
python3 demo/browser-action-ledger/process_browser_action_demo.py
```

Expected output:

- `dry-run-action-ledger.csv`
- `blocked-action-queue.csv`
- `failure-taxonomy.csv`
- `alert-rules.csv`
- `error-log.csv`

## QA Checks

- Every accepted row must come from `approved_source_only`.
- Credential, anti-bot/proxy, live form submission, live source, and duplicate rows must block.
- Selector failures and API failures must become taxonomy rows.
- Rate-limit rows must become alert-rule rows, not retry loops.
- Missing required fields must land in `error-log.csv`.

## First Client Boundary

Use this for a first paid dry-run proof only. Live scraping, anti-bot bypass, proxy management, credential handling, account operation, live form submissions, and platform-rule evasion stay excluded and may remain no-fit.
