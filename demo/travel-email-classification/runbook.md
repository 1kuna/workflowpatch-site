# Travel Email Classification Proof Runbook

This redacted or synthetic proof shows the first safe branch for a B2B travel agency email automation system.

## Inputs

- `gmail-sample-emails.csv`: redacted Gmail-style messages across hotel updates, urgent booking changes, invoices, ambiguous messages, auto-replies, and missing account keys.
- `classification-rules.csv`: label rules, minimum confidence, target Sheets stage, and Slack escalation flags.
- `status-stage-map.csv`: the approved request status stages.

## Outputs

- `classification-ledger.csv`: accepted classifications with confidence and evidence.
- `sheets-status-queue.csv`: Google Sheets-ready status rows.
- `slack-escalation-drafts.csv`: review-first Slack alert drafts for urgent or booking-change rows.
- `review-queue.csv`: ambiguous or loop-protected messages that need a human decision.
- `error-log.csv`: hard failures such as missing client account keys.

## Guardrails

- No client Gmail, Sheets, Slack, booking engine, or LLM account is connected.
- No customer email is sent.
- Slack alerts are drafts, not live posts.
- Auto-reply loop protection blocks out-of-office style rows.
- Ambiguous category matches are reviewed before any Sheets or Slack action.
- Booking-engine writes are out of scope for the first proof.

## Acceptance Checks

1. Urgent booking-change emails create a Sheets row and Slack draft.
2. Hotel updates and invoices create Sheets rows without Slack escalation.
3. Ambiguous messages land in review.
4. Auto-replies are protected from loops.
5. Missing account keys create hard errors.
6. Every accepted row has a reference id and evidence.

## Rebuild

```bash
python3 process_travel_email_demo.py
```
