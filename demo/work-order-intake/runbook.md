# Work Order Intake Demo Runbook

Purpose: prove a shared-Gmail work-order intake path before touching live Gmail, FACIL-IT, Google Workspace, Google Chat, production work orders, customer data, vendor data, or any live write path.

Inputs:

- `source-emails.csv`: mock shared-Gmail work-order emails with extracted fields.
- `location-map.csv`: mock buyer-approved store and FACIL-IT site map.
- `facil-it-field-map.csv`: required field map for a work-order create or update plan.
- `intake-policy.csv`: confidence, duplicate, attachment, location, write, and Chat rules.

Outputs:

- `work-order-ledger.csv`: parsed work orders that are safe enough for review.
- `facil-it-write-plan.csv`: dry-run create or update candidates with idempotency keys.
- `google-chat-summary-queue.csv`: Chat-ready summary rows that are not sent.
- `blocked-review-queue.csv`: missing WO numbers, ambiguous locations, attachment failures, duplicates, and low-confidence parses.
- `error-log.csv`: malformed or empty forwarded emails.

Acceptance checks:

1. Clean work-order emails produce reviewable ledger rows and dry-run FACIL-IT write-plan rows.
2. Every write-plan row has a stable idempotency key using work-order number and FACIL-IT site id.
3. Duplicate forwarded emails become blocked rows instead of second write candidates.
4. Missing work-order numbers and ambiguous store matches are blocked.
5. Attachment fetch failures are blocked before any FACIL-IT write plan.
6. Low-confidence parses and empty forwarded bodies are visible in review or error outputs.
7. Google Chat summaries are queued as text only and are never sent by this proof.
8. No live Gmail, FACIL-IT, Google Workspace, Google Chat, customer data, vendor data, or production work orders are used.

Paid implementation boundary:

- Start with two redacted or synthetic work-order emails and a buyer-approved FACIL-IT field map.
- Confirm work-order number, store id, location, attachment, duplicate, and Chat routing rules before touching tools.
- Keep the first output as a dry-run ledger, write-plan file, Chat summary queue, blocked review queue, and error log.
- Add live Gmail, FACIL-IT, Make, Google Workspace, Google Chat, or production work-order writes only after separate written approval and scope.
