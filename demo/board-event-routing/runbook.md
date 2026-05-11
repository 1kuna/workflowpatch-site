# Monday Board Routing Proof Runbook

Purpose: prove a redacted Monday.com-style board event can be validated and routed through a draft n8n support path without using sensitive legal, client, case, or matter data.

Inputs:

- `board-events.csv`: mock redacted board events.
- `routing-policy.csv`: allowed status-to-destination rules.

Outputs:

- `routing-ledger.csv`: rows safe enough for a dry-run route or support handoff.
- `review-queue.csv`: rows needing human review before any action or live write.
- `error-log.csv`: malformed rows blocked before routing.

Acceptance checks:

1. Sensitive rows are blocked into `manual_scope_review`.
2. Unknown statuses are held until a policy exists.
3. Duplicate item/status events do not create another task.
4. Missing owner emails become hard errors.
5. No live Monday.com, n8n, email, CRM, legal advice, confidential case data, or matter data is used.

Paid implementation boundary:

- Start with one redacted board schema, one non-sensitive event family, and one destination or review queue.
- Do not request confidential legal, client, case, or matter data for the first proof.
- Use dry-run ledgers and blocked-row review before live writes or broader support.
