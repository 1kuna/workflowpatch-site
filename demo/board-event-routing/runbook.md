# Board Event Routing Demo Runbook

Purpose: prove a Monday.com-style board event can be routed without using sensitive client, case, or matter data.

Inputs:

- `board-events.csv`: mock redacted board events.
- `routing-policy.csv`: allowed status-to-destination rules.

Outputs:

- `routing-ledger.csv`: rows safe enough to route.
- `review-queue.csv`: rows needing human review before any action.
- `error-log.csv`: malformed rows blocked before routing.

Acceptance checks:

1. Sensitive rows are blocked into `manual_scope_review`.
2. Unknown statuses are held until a policy exists.
3. Duplicate item/status events do not create another task.
4. Missing owner emails become hard errors.
5. No live Monday.com, n8n, email, CRM, or legal matter data is used.

Paid implementation boundary:

- Start with one redacted board schema, one event family, and one destination.
- Do not request confidential case data for the first proof.
- Use dry-run ledgers before live writes.
