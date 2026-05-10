# Airtable Performance Triage Runbook

This mock runbook shows the first slice WorkflowPatch would use before recommending Enterprise, HyperDB, a SQL migration, or external workers.

## Inputs

- Redacted base map or screenshots.
- One slow automation or script path.
- Rough record counts and linked-table shape.
- Peak-time queue delay, timeout, or UI lag examples.
- What must not be touched in a first proof.

## First-Pass Checks

1. Map trigger, records touched, linked fields, script reads and writes, downstream automations, and owner.
2. Separate plan or seat limits from architecture issues.
3. Flag nested loops, full-base scans, premature triggers, write fanout, linked-record bloat, and conflicting automations.
4. Pick one keep, split, or offload recommendation for the worst path.
5. Keep all output in a reviewable ledger before any live base edit.

## Exclusions

- No live base access from first touch.
- No Enterprise or HyperDB outcome promise.
- No full SQL migration recommendation without evidence.
- No production script edits without a written input/output contract.
