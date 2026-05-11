# Finance Ops Handoff Proof Runbook

This proof demonstrates one CRM/forms/inbox-to-finance-ops handoff without connecting to live Zoho, Xero, Google Drive, CRM, email, payroll, tax, or accounting systems.

## Inputs

- `zoho-events.csv`: redacted or synthetic CRM, forms, and inbox-style events.
- `account-map.csv`: approved account-to-Xero, CRM-owner, finance-owner, and Drive-root map.
- `destination-policy.csv`: destination rules for Xero drafts, Drive/CRM handoffs, customer messages, and excluded sensitive finance actions.

## Outputs

- `handoff-ledger.csv`: source events that can become reviewed handoff artifacts.
- `approval-queue.csv`: events that need a finance or operations owner to approve, narrow, or block before any write.
- `exception-queue.csv`: duplicate or incomplete rows that should not be replayed silently.
- `error-log.csv`: impossible rows such as unknown accounts or destination policies.

## Guardrails

- Xero output is a draft/write-plan only, not payment approval or accounting export.
- Customer-facing messages, payroll, tax, compliance, and payment actions stay out of the first proof.
- Duplicate correlation ids are blocked before any repeated side effect.
- Unknown accounts become hard errors instead of guessed CRM/Xero contacts.
- Finance-owner review is required whenever the destination policy or source event says review is needed.

## Acceptance Checks

1. Valid Zoho events produce reviewed handoff ledger rows.
2. Customer-facing or finance-sensitive rows enter the approval queue.
3. Duplicate correlation ids enter the exception queue.
4. Unknown account ids produce hard errors.
5. No live finance, CRM, Drive, email, payroll, tax, or compliance action is performed by the demo.

## First Client Slice

For a live client, start with one repeated manual handoff: one source event/export, one destination contract, allowed automatic writes, review-gated fields, and one failure example. The first sprint should produce a ledger, approval queue, exception/error rows, and a written runbook before broader contractor, accounting, payout, tax, or company-wide automation work is considered.
