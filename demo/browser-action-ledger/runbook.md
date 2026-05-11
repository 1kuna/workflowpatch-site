# WorkflowPatch Browser Action Reliability Proof Runbook

This is a dry-run proof for browser/API workflows that need reliability evidence before any live action. It turns approved source rows into action plans, blocked scope rows, failure taxonomy rows, alert rules, and hard errors.

It does not perform live scraping, bypass anti-bot controls, manage proxies, handle credentials, submit forms, operate accounts, or touch production marketing tools.

## First Paid Slice

- Source: one approved-source export, allowed API row sample, or redacted target-flow note set.
- Transformation: browser/API action planning, dry-run state logging, duplicate checks, selector/API/rate-limit taxonomy, alert rules, and a written runbook.
- Destination: dry-run action ledger, blocked-action queue, failure taxonomy, alert rules, error log, and handoff notes.
- Useful sample: 10 to 30 approved rows, expected state transitions, allowed action boundaries, known selector/API failure examples, retry expectations, and blocked/error examples.

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
