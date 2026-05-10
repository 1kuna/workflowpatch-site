# WorkflowPatch Event Production Project Bible Demo Runbook

This demo is a mock first-proof slice for event-production Project Bible work.

It does not connect to Airtable, Slack, Google Drive, DocuSign, Make, Zapier, payroll, HR, vendor systems, client portals, or live project data.

## Inputs

- `project-records.csv`: redacted project rows with budget, milestone, vendor, rigging, visibility, owner, sensitivity, and phase fields.
- `role-policy.csv`: role-specific visibility rules for producer, client, production manager, and finance review.
- `readiness-policy.csv`: policy hints for budget, milestone, vendor, rigging, and client-summary readiness.

## Outputs

- `review-ledger.csv`: project rows ready for a role-based review ledger.
- `role-visibility-map.csv`: draft view map by project and role.
- `exception-queue.csv`: rows blocked for budget, milestone, vendor, rigging, client-summary, duplicate, completed, or sensitive-scope review.
- `error-log.csv`: malformed rows that need correction before any build plan.

## Acceptance Checks

- Sensitive client rows are blocked before visibility automation.
- Duplicate or completed project rows stay in review instead of flowing into active controls.
- Budget, milestone, vendor, rigging, and client-summary risk appears as explicit owner action.
- The first proof remains a written, dry-run diagnostic before full Project Bible architecture.
