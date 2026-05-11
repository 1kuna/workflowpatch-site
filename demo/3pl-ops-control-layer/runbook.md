# 3PL Ops Control Layer Runbook

1. Export a redacted or synthetic event slice from the relevant WMS, ERP, MES, scanner, or operator source.
2. Confirm every event has a work_order_id, action, current state, target state, and correlation id.
3. Run `python3 process_3pl_ops_demo.py`.
4. Review `action-ledger.csv` for dry-run proposed actions.
5. Review `standards-review-ledger.csv` and `approval-queue.csv` before any physical or production-system action.
6. Resolve `blocked-action-queue.csv` and `error-log.csv` before considering live integration.

Proof boundary: no live WMS, ERP, MES, scanner, inventory, fulfillment, line-side, safety, or floor-control write is performed by this demo.
