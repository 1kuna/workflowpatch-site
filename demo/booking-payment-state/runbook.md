# Booking Payment State Proof Runbook

Purpose: prove a scheduling/payment workflow can separate confirmed bookings, unpaid tentative holds, unavailable preferences, and malformed submissions before any live customer messages are sent.

First buyer slice:

- Source: one redacted Wix form row, Airtable class/booking/payment table shape, and trusted Stripe or Gmail payment notification sample.
- Transformation: validate payment state, class capacity, ridercoach availability, duplicate booking risk, and contact fields.
- Destination: booking ledger, unpaid hold queue, alternate-date/conflict queue, approval-required follow-up drafts, error log, and written handoff.

Useful sample: one paid form row, one unpaid row, one capacity or coach conflict, trusted payment notification shape, table fields, duplicate-booking rule, and customer-message approval rule.

Inputs:

- `form-submissions.csv`: redacted or synthetic Wix-style form rows with two preferred class times.
- `class-inventory.csv`: redacted or synthetic class capacity, confirmed count, coach availability, and enrollment link.
- `payment-notifications.csv`: redacted or synthetic Stripe/Gmail payment notifications.

Outputs:

- `booking-ledger.csv`: paid confirmations and unpaid tentative holds.
- `followup-queue.csv`: approval-required payment reminder drafts.
- `conflict-queue.csv`: unavailable preferences needing alternate-date handling.
- `error-log.csv`: malformed submissions blocked before messaging.

Acceptance checks:

1. Paid submissions become confirmed booking rows only when capacity and coach availability pass.
2. Unpaid submissions become tentative holds and payment-reminder drafts, not confirmed bookings.
3. Full classes and unavailable coaches route to conflict review.
4. Missing contact data becomes a hard error.
5. No live Stripe, Wix, Airtable, Gmail, SMS, phone, or enrollment-system action is used.

Paid implementation boundary:

- Start with one class family, one form source, one payment notification source, and one Airtable booking table.
- Keep all outbound messages approval-required until the state rules are accepted.
- Do not automate login-only external systems in the first proof unless an official API or approved manual handoff exists.
- Do not include phone AI, SMS, MSF RES browser actions, live payment actions, or customer-facing sends in the first proof.
