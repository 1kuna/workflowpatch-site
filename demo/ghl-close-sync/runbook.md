# GHL Close Sync Demo Runbook

This mock proof demonstrates a conflict-safe GHL and Close two-way sync without connecting to live CRM accounts.

## Inputs

- `contact-map.csv`: stable contact key, email, Close id, GHL id, owner, and source-of-truth rules.
- `field-policy.csv`: field-level direction, winning system, and review rule.
- `close-appointment-events.csv`: redacted Close appointment events.
- `ghl-contact-changes.csv`: redacted GHL contact changes.

## Outputs

- `sync-ledger.csv`: rows ready for reviewed GHL or Close updates.
- `conflict-review-queue.csv`: duplicate events, missing contact matches, and identity/source-of-truth conflicts.
- `error-log.csv`: impossible rows such as missing required appointment fields or unknown field policies.
- `handoff.md`: written summary of what synced, what blocked, and what must be decided before production.

## Guardrails

- No live GHL or Close writes.
- No SMS, email, or customer-facing messages.
- No historical backfill from the first proof.
- No silent overwrite when source-of-truth is unclear.
- Duplicate correlation ids are blocked before any destination write.

## Acceptance Checks

1. Close appointment events with a stable match enter the sync ledger.
2. GHL contact changes with an allowed field policy enter the sync ledger.
3. Missing contact matches enter the conflict review queue.
4. Identity-field changes enter the conflict review queue.
5. Duplicate correlation ids enter the conflict review queue.
6. Unknown or impossible field policy cases enter the error log.
