# POS Daily Reconciliation Runbook

This demo uses mock data only.

## Scope

First paid slice:

- one redacted Toast order/item export or API sample,
- one category map,
- one target daily summary shape,
- one Google Sheets destination shape,
- reconciliation and blocked-row evidence before any live write.

## Excluded Until Separately Approved

- live Toast credentials,
- live Google Sheets writes,
- payment, payroll, or customer data,
- customer-facing messages,
- full reporting rebuilds,
- broad restaurant analytics ownership.

## Review Checklist

1. Confirm business date and timezone rules.
2. Confirm revenue center names.
3. Confirm lunch/dinner or service-window logic.
4. Confirm category map by Toast GUID.
5. Check duplicate item ids from replay or partial runs.
6. Compare calculated summary rows to Toast Daily Sales Summary.
7. Send only approved rows to the destination.
