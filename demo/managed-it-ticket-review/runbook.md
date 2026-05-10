# Managed IT Ticket Review Demo Runbook

Purpose: prove a managed-IT support, onboarding, or account-review workflow with sanitized exports before touching live PSA/helpdesk credentials, endpoint data, security findings, client secrets, or customer-facing sends.

Inputs:

- `ticket-events.csv`: mock sanitized ticket, monitoring, chat, onboarding, or service activity rows.
- `client-map.csv`: mock client/account-manager lookup table.
- `review-policy.csv`: category-specific review and next-action rules.

Outputs:

- `ticket-review-ledger.csv`: rows accepted for internal account-manager, TAM, engineer, or service-lead review.
- `client-summary-draft-queue.csv`: approval-required client/internal summary candidates.
- `blocked-escalation-queue.csv`: unknown clients, security-sensitive rows, onboarding holds, duplicates, and low-confidence summaries.
- `error-log.csv`: malformed source rows and invalid extraction metadata.

Acceptance checks:

1. Clean sanitized rows enter an internal review ledger with account-manager evidence.
2. Client-facing candidates stay as approval-required drafts only.
3. Security-sensitive rows are blocked before any summary exists.
4. Unknown or non-active clients are blocked before routing.
5. Duplicate ticket patterns do not create duplicate review items.
6. Low-confidence summaries route to review instead of becoming client-visible.
7. Malformed rows create hard errors.
8. No live ticketing, PSA, Microsoft tenant, endpoint, security, client-secret, or customer-facing action is used.

Paid implementation boundary:

- Start with one sanitized export and one internal review destination.
- Write the field allow/block list before processing.
- Keep the first proof to internal review queues and approval-required drafts.
- Add live credentials, client-facing summaries, security-sensitive fields, or production writes only after separate written approval and scope.
