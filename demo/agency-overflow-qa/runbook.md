# Agency Overflow QA Demo Runbook

Purpose: show how WorkflowPatch handles a narrow agency or partner overflow slice without taking over strategy, client ownership, broad bench availability, live writes, or customer-facing work.

Inputs:

- One redacted source export, inbox sample, webhook sample, or CRM sample.
- One target destination or review output.
- The partner's approval boundary for anything client-visible.
- Fields that must be blocked, redacted, or left untouched.

Process:

1. Load the request rows.
2. Apply scope and safety rules before producing any output.
3. Put internal low-sensitivity rows into the QA ledger.
4. Put client-visible or live-write rows into the review queue.
5. Put broad retainer, bench, credential, or production-connector requests into blocked scope.
6. Log malformed rows instead of silently dropping them.

Acceptance checks:

- Internal low-risk rows produce QA artifacts.
- Client-visible rows are held for partner approval.
- Broad retainer or bench requests are blocked.
- Secrets or credentials are excluded.
- No live CRM, client, vendor, inbox, or production write occurs from the first proof.
