# HubSpot ClickUp Handoff Proof Runbook

This redacted or synthetic proof shows the first WorkflowPatch slice for a HubSpot to ClickUp handoff request where sales-stage changes need to become production or project handoff work without duplicate tasks, silent write-back drift, or unmanaged live writes.

## Inputs

- `hubspot-events.csv`: sanitized HubSpot deal-stage events and proposed write-back fields.
- `clickup-map.csv`: approved company, pipeline, ClickUp list, and write-back boundaries.
- `sync-policy.csv`: owner-review copy for create/update handoff candidates.

Useful first buyer sample:

- one redacted HubSpot deal that should create or update a ClickUp task,
- the ClickUp list, status, and required task fields,
- the HubSpot field that should store the ClickUp task ID or status,
- one duplicate or ambiguous example that should be held for review.

## Outputs

- `task-ledger.csv`: task create/update candidates that passed deterministic checks.
- `writeback-preview.csv`: HubSpot write-back drafts that still require owner approval.
- `conflict-queue.csv`: unknown, low-confidence, sensitive, destructive, duplicate, or unapproved-boundary rows.
- `error-log.csv`: malformed rows that cannot be evaluated.

## Guardrails

- No live HubSpot writes.
- No live ClickUp task creation.
- No unmanaged duplicate cleanup.
- No sensitive site-access details in task drafts.
- No source-of-truth or destructive field updates without explicit owner approval.

## Acceptance Check

Run:

```bash
python3 process_hubspot_clickup_demo.py
```

Expected result:

- Clean HubSpot events create task-ledger and write-back-preview rows.
- Duplicate deal-stage events go to `conflict-queue.csv`.
- Unknown companies, sensitive details, destructive changes, and low-confidence mappings are blocked visibly.
- Malformed events go to `error-log.csv`.
