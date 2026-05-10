# RevOps Integration QA Demo Runbook

Purpose: prove a HubSpot, Salesforce, Marketo, BigQuery, CSV, or agency-overflow QA workflow with sanitized exports before touching live CRM credentials, client workspaces, customer records, campaign sends, or production writes.

Inputs:

- `integration-events.csv`: mock integration/export, sync issue, import preview, attribution, or handoff rows.
- `client-map.csv`: mock client, owner, review queue, account status, and approved system boundary table.
- `qa-policy.csv`: risk-specific summary, review reason, and next-action rules.

Outputs:

- `qa-ledger.csv`: rows accepted for owner or implementation-review queue.
- `owner-handoff-queue.csv`: approval-required owner summary candidates.
- `blocked-record-queue.csv`: unknown clients, account holds, unapproved systems, sensitive rows, destructive changes, duplicates, and low-confidence QA rows.
- `error-log.csv`: malformed source rows and invalid extraction metadata.

Acceptance checks:

1. Known active clients with approved source and destination systems enter an owner review ledger.
2. Client-facing candidates stay as approval-required drafts only.
3. Sensitive details, destructive or policy-affecting changes, and unapproved system boundaries are blocked.
4. Unknown or non-active clients are blocked before routing.
5. Duplicate integration events do not create duplicate review rows.
6. Low-confidence rows route to review instead of becoming sync-ready.
7. Malformed rows create hard errors.
8. No live CRM, warehouse, campaign, billing, client-system, or production write is used.

Paid implementation boundary:

- Start with one sanitized export and one review destination.
- Write the field allow/block list before processing.
- Keep the first proof to owner review queues and approval-required handoff drafts.
- Add live credentials, client-facing output, destructive writes, or production syncs only after separate written approval and scope.
