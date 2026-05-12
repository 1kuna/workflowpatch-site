# Private Automation QA Proof Runbook

Purpose: show the first paid slice for a narrow automation QA or partner-overflow workflow without taking over strategy, client ownership, support-bench coverage, live writes, or customer-facing work.

Inputs:

- One redacted client export, inbox sample, webhook sample, lead form, order event, or CRM sample.
- One target destination, owner-review output, or handoff note.
- The owner's approval boundary for anything client-visible or production-facing.
- Fields that must be blocked, redacted, or left untouched.
- `overflow-slice-map.csv`: how the same guardrail maps to CRM lead routing, attribution webhook QA, and agency handoff QA.

Process:

1. Load the request rows.
2. Apply scope and safety rules before producing any output.
3. Put internal low-sensitivity rows into the QA ledger.
4. Put client-visible, sensitive, or live-write rows into the review queue.
5. Put broad retainer, support-bench, credential, or production-connector requests into blocked scope.
6. Log malformed rows instead of silently dropping them.

Acceptance checks:

- Internal low-risk rows produce QA artifacts.
- Client-visible rows are held for owner approval.
- CRM, lead-routing, attribution, API, and webhook slices stay scoped to one source, one decision rule, and one reviewable destination.
- Broad retainer, support-bench, or delivery-ownership requests are blocked.
- Secrets or credentials are excluded.
- No live CRM, client, vendor, inbox, or production write occurs from the first proof.
