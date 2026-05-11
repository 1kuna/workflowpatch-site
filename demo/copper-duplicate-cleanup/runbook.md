# Copper Duplicate Cleanup Demo Runbook

This is a mock WorkflowPatch demo for a Zapier-to-Make Copper CRM migration slice. It uses no client data, no credentials, and no connected Copper account.

## Inputs

- `existing-copper-records.csv`: mock current Copper opportunities and people.
- `copper-trigger-events.csv`: mock trigger payloads from five migration workflows.
- `match-policy.csv`: the matching order, do-not-overwrite fields, and review conditions.

## Command

```bash
python3 demo/copper-duplicate-cleanup/process_copper_duplicate_demo.py
```

## Outputs

- `upsert-ledger.csv`: dry-run create/update candidates that are safe for human review.
- `conflict-queue.csv`: duplicate, ambiguous, or sensitive records that need a human decision before any Copper write.
- `error-log.csv`: payloads that are blocked because the input is not approved or not usable.

## Acceptance Checks

- An event with a known external key updates the existing Copper record instead of creating a duplicate.
- A new approved event becomes a dry-run create candidate.
- Multiple natural-key matches are held in the conflict queue.
- Missing match keys are held before any create.
- Duplicate event ids are held as replay/duplicate-run evidence.
- Unapproved live payloads are blocked in the error log.
- Owner fields are never overwritten by the dry-run output.

## Non-Goals

- No live Copper write is executed.
- No all-five-workflow rebuild is implied.
- No contact, opportunity, owner, or lifecycle field is changed without written approval.
- No guarantee is made about Copper, Zapier, Make, or any third-party API availability.
