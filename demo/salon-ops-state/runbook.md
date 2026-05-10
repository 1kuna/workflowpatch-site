# WorkflowPatch Salon Ops State Demo Runbook

This demo is a mock first-proof slice for salon operations across Jotform, Zenoti-style booking events, Airtable, and Zapier.

It does not connect to live customer data, Zenoti, Jotform, Zapier, Airtable, customer messages, or production change paths.

## Inputs

- `source-events.csv`: redacted Jotform or Zenoti-style events with service, provider, appointment, consent, deposit, match, and replay fields.
- `action-policy.csv`: event-to-state and Zapier action rules.
- `field-policy.csv`: fields allowed or excluded in the first proof.

## Outputs

- `client-service-ledger.csv`: Airtable-ready state rows.
- `zapier-action-queue.csv`: dry-run action rows with customer messages held for approval.
- `blocked-event-queue.csv`: rows blocked for missing consent, deposit review, ambiguous Zenoti match, sensitive scope, unknown event type, or duplicate replay.
- `error-log.csv`: malformed events that need correction before any live workflow.

## Acceptance Checks

- No sensitive customer notes are included.
- Duplicate replay keys do not create duplicate action rows.
- Customer messages stay approval-required.
- Ambiguous Zenoti matches and deposit/payment questions are blocked before any live action.
- The proof remains a written dry run before broader salon-system implementation.
