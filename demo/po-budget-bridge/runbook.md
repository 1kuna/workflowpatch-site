# PO Budget Bridge Demo Runbook

This mock proof demonstrates one Airtable-to-Google-Sheets budget bridge without connecting to live Airtable bases, Google Sheets, accounting systems, or payment tools.

## Inputs

- `projects.csv`: Airtable-style project records with the approved budget sheet id.
- `airtable-purchase-orders.csv`: Airtable-style PO records with project, vendor, status, budget code, and approved amount.
- `sheet-expense-rows.csv`: mock Google Sheets budget expense rows entered by production users.

## Outputs

- `bridge-ledger.csv`: expense rows that are safe to sync because project, sheet, PO, status, budget code, and amount checks passed.
- `exception-queue.csv`: rows that need human review before any sync or write-back.
- `error-log.csv`: malformed or impossible rows that should not disappear silently.

## Guardrails

- Airtable remains the operational source of truth for projects and approved POs.
- Google Sheets remains the production budget workspace.
- The bridge validates project-to-sheet ownership before evaluating PO data.
- Cancelled POs, unknown POs, paused projects, wrong budget sheets, and over-PO amounts are blocked.
- No payment approval, vendor communication, or accounting write is performed by the demo.

## Acceptance Checks

1. Valid expense rows produce `sync_ready` bridge ledger rows.
2. Expenses over the approved PO amount enter the exception queue.
3. Cancelled POs enter the exception queue.
4. Paused projects enter the exception queue.
5. Unknown project rows produce hard errors.

## First Client Slice

For a live client, start with one project budget template, one Airtable PO table, and one sync direction. Confirm whether the destination write should be Airtable-only, Sheets-only, or a two-step review queue before any live update happens.
