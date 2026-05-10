# Automation Builder Audit Demo Runbook

This mock proof demonstrates how WorkflowPatch evaluates a proposed automation slice without making personal hiring judgments or connecting to live systems.

## Inputs

- `workflow-slices.csv`: the workflow slice, source, destination, required input contract, dedupe key, and review boundary.
- `builder-submissions.csv`: mock builder artifacts or proposal notes for those slices.
- `audit-rules.csv`: the checks used to inspect the artifact quality.

## Outputs

- `audit-ledger.csv`: scored artifact rows and verdicts.
- `risk-review-queue.csv`: missing or unsafe evidence that should be clarified before production work.
- `reusable-test-matrix.csv`: repeatable tests a buyer can require from any builder.
- `error-log.csv`: impossible rows, such as an artifact for an unregistered workflow slice.
- `builder-quality-handoff.md`: the written summary a buyer can use without a call.

## Guardrails

- Evaluate workflow evidence, not personal traits.
- Do not rank candidates or make employment recommendations.
- Do not request live credentials, private customer data, resumes, or internal HR records.
- Keep the first paid proof to one CRM, routing, or light-agent flow.
- Require source evidence for any AI-generated summary or judgment.

## Acceptance Checks

1. A complete artifact reaches the audit ledger as ready for a paid proof.
2. Missing dedupe keys, unsafe retries, thin tests, or missing source links enter the risk review queue.
3. Unknown workflow slices enter the error log.
4. Every known submission gets a reusable test matrix covering happy path, duplicate replay, bad payload, and partial destination failure.
