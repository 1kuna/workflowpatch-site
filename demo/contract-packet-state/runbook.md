# Contract Packet State Demo Runbook

This mock proof shows how WorkflowPatch would handle contract packet chasing without drafting contracts, editing templates, sending candidate messages, or touching real employee records.

## Inputs

- `hire-events.csv`: redacted or synthetic approved-hire rows.
- `packet-policy.csv`: template families, required fields, reminder timing, escalation timing, and filing destinations.

## Outputs

- `state-ledger.csv`: every hire row mapped to the next operational state.
- `reminder-queue.csv`: reminder or escalation candidates, still approval-gated.
- `filing-manifest.csv`: signed packets ready for filing.
- `error-log.csv`: rows blocked before packet creation or candidate-facing action.

## Guardrails

- No legal advice or contract drafting.
- No live employee documents in the first proof.
- No candidate-facing sends before approval.
- No HRIS, e-sign, or file-system writes until a dry-run ledger is accepted.

## Acceptance Checks

- Missing required fields produce blocked rows.
- Pending internal review does not create candidate-send work.
- Candidate reminders stay in an approval-required queue.
- Signed packets produce a filing manifest row.
- Every output row is traceable to one input hire id.
