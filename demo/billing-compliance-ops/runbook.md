# Billing Compliance Ops Proof Runbook

This proof is a dry-run operating layer for admin, billing, evidence, and deadline work. It uses synthetic rows only.

## Source

- `source-events.csv` contains synthetic Stripe, inbox, auditor, Holded, Slack, Drive, and CRM-style events.
- `control-policy.csv` defines what can be staged, reviewed, or blocked.

## Transformation

- Validate required account, amount, due-date, and source-evidence fields.
- Route safe internal work to the billing-control ledger or follow-up queue.
- Route audit evidence requests to owner review without making compliance claims.
- Block supplier payment, tax filing, payroll, bank, and customer-facing send actions.

## Destination

- `ops-control-ledger.csv` records accepted and review-needed events.
- `follow-up-queue.csv` stages internal follow-up drafts and owner approvals.
- `evidence-request-queue.csv` tracks audit evidence collection.
- `blocked-action-queue.csv` holds payment, tax, and external-send requests.
- `error-log.csv` preserves hard stops.

## Production Boundary

No live Stripe, Holded, Odoo, HubSpot, Salesforce, Google Workspace, Slack, bank, payroll, accounting, tax, customer, vendor, auditor, or production writes are performed. No tax, legal, accounting, audit, privacy, compliance, HR, payroll, banking, or employment advice is provided.
