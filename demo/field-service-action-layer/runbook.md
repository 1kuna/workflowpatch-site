# Field-Service Action Layer Runbook

This mock demo shows the smallest safe slice of a Voiceflow or chat action layer for a field-service company.

## Inputs

- `customers.csv`: known customer identity and account state.
- `work-orders.csv`: current work order, JobTread job id, status, window, technician, and account balance signal.
- `voiceflow-requests.csv`: incoming customer requests from a voice/chat layer.
- `action-policy.csv`: which actions may be considered for automation.

## Outputs

- `action-ledger.csv`: dry-run actions that passed identity, policy, account, and work-order checks.
- `approval-queue.csv`: reviewer prompts for the human approval step before any external write.
- `blocked-actions.csv`: requests blocked for duplicates, unknown customers, account holds, or disallowed action types.
- `error-log.csv`: malformed rows that need source cleanup.

## Operating Boundary

The first paid patch should not write directly to JobTread, a calendar, SMS, or a customer account. Start with a dry-run ledger and approval queue. Turn on writes only after the client approves the action policy, duplicate key, customer matching rule, and reviewer path.

## Acceptance Checks

1. Duplicate requests do not create duplicate downstream actions.
2. Unknown callers are blocked before scheduling.
3. Account holds are blocked before scheduling or rescheduling.
4. Pricing, refunds, and contract-term actions are never automated.
5. Every write candidate has evidence and a human approval prompt.
