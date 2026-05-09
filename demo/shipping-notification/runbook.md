# Shipping Notification Demo Runbook

This demo shows the delivery shape for a fulfillment or customer-update workflow.

## Scope

- Source: mock order export plus mock carrier-status export.
- Transformation: decide whether each order can safely receive a shipping-update draft.
- Destination: notification queue, operations alert queue, and error log.

## Acceptance Checks

1. Ready orders with live tracking and ETA create customer-update drafts.
2. Customer-facing copy remains approval-gated.
3. Tracking that is not live creates an internal operations alert instead of a customer email.
4. Orders not marked ready are blocked from customer notification.
5. Missing required fields and duplicate order IDs land in the error log.

## Production Notes

- Do not send customer emails directly from the first build.
- Use buyer-approved carrier APIs or exports only.
- Keep a replayable order ID and tracking evidence line for every draft.
- Add a cutoff rule for repeated carrier-check failures before any customer-facing send step exists.
