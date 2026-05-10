# Program Ops KPI Demo Runbook

Purpose: prove one education program-ops path before any live Airtable, Zapier, child/family, staff-facing, or parent-facing system is touched.

## Source

- Use one redacted or synthetic attendance export, staffing chart, or KPI source.
- Required fields: event id, event type, site key, program week, row owner, match state, sensitivity, and replay key.
- Do not include child names, family contact details, medical notes, payment details, or private enrollment records.

## Transform

- Validate required fields.
- Block duplicate replay keys.
- Block child/family-sensitive scope.
- Block unmapped site/week rows.
- Route missing attendance and staffing coverage gaps to an exception queue.
- Produce dry-run KPI rows only for accepted site-week records.

## Destination

- `program-ledger.csv`: accepted source rows and program ledger decisions.
- `kpi-output.csv`: dry-run KPI/reporting rows.
- `exception-queue.csv`: attendance, staffing, or manual-review exceptions.
- `blocked-event-queue.csv`: rows that should not move forward.
- `error-log.csv`: malformed inputs that need source repair.

## Boundaries

- No live Airtable or Zapier writes.
- No child/family data in the first proof.
- No parent, staff, or child-facing messages.
- No staffing decisions.
- No ongoing support commitment until a written paid scope is accepted.
