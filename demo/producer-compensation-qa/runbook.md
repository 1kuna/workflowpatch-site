# Producer Compensation QA Runbook

Purpose: prove a compensation-ops control layer with redacted or synthetic producer, policy, commission, hierarchy, chargeback, retry, and payout-state events before any live insurance carrier, producer, customer, finance, commission, policy, payout, payroll, tax, accounting, legal, compliance, or production data enters scope.

## Inputs

- `source-events.csv`: redacted or synthetic event rows.
- `producer-map.csv`: approved producer and hierarchy map.
- `compensation-policy.csv`: event-type policy and destination rules.

## Outputs

- `compensation-qa-ledger.csv`: rows safe to stage for owner review.
- `owner-review-queue.csv`: hierarchy, chargeback, duplicate, or review-required rows.
- `blocked-action-queue.csv`: payout, payment, customer-message, sensitive-data, or out-of-scope actions.
- `error-log.csv`: malformed or unmapped source rows.

## First-Sprint Boundary

- No live carrier, producer, customer, policy, commission, payout, payroll, tax, accounting, legal, compliance, HR, or production data.
- No payout release, payment initiation, bank change, statement send, carrier submission, customer message, or production write.
- No insurance, financial, accounting, tax, legal, compliance, HR, or compensation advice.
- Any implementation beyond the proof requires a separate written scope, approved access, and verified payment.

## Acceptance Checks

- Every accepted row has a known producer, approved hierarchy path, unique correlation id, supported event type, and owner-review output.
- Every hierarchy mismatch, chargeback, duplicate, and review-required policy lands in `owner-review-queue.csv`.
- Every payout release or sensitive-data row lands in `blocked-action-queue.csv`.
- Every unmapped producer or unsupported event type lands in `error-log.csv`.
