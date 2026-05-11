# Silent Output Audit Runbook

This mock proof is for n8n or Make workflows that do not crash, but still produce bad output.

## Input

- `workflow-runs.csv`: synthetic workflow run rows with expected action, observed action, expected context, observed context, tone, business metric range, alert state, client visibility, source approval, sensitivity flag, and duplicate key.
- `expected-output-rules.csv`: small rule map showing why each check exists and how it should be summarized safely.

## Output

- `internal-audit-ledger.csv`: one row per non-malformed run with decision, reason code, reason, and client visibility boundary.
- `client-status-view.csv`: sanitized status rows that a client could inspect without raw debug detail.
- `review-queue.csv`: silent or flagged bad-output rows that need human review.
- `blocked-action-queue.csv`: unsafe rows that should not proceed.
- `error-log.csv`: malformed rows that fail loudly instead of being guessed through.

## Acceptance Checks

- Clean run reaches the internal audit ledger and client-safe view.
- Wrong action, wrong context, tone drift, or business metric drift reaches review or block.
- A client-visible bad output blocks before any live send.
- Duplicate replay key blocks.
- Unapproved source and sensitive-data rows block.
- Missing required fields reach the hard error log.

## Boundaries

- No live workflow credentials.
- No production n8n, Make, CRM, Slack, email, or customer-system writes.
- No client-facing messages are sent.
- Raw debug detail is separated from the client-safe view.
- Ongoing monitoring is a later scope, not implied by the first proof.
