# WorkflowPatch Member Intake QA Runbook

This proof uses synthetic member-intake events only. It does not use live member data, dating profiles, customer messages, CRM records, call recordings, payment data, or production accounts.

## Inputs

- `member-events.csv` - synthetic consultation, profile-update, matchmaker-note, referral, no-show, and date-feedback rows.
- `member-policy.csv` - review and output policy for each event family.

## Outputs

- `member-intake-qa-ledger.csv` - rows safe enough to stage for owner review.
- `owner-review-queue.csv` - duplicate, reengagement, handoff, or feedback rows needing owner review.
- `blocked-action-queue.csv` - live-channel, sensitive-detail, SMS, member-message, or date-action rows stopped before execution.
- `error-log.csv` - malformed or incomplete rows.

## Production Boundary

No live member, prospect, matchmaker, dating-profile, CRM, payment, call, SMS, WhatsApp, email, calendar, or production data. No matching advice, relationship advice, legal advice, privacy advice, HR advice, SMS send, member message, date scheduling, CRM write, profile update, or production action.

## Acceptance Check

Run:

```bash
python3 process_member_intake_demo.py
```

Expected counts:

- `source_rows=8`
- `ledger_rows=2`
- `review_rows=2`
- `blocked_rows=3`
- `error_rows=1`
