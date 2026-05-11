# Staffing Order Intake Guardrail Proof Runbook

Purpose: prove a staffing order-intake guardrail before touching a live inbox, Make scenario, Monday.com board, staffing-client data, or production write path.

Useful first buyer sample:

- one redacted forwarded order email that should create a draft row,
- one order that should be blocked because the client does not match cleanly,
- the Monday client lookup field and required order fields,
- the alert destination or written handoff note wanted for blocked rows.

Inputs:

- `order-emails.csv`: mock forwarded staffing order emails with extracted fields.
- `client-map.csv`: mock Monday client lookup table with account and billing state.
- `extraction-policy.csv`: required-field and confidence rules.

Outputs:

- `order-draft-ledger.csv`: draft-only order rows that are safe enough to inspect.
- `blocked-alert-queue.csv`: unknown clients, billing holds, missing fields, low-confidence extractions, and duplicate replays.
- `extraction-error-log.csv`: malformed forwarded emails or invalid extraction metadata.

Acceptance checks:

1. Clean known clients create draft-only order rows with Monday lookup evidence.
2. Unknown clients become blocked alerts instead of guessed client matches.
3. Billing holds are blocked before any order draft.
4. Missing required fields and low-confidence extraction are review-gated.
5. Duplicate forwarded order replays do not create duplicate drafts.
6. Empty or malformed forwarded bodies create hard error rows.
7. No live inbox, Make.com, Monday.com, customer, worker, or staffing-client data is used.

Paid implementation boundary:

- Start with redacted or synthetic forwarded order samples.
- Write the Monday client lookup key and required staffing fields before touching tools.
- Keep first output as a dry-run draft ledger plus blocked alert queue.
- Add live inbox, Make.com, Monday.com, or production writes only after separate written approval and scope.
