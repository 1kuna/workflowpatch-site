# CRM Sync Demo Runbook

This is a mock WorkflowPatch demo. It uses no client data, no credentials, and no connected CRM accounts.

## Inputs

- `contact-map.csv`: current known mapping between Close contacts and GHL contacts.
- `close-appointments.csv`: mock appointment events from Close.
- `ghl-contact-changes.csv`: mock contact-field changes from GHL.

## Command

```bash
python3 demo/crm-sync/process_crm_sync_demo.py
```

## Outputs

- `sync-ledger.csv`: rows that are safe for a reviewer to approve for sync.
- `conflict-queue.csv`: business conflicts that need a human decision before any write happens.
- `error-log.csv`: malformed or missing-identity rows that are blocked immediately.

## Acceptance Checks

- A valid Close appointment for a mapped contact lands in the sync ledger.
- A valid GHL contact change for a mapped contact lands in the sync ledger.
- A Close appointment whose email belongs to a different Close contact is blocked.
- An unmapped Close appointment becomes a conflict, not a blind contact create.
- A GHL change whose identifiers disagree with the contact map is blocked.
- A row with no usable identity is written to the error log.

## Non-Goals

- No CRM write is executed.
- No contact is created automatically.
- No phone, SMS, email, or payment action is triggered.
- No promise is made about Close, GHL, or any third-party API availability.
