# Public Source Monitor Runbook

This is a mock WorkflowPatch proof surface. It uses no client data, no credentials, no live source fetches, no PHI, no patient records, and no legal or regulatory judgment.

## First Slice

One public-source monitor proof:

1. Confirm the approved public source family.
2. Define the non-sensitive fields that may be captured.
3. Define the boundary tag shape, such as state, tenant, region, or account.
4. Route uncertain rows, schema changes, and source failures to review.
5. Log canary failures before any destination write.

## Guardrails

- No PHI or patient identifiers.
- No credentialing packets, payer records, or regulated case files.
- No legal, medical, or compliance advice.
- No production tenant architecture from the first proof.
- No silent writes when source schema, boundary tag, or canary state is unclear.

## Acceptance Checks

- Every source event maps to a monitor-ledger row.
- Every schema change or low-confidence row reaches the review queue.
- Every out-of-scope or boundaryless row reaches the error log.
- The canary log proves the alert path without touching a live system.
