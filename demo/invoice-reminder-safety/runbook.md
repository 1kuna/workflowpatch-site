# Invoice Reminder Safety Demo Runbook

This demo shows the delivery shape for an invoice follow-up workflow where customer messages must stay boring, accurate, and approval-gated.

## Scope

- Source: mock invoice ledger, mock payment events, mock customer replies, and reminder-stage policy.
- Transformation: decide whether each invoice is safe for the next reminder stage, should be paused for review, or must be blocked.
- Destination: reminder ledger, send-review queue, dispute-review queue, blocked-send queue, and error log.

## Acceptance Checks

1. Paid invoices never receive another reminder.
2. Customer replies pause automation before another template send.
3. Reminder stages are not repeated when history already shows that stage.
4. Partial payments are surfaced for human review before any customer copy is approved.
5. Missing required fields and duplicate invoice IDs land in the error log.

## Production Notes

- Do not send live reminder emails from the first build.
- Use buyer-approved invoice and payment sources only.
- Keep a replayable invoice ID, payment evidence, reply evidence, and reminder-stage state for every decision.
- Stop automated reminders when a customer replies, disputes the invoice, promises payment, or a human owner takes over.
