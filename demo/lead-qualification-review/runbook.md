# Lead Routing Review Proof Runbook

This proof surface uses redacted or synthetic `.example` leads only.

## Purpose

Show the first safe slice for a sales, marketing, RevOps, or HubSpot routing request:

1. Normalize source rows.
2. Score only the evidence that is present.
3. Block duplicate, unpermitted, or malformed rows.
4. Put review-ready rows in an owner approval queue before any CRM write, report update, or outreach.

## Inputs

- `lead-sources.csv`
- `existing-crm.csv`
- `qualification-rules.csv`

## Outputs

- `lead-review-ledger.csv`
- `approval-queue.csv`
- `blocked-leads.csv`
- `error-log.csv`

## Acceptance Checks

- No live outreach is sent.
- No CRM write happens automatically.
- Rows missing company, email, or source land in `error-log.csv`.
- Existing CRM contacts land in `blocked-leads.csv`.
- Rows without clear permission or buyer-created context are blocked before outreach.
- Review-ready rows include the evidence and owner needed for a human decision.
- Routing and reporting outputs stay dry-run or approval-gated until separately scoped.

## Regenerate

```bash
python3 process_lead_review_demo.py
```
