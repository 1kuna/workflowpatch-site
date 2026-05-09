# WorkflowPatch C-Store Invoice Reconciliation Demo Runbook

Demo workflow:

`mock c-store invoice lines -> vendor map + pricebook -> accepted ledger + exception queue + reconciliation summary + error log`

## Inputs

- Mock invoice-line CSV with invoice id, store id, vendor name, SKU, quantity, unit price, line total, and source file.
- Mock vendor map with observed names and canonical vendor accounts.
- Mock pricebook with approved unit prices, categories, and variance limits.
- No real invoices, no credentials, no payment approvals, no vendor messages, and no connected accounts.

## Processing Rules

1. Reject rows missing `invoice_id`, `store_id`, or `vendor_sku`.
2. Reject duplicate `invoice_id + store_id + vendor_sku` lines before any spend is counted.
3. Normalize approved vendor aliases before pricebook matching.
4. Block unapproved vendors into the exception queue.
5. Block SKUs that belong to a different canonical vendor.
6. Block unit prices outside the approved pricebook variance.
7. Block line totals that do not equal `quantity * unit_price`.
8. Write safe lines to `accepted-ledger.csv` as review-ready rows, not auto-approved payments.
9. Summarize every invoice/store/vendor group in `reconciliation-summary.csv`.

## Acceptance Checks

- Accepted rows preserve invoice, store, vendor, SKU, price, total, source file, and evidence.
- Business mismatches appear in `exception-queue.csv`.
- Duplicate or malformed rows appear in `error-log.csv`.
- Reconciliation summary separates accepted spend from exception spend.
- No row is paid, exported to accounting, or sent to a vendor without human approval.

## Handoff

For a real sprint, the buyer would provide one redacted invoice/export, the matching vendor or pricebook fields, and the review destination. WorkflowPatch would keep the first build to one approved source and one review output. Payment approval, accounting writes, vendor communication, and compliance decisions stay outside the automation unless separately scoped and explicitly approved by the buyer.
