# Shipping Notification Gate Proof Runbook

This demo shows the delivery shape for a fulfillment or customer-update workflow.

## First Buyer Slice

- Source: one redacted Google Sheet ready row plus carrier/status source rules.
- Transformation: validate ready state, tracking status, ETA evidence, duplicate risk, and notify/no-notify rule.
- Destination: customer email draft queue, operations alert queue, error log, and written handoff.

Useful sample: one ready order, one delayed or missing tracking case, required customer/order fields, duplicate-order rule, delayed-tracking alert rule, and destination email draft shape.

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
- Do not make weather or ETA promises without buyer-approved carrier evidence.
- Use buyer-approved carrier APIs or exports only.
- Keep a replayable order ID and tracking evidence line for every draft.
- Add a cutoff rule for repeated carrier-check failures before any customer-facing send step exists.
