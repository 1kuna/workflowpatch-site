# HubSpot RingCentral QA Proof Runbook

## Source

Use one redacted or synthetic export containing HubSpot contact or deal events, RingCentral call/activity events, and Vercel-form submission rows. The first proof does not need credentials, live HubSpot access, live RingCentral access, call recordings, customer data, or production writes.

## Transformation

Normalize each event into a review ledger, apply the field-map policy, match contact and company identity, block duplicates, hold recording-dependent activity, surface missing owner/source fields, and create dashboard/forecast review rows before any write.

## Destination

The output is a written handoff containing:

- sync review ledger,
- dashboard and forecast review queue,
- blocked write queue,
- SOP and training handoff,
- error log,
- source field-map policy.

## Useful Sample

A useful first sample is 5 to 10 redacted or synthetic events with one Vercel form submission, one RingCentral call log, one HubSpot deal-stage change, one duplicate form submit, and one malformed form event.

## Out Of Scope

- live HubSpot writes,
- live RingCentral actions,
- call recordings,
- customer data,
- credentials,
- outbound calls,
- outbound email,
- SMS sends,
- employee application flow,
- interviews,
- custom legal, HR, payroll, or staffing commitments.
