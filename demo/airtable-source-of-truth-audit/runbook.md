# Airtable Source Of Truth Audit Demo Runbook

This mock proof shows the first WorkflowPatch slice for a high-volume Airtable internal-tools architecture question.

## Inputs

- `object-inventory.csv`: sanitized objects, record counts, current systems, owners, and source-of-truth candidates.
- `writer-map.csv`: systems allowed to read or write each object.
- `audit-policy.csv`: review copy for source-of-truth, archive, writer, and blocked decisions.

## Outputs

- `decision-pack.csv`: source-of-truth decisions ready for architecture review.
- `write-policy-map.csv`: draft write policies for Airtable, Stacker, Make, n8n, Supabase, Polytomic, and adjacent systems.
- `archive-review-queue.csv`: archive or mirror candidates that need owner approval.
- `blocked-decision-queue.csv`: duplicate, sensitive, missing-source, or unmapped rows.
- `error-log.csv`: malformed rows that cannot be evaluated.

## Guardrails

- No live Airtable writes.
- No production Stacker, Make, n8n, Supabase, or Polytomic changes.
- No source-of-truth authority claimed by WorkflowPatch.
- Sensitive objects and policy-affecting decisions remain blocked until owner-approved.
- This is an architecture diagnostic, not a full internal-tools rebuild.

## Acceptance Check

Run:

```bash
python3 process_airtable_source_of_truth_demo.py
```

Expected result:

- High-volume objects become decision-pack rows with explicit source-of-truth owners.
- Allowed writers become approval-required policy rows.
- Archive candidates become owner-review rows.
- Sensitive, duplicate, missing-source, or unmapped objects block visibly.
- Malformed rows go to `error-log.csv`.
