# SMS Approval State Demo Runbook

This mock proof pack shows the first safe slice for a stateful SMS workflow:

1. Read inbound SMS rows from `inbound-messages.csv`.
2. Match each phone token to `users.csv`.
3. Block unknown, opted-out, paused, or already-pending conversations.
4. Draft an activity message from `activity-catalog.csv`.
5. Put the draft in `slack-approval-queue.csv`.
6. Apply reviewer decisions from `slack-decisions.csv`.
7. Queue only approved messages in `outbound-queue.csv`.
8. Record state changes, analytics events, and hard failures.

Acceptance checks:

- No outbound row is created without an approval decision.
- Opted-out, paused, unknown, and already-pending rows are blocked visibly.
- Every drafted row has a conversation-state record.
- Every accepted or blocked path leaves evidence for review.

This demo uses mock rows only. It does not send SMS, call Twilio, call Claude, post to Slack, or store personal health data.
