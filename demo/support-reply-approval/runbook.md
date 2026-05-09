# Support Reply Approval Demo Runbook

This demo shows the delivery shape for a customer-support draft workflow.

## Scope

- Source: mock support email export, mock approved knowledge-base rows, and mock send history.
- Transformation: classify each email, match it to an approved answer, and decide whether a draft is safe enough to queue for human approval.
- Destination: draft reply queue, review queue, source ledger, and error log.

## Acceptance Checks

1. Routine support emails with approved knowledge-base sources create draft replies.
2. Customer-facing copy remains approval-gated.
3. Refund, dispute, missing-source, and duplicate-send cases land in the review queue.
4. Missing customer email and duplicate source email IDs land in the error log.
5. Every draft or hold preserves evidence about the matched topic and source.

## Production Notes

- Do not send customer replies directly from the first build.
- Start with buyer-approved knowledge-base snippets or product docs only.
- Keep a send-history check so repeated inbound emails do not create duplicate sends.
- Add a reviewer feedback field before trying to improve prompt behavior.
- Keep payment, legal, health, refund, and angry-customer cases behind human review unless the buyer explicitly approves a written policy.
