# WorkflowPatch Care Intake Review Demo Runbook

This mock proof shows a safe first slice for care-provider intake, scheduling, and outreach operations.

Boundary:

- Uses synthetic and redacted examples only.
- No PHI, patient records, clinical notes, credentials, live scheduling, live CRM writes, or outbound messages.
- Public job or role evidence can shape a workflow hypothesis, but it is not treated as client data.

First slice:

1. Normalize source events from web forms, email, SMS consent events, and public operations signals.
2. Apply consent, duplicate, sensitive-data, and channel rules.
3. Route clean items to an intake or scheduling review queue.
4. Block opt-outs, sensitive/clinical content, and live outbound actions.
5. Produce a written handoff before any real integration work.

Acceptance checks:

- Every accepted row has source evidence and a matched policy.
- Every blocked row has an explicit reason.
- Outbound messages remain draft-only or blocked.
- Scheduling and CRM updates remain internal write plans until separately approved.
