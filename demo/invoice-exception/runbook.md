# WorkflowPatch Invoice Exception Demo Runbook

Demo workflow:

`mock invoice rows -> pricebook and PO checks -> accepted ledger + exception queue + error log`

## Inputs

- Mock invoice CSV with invoice id, vendor, SKU, PO number, quantity, unit price, invoice total, and source file.
- Mock pricebook CSV with approved unit prices and required PO prefixes.
- No real invoices, no secrets, no payment approvals, and no connected accounts.

## Processing Rules

1. Reject rows missing `invoice_id`.
2. Reject duplicate `invoice_id` values before any business rule runs.
3. Block unknown SKUs into the exception queue.
4. Block unit-price mismatches against the approved pricebook.
5. Block line totals that do not equal `quantity * unit_price`.
6. Block PO numbers with the wrong vendor prefix.
7. Write clean rows to `accepted-ledger.csv` as `ready_for_human_review`.
8. Never auto-approve, auto-pay, or send vendor messages.

## Acceptance Checks

- Valid rows appear in `accepted-ledger.csv`.
- Business mismatches appear in `exception-queue.csv`.
- Malformed or duplicate rows appear in `error-log.csv`.
- Every decision has short evidence a non-technical reviewer can inspect.
- The original source file name remains visible for review.

## Handoff

For a real sprint, this pattern would be wired to one approved source and one approved destination. The buyer would provide the pricebook/export shape and redacted examples first. Payment approval, vendor communication, and compliance decisions stay outside the automation unless explicitly scoped and approved by the buyer.
