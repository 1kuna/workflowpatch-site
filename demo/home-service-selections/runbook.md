# WorkflowPatch Home-Service Selections Runbook

This mock proof shows a safe first slice for a home-service Airtable and Fillout system.

## Inputs

- `fillout-selection-submissions.csv`: mock sales-team selection rows.
- `master-items-catalog.csv`: active and held master catalog items.
- `project-records.csv`: project and brand state.

## Outputs

- `project-selection-ledger.csv`: accepted or warning rows ready for project review.
- `vendor-order-draft-queue.csv`: vendor order rows that are drafts only.
- `exception-log.csv`: blocked or review rows with a next step.

## Acceptance Checks

- Active catalog items in allowed rooms create ledger rows.
- Approved rows can create vendor order drafts, but no vendor send happens.
- Phase-held, unknown, paused, or malformed rows stay visible in the exception log.
- The handoff names exactly what would need approval before live Airtable writes or vendor communication.

## Boundary

This demo uses mock data only. It does not connect to Airtable, Fillout, vendors, customer records, accounting systems, or live project records.
