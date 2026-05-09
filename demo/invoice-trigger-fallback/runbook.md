# Invoice Trigger Fallback Demo Runbook

Purpose: prove an invoice workflow can detect delayed or missing QuickBooks Online trigger events before staff wait on an instant trigger or a client sees an incomplete invoice email.

Inputs:

- `qbo-invoices.csv`: mock QuickBooks invoice export with created time, customer email, amount, invoice status, and Stripe-link readiness time.
- `zap-trigger-runs.csv`: mock Zap run history for invoice trigger events.

Outputs:

- `invoice-event-ledger.csv`: invoices recovered into a reviewable invoice-email state.
- `delayed-invoice-review.csv`: invoices that were missing or delayed enough to need fallback review.
- `blocked-send-queue.csv`: duplicate, void, or payment-link-not-ready rows blocked before any customer email.
- `error-log.csv`: malformed invoices blocked before any review or send path.

Acceptance checks:

1. Timely invoice triggers become review-ready ledger rows.
2. Delayed triggers are recovered into the ledger and also flagged for review.
3. Missing trigger events become fallback review rows.
4. Duplicate trigger runs are blocked before duplicate customer sends.
5. Invoices without a ready Stripe/payment link are blocked before a client-facing email.
6. Voided invoices and missing customer emails do not enter the send path.
7. No live QuickBooks, Zapier, Stripe, Gmail, or client-email action is used.

Paid implementation boundary:

- Start with one invoice source, one Zap run-history source, and one review queue.
- Use redacted invoice samples or exports first.
- Treat upstream QuickBooks/Zapier trigger behavior as evidence to work around, not something WorkflowPatch can guarantee to fix.
- Keep customer-facing invoice emails approval-required until the fallback ledger is accepted.
