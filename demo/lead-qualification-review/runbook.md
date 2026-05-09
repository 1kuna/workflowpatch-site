# Lead Qualification Review Runbook

This is a mock WorkflowPatch proof surface. It uses sample `.example` leads only.

## Purpose

Show the first safe slice for a sales or marketing automation request:

1. Normalize source rows.
2. Score only the evidence that is present.
3. Block duplicate, unpermitted, or malformed rows.
4. Put review-ready rows in an approval queue before any CRM write or outreach.

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

## Regenerate

```bash
python3 process_lead_review_demo.py
```
