# WorkflowPatch Lead Review Ledger Demo Runbook

This is a synthetic dry-run proof for lead-form, CRM, WhatsApp, and Google Reviews automation. It turns sample lead rows into a CRM lead ledger, internal review queue, blocked action queue, and hard errors.

It does not send WhatsApp messages, request Google Reviews, write to a CRM/database, use live customer data, use credentials, or touch a production account.

## Regenerate

```bash
python3 demo/lead-review-ledger/process_lead_review_demo.py
```

Expected output:

- `crm-lead-ledger.csv`
- `internal-review-queue.csv`
- `blocked-action-queue.csv`
- `error-log.csv`

## QA Checks

- Every accepted row must come from `synthetic_or_redacted`.
- Duplicate `duplicate_key` rows must land in `blocked-action-queue.csv`.
- WhatsApp rows without consent must be blocked before a draft action.
- CRM-unmatched rows must route to internal review.
- Review-request rows must stay `internal_review_only`.
- Missing required fields must land in `error-log.csv`.

## First Client Boundary

Use this for a first paid dry-run proof only. Live WhatsApp sends, Google Reviews requests, CRM/database writes, customer messages, credentials, and broad operator coverage stay out of scope until separately approved and documented.
