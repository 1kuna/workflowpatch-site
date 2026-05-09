# Webhook Idempotency Demo Runbook

This demo shows the delivery shape for a webhook or event-ingestion workflow where duplicate side effects and tenant bleed are the main risk.

## Scope

- Source: mock inbound webhook events plus a mock tenant registry.
- Transformation: verify event safety, claim the idempotency key, validate tenant boundaries, and normalize accepted handler input.
- Destination: accepted event ledger, blocked event queue, and error log.

## Acceptance Checks

1. New signed events for active tenants create accepted handler rows.
2. Duplicate event IDs are blocked before any downstream write.
3. Invalid signatures are blocked.
4. Unsupported event types are blocked unless explicitly allowed for the tenant.
5. Payload tenant mismatches are blocked.
6. Unknown or inactive tenants are blocked.
7. Missing core fields land in the error log.

## Production Notes

- Do not call downstream systems until idempotency and tenant checks pass.
- Keep replay evidence for every accepted or blocked event.
- Store only the minimum payload needed for audit and replay.
- Add buyer-approved handler logic after this guardrail works on sample events.
