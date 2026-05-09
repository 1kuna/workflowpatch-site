# Reverse Logistics Routing Demo Runbook

This demo is a mock WorkflowPatch proof for ecommerce, returns, overstock, and reverse-logistics teams.

## Scope

- Source: one return or overstock event export plus one brand-guardrail table.
- Transformation: validate event identity, brand route policy, channel restrictions, condition, and value threshold.
- Destination: route review queue, routing ledger, exception log, and KPI summary.

## Guardrails

- No live warehouse, marketplace, pricing, or brand-partner writes.
- No customer, warehouse, SKU, pricing, or brand-partner data is used.
- Every routed item still requires human approval before action.
- Duplicate event ids, missing brand policies, missing inventory status, and blocked channels stay out of the route ledger.

## Acceptance Checks

1. Valid, policy-backed events create route review rows.
2. Damaged items only route to repair review when the brand allows repair.
3. Duplicate event ids are blocked.
4. Missing brand guardrails are blocked.
5. KPI totals only include rows that are ready for review.

## Files

- `recovery-events.csv`: mock return and overstock source events.
- `brand-guardrails.csv`: mock route policy by brand.
- `routing-ledger.csv`: accepted route decisions pending approval.
- `route-review-queue.csv`: human review queue for route recommendations.
- `exception-log.csv`: blocked rows with next steps.
- `kpi-summary.csv`: review-ready counts and estimated value by route.
- `process_reverse_logistics_demo.py`: deterministic demo generator.
