# Scenario Modularization Demo Runbook

This is a mock WorkflowPatch proof pack for a Make/n8n account that has grown into large scenarios with repeated parsing, mixed side effects, and unclear retry behavior.

## Scope

- Source: `scenario-inventory.csv`, `module-boundaries.csv`, `idempotency-plan.csv`, and `naming-runbook.csv`
- Transform: decide which module boundaries should be extracted first, which need review gates, and which should stay inline
- Destination: `refactor-ledger.csv` and `error-paths.csv`

## Guardrails

- No live Make, n8n, CRM, vendor, or email account is connected.
- No buyer blueprints, credentials, webhook secrets, or production records are included.
- This proof does not promise a whole-account refactor.
- The first paid sprint would prove one scenario family and one reusable boundary before touching broad production logic.

## Acceptance Checks

- Every extracted boundary has an idempotency key.
- Side-effecting modules require dry-run, approval, or ledger behavior before live writes.
- Boundaries with no reuse pressure stay inline instead of being extracted for neatness.
- Every expected failure class has a queue, ledger, or reviewer action.
- The naming runbook makes the handoff inspectable without opening the automation builder.

## Buyer Data Needed For A Paid Sprint

- One redacted scenario map or screenshots for the target family.
- One typical payload and one failing payload.
- Current module count, operation count, and the highest-cost modules.
- The desired replay behavior for duplicates, vendor limits, and missing mappings.
- Which writes must start in dry-run or approval mode.
