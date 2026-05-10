# WorkflowPatch Venue Guest Alignment Demo Runbook

This demo is a mock first-proof slice for Vemos, Square, Mailchimp, and Airtable alignment.

It does not connect to live customer data, Vemos, Square, Mailchimp, Airtable, customer messages, payment-affecting writes, or production change paths.

## Inputs

- `source-events.csv`: redacted Vemos, Square, or Mailchimp-style events with guest key, event family, payment state, consent, match, and replay fields.
- `action-policy.csv`: event-to-state and review/action queue rules.
- `field-policy.csv`: fields allowed or excluded in the first proof.

## Outputs

- `guest-state-ledger.csv`: Airtable-ready guest or member state rows.
- `review-action-queue.csv`: dry-run review/action rows with customer messages held for approval.
- `blocked-event-queue.csv`: rows blocked for payment ambiguity, missing consent, ambiguous identity, sensitive scope, unknown event type, duplicate replay, or blocked Mailchimp status.
- `error-log.csv`: malformed events that need correction before any live workflow.

## Acceptance Checks

- Private guest notes and payment instrument details are excluded.
- Duplicate replay keys do not create duplicate action rows.
- Customer messages and marketing actions stay approval-required.
- Refund, dispute, ambiguous identity, unsubscribed, and sensitive rows block before live action.
- The proof remains written and dry-run before any broader venue-system alignment.
