# Postgres Statement Email Runbook

This mock demo shows the smallest safe slice of a weekly statement workflow from database rows to email drafts.

## Inputs

- `session-records.csv`: mock database export representing rows that would come from PostgreSQL.
- `send-history.csv`: statement keys already sent, used to prevent duplicate weekly emails.

## Outputs

- `statement-ledger.csv`: grouped statement rows with totals, source records, and statement keys.
- `email-draft-queue.csv`: email drafts that still require human approval before sending.
- `blocked-statements.csv`: rows blocked for missing recipients, unapproved source state, or already-sent statements.
- `error-log.csv`: malformed source rows, including duplicate record ids.

## Operating Boundary

The first paid patch should not start with live sends. Start by running the query against a redacted or test week, generating the statement ledger and email draft queue, and proving duplicate suppression. Azure Communication Services or another mail provider should be enabled only after the client approves the statement key, recipient mapping, CC rules, retry policy, and approval step.

## Acceptance Checks

1. Approved rows group into the correct weekly statement.
2. Duplicate source record ids are logged as errors.
3. Missing pair or external recipients are blocked before drafting.
4. Already-sent statement keys are not drafted again.
5. Every email draft preserves source record evidence and remains approval-gated.
