# GTM Signal Routing Proof Runbook

## Source

Use one redacted or synthetic set of Clay, HubSpot, product-usage, call-intelligence, enrichment, or data-warehouse events. The first proof does not need credentials, live CRM access, prospect lists, customer recordings, patient or clinical data, or outbound-sequence access.

## Transformation

Normalize each event into a GTM signal ledger, apply account-key, duplicate, sensitive-source, and live-action policies, then route accepted rows to owner review and draft-only CRM previews. Unusable events stop in a visible error log instead of being silently skipped.

## Destination

The output is a written handoff containing:

- GTM signal ledger,
- scoring and routing policy,
- owner review queue,
- draft-only CRM update preview,
- blocked action queue,
- error log,
- source contract notes.

## Useful Sample

A useful first sample is 5 to 10 redacted or synthetic GTM events that include at least one clean account-scoring row, one demo or buying-committee signal, one expansion or activation-risk signal, one duplicate, one missing-key error, and one row that must not trigger a live CRM or outreach action.

## Out Of Scope

- live HubSpot, Salesforce, Clay, Attention, Gong, BigQuery, Apollo, enrichment, or data-warehouse writes,
- live outbound sequence enrollment,
- prospect-facing messages,
- customer-facing messages,
- call recordings,
- patient, clinical, or private customer data,
- credentials,
- deliverability advice,
- broad GTM strategy ownership,
- custom legal, HR, staffing, or employee commitments.
