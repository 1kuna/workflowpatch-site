# Access State Proof Runbook

This proof demonstrates one Phase 1 onboarding/access workflow with redacted or synthetic inputs and without connecting to real landing pages, auth providers, payment processors, or email tools.

## First Buyer Slice

- Source: redacted signup, purchase/refund, or company/user access events plus payment, attribution, role, or company-scope rules.
- Transformation: match the relevant access evidence, decide access state, block ambiguous/refunded/missing-attribution/company-scope cases, and log errors.
- Destination: Airtable-style access ledger, platform access action queue, review queue, and written handoff.

Useful sample: one allowed user or purchase, one blocked or failed case, one ambiguous role/company/attribution case, destination fields, expected access states, and the manual-review rule.

## Inputs

- `signup-events.csv`: redacted or synthetic signup events from landing pages.
- `content-access-catalog.csv`: requested tier rules and content groups.

## Outputs

- `onboarding-ledger.csv`: accepted or pending onboarding states.
- `access-review-queue.csv`: rows requiring a human decision before access is granted.
- `email-draft-queue.csv`: approval-required onboarding or payment follow-up drafts.
- `error-log.csv`: malformed rows that should not disappear silently.

## Guardrails

- Airtable is treated as the operational ledger, not as a substitute for real authentication.
- Payment-required tiers do not receive access without a paid event.
- Unverified emails do not receive access even if payment is present.
- Restricted partner access is held for manual approval.
- No outbound email is sent by the demo; draft rows stay approval-required.
- Duplicate or existing-user signals are held for review instead of creating another account.
- No live refund, permission edit, access, or customer-message action is part of the first proof.

## Acceptance Checks

1. A paid, verified founding signup is granted access to the Founder Circle.
2. An unpaid course signup is held as `pending_payment` and receives an approval-required draft.
3. A paid but unverified signup is held as `pending_email_verification`.
4. A partner-tier signup is held in `access-review-queue.csv`.
5. A missing email creates an `error-log.csv` row.

## First Client Slice

For a live client, start with one signup or access source, one access decision, and one destination ledger. The first proof should use redacted or synthetic sample events and should define whether identity and content access are handled by a real auth/front-end system, with Airtable used for onboarding operations and review state.
