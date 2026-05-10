# Async Proof Slice Demo Runbook

This mock proof demonstrates one written, async test build shape without connecting to live CRMs, Sheets, Notion, inboxes, AI APIs, or production workflows.

## Inputs

- `workflow-briefs.csv`: the workflow brief, source, destination, success definition, blocked definition, and status-update channel.
- `sample-events.csv`: redacted event/export rows to test against the brief.
- `validation-rules.csv`: core checks for required fields, duplicate correlation ids, and review-worthy AI output.

## Outputs

- `status-ledger.csv`: rows that passed the proof-slice checks and are ready for reviewed delivery.
- `review-queue.csv`: rows blocked for missing destination data, duplicate side effects, or low-confidence output.
- `error-log.csv`: impossible rows such as unknown workflow briefs.
- `status-update.md`: a written status note showing what happened without a call.

## Guardrails

- The proof is one source, one transform, and one destination, not broad bench availability.
- Review rows are not hidden behind a happy-path demo.
- Duplicate side effects are blocked before any destination write.
- AI or judgment output stays reviewable; low-confidence rows do not silently write.
- No customer-facing message, SMS, payment, credentialed production write, or open-ended hourly commitment is included.

## Acceptance Checks

1. Valid rows produce status-ledger entries.
2. Duplicate correlation ids enter the review queue.
3. Missing owner or destination data enters the review queue.
4. Low-confidence AI-style output enters the review queue.
5. The written status update summarizes ready, review, and error rows.

## First Client Slice

For a live client, start with one workflow brief, one redacted sample payload/export/event, target destination fields, edge cases, and what should be blocked. The output should be a ledger, review queue, error log, status note, and handoff showing whether ongoing collaboration is worth continuing.
