# Document/email review demo runbook

This proof shows the first safe slice for a document, email, or CRM-export workflow:

1. Start with approved redacted source rows only.
2. Extract or classify into a reviewable structured row.
3. Block sensitive data, unapproved sources, duplicates, malformed input, and live-write requests.
4. Route low-confidence or incomplete rows to human review.
5. Produce a destination-ready artifact only after the row is safe for review.

## Inputs

- `source-items.csv`: synthetic email, document, and CRM-export rows.
- `extraction-policy.csv`: first-proof routing rules.

## Outputs

- `extraction-ledger.csv`: one decision row per usable input.
- `destination-ready.csv`: accepted rows that can be inspected by a human.
- `human-review-queue.csv`: uncertain rows that need review before destination action.
- `blocked-item-queue.csv`: rows excluded from first proof.
- `error-log.csv`: malformed input rows.

## Exclusions

- No client data.
- No credentials or browser accounts.
- No live CRM or ERP write.
- No external email, Slack, SMS, or customer send.
- No unpaid technical mini-task or employment-screening commitment.
