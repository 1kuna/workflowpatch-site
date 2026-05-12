# Workflow Reliability Ledger Runbook

This proof shows the first safe production-readiness shape for production-minded n8n or workflow-automation partners.

## Inputs

- `workflow-events.csv`: synthetic workflow events and failure cases.
- `reliability-policy.csv`: the reliability checks that decide whether a row is accepted, reviewed, blocked, or errored.

## Outputs

- `reliability-ledger.csv`: every non-hard-error row with its decision and reason.
- `monitoring-ledger.csv`: rows ready for dry-run monitoring and handoff.
- `fallback-review-queue.csv`: rows missing reliability details that must be fixed before live use.
- `blocked-action-queue.csv`: rows that request live actions, expose sensitive data, duplicate an event, or use an unapproved source.
- `error-log.csv`: rows malformed enough that the process should fail visibly.

## First-Proof Boundary

The first paid proof should stay redacted, written, and review-first. It should not use live client credentials, customer messaging, phone/voice actions, SMS sends, production writes, or broad agency partner terms until a separate written scope is accepted.

## Acceptance Check

Run:

```bash
python3 process_workflow_reliability_demo.py
```

Expected shape:

- at least one accepted monitoring row,
- at least one reliability-review row,
- at least one blocked live-action/sensitive/duplicate/source row,
- at least one hard error row,
- no silent promotion of live customer actions.
