# WorkflowPatch Demo Runbook

Demo workflow:

`request export -> classification + draft next step -> review queue + error log`

## Inputs

- CSV export with request id, requester details, message, source, and priority hint.
- No real customer data.
- No secrets or connected accounts.

## Processing Rules

1. Reject rows missing `request_id`, `requester_email`, or `message`.
2. Reject duplicate `request_id` values instead of processing the same request twice.
3. Classify each valid row as sales, support, reporting, operations, or unclear.
4. Assign urgency from the message and priority hint.
5. Draft an internal next step for human review.
6. Mark all customer-facing copy as `approval_required=true`.
7. Write blocked rows to a visible error log.

## Acceptance Checks

- Valid rows appear in `review-queue.csv`.
- Invalid rows appear in `error-log.csv`.
- No external message is sent automatically.
- Duplicate request ids are blocked.
- A non-technical operator can inspect the output without opening code.

## Handoff

For a real sprint, this same pattern would be wired to one approved source and one approved destination, with credentials provided by the buyer and with a human approval step before any external output leaves the team.
