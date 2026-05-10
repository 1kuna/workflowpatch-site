# Client Insight Review Demo Runbook

## Purpose

Show how WorkflowPatch can turn approved, redacted agency report exports into an internal opportunity ledger, strategist review queue, exception queue, and draft-only client insight rows.

## Inputs

- `report-export.csv`: mock report rows from ad, analytics, CRM, SEO, email, and display exports.
- `insight-policy.csv`: review boundaries for source safety, evidence, duplicates, date ranges, stale campaigns, and draft-only output.

## Outputs

- `opportunity-ledger.csv`: accepted report rows with computed revenue delta, ROAS, evidence link, and review decision.
- `strategist-review-queue.csv`: opportunity candidates that need strategist judgment before any client-facing recommendation.
- `client-ready-draft-queue.csv`: internal draft rows only, never sent or published.
- `exception-queue.csv`: rows with date-range, stale-campaign, spend/revenue, or evidence problems.
- `blocked-insight-queue.csv`: live-client-data and duplicate rows blocked before review.
- `error-log.csv`: hard missing-field failures.

## Acceptance Checks

- Approved redacted exports are the only allowed source for a first proof.
- Every opportunity row has evidence before it can become a draft.
- Client-ready copy remains internal review only.
- Exceptions and hard errors stay visible instead of being buried in a narrative summary.
- Live ad, analytics, CRM, or client accounts are not connected.

## Out Of Scope

- No live client data.
- No live ad, analytics, CRM, CMS, or reporting credentials.
- No external client send, publish, or dashboard write.
- No marketing strategy ownership.
- No claim that an automated insight is correct without strategist review.
