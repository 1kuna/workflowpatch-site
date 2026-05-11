# Licensing Ops State Runbook

1. Export or receive the redacted source events.
2. Confirm each event has a stable client id, email, action, and correlation id.
3. Run `python3 process_licensing_ops_demo.py`.
4. Review `licensing-state-ledger.csv` for status rows that are safe to prepare.
5. Review `approval-review-queue.csv` before any payout, payroll, or customer-message action.
6. Resolve `blocked-action-queue.csv` and `error-log.csv` before connecting live accounts.

Proof boundary: no live GHL, Whop, Gusto, Testimonial.io, Sheets, email, payroll, payout, or customer-facing action is performed by this demo.
