# Scenario Ops Reduction Demo Runbook

This is a mock WorkflowPatch proof pack for an existing Make/n8n scenario set that burns too many operations and still fails in production.

## Scope

- Source: exported scenario run rows in `scenario-runs.csv`
- Transform: identify duplicate runs, repeated immediate retries, missing gating fields, and missing maps before expensive modules run
- Destination: `ops-reduction-ledger.csv`, `patch-plan.csv`, and `error-log.csv`

## Guardrails

- No live Make/n8n account is connected.
- No buyer scenario blueprints, secrets, or production records are included.
- This proof does not promise exact savings without a real operations export.
- The first paid sprint would patch one scenario family, not every scenario in the account.

## Acceptance Checks

- Duplicate successful runs are marked `skip_duplicate`.
- Repeated rate-limit runs are moved to `retry_after_queue`.
- Missing fields and mapping gaps block before expensive modules.
- Every suggested patch has reviewer action text.
- Unmapped errors must appear in `error-log.csv`.

## Buyer Data Needed For A Paid Sprint

- One exported scenario family or run-history sample.
- Current monthly operation count and target reduction range.
- Example failed executions or screenshots.
- Which modules are expensive, quota-limited, or customer-impacting.
- Whether live writes need dry-run or approval mode first.
