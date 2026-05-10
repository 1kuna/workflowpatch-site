# Property Booking Sync Runbook

## Scope

This mock proof turns one redacted property, booking, or owner event family into:

- an Airtable-ready property state ledger,
- a HubSpot sync review queue,
- a contract/payment exception log,
- a blocked sync queue,
- a hard-error log.

## Inputs

- One redacted property or booking sample.
- Airtable fields that represent operating state.
- HubSpot object and sync direction.
- Contract and payment exception rules.
- A list of forbidden owner, guest, payment, and contract fields.

## First-Proof Boundaries

- No live owner or guest data.
- No live Airtable or HubSpot writes.
- No owner or guest communication.
- No contract, payment, commission, or availability decision.
- No full property-management-system rebuild.

## Acceptance Checks

- Clean property, booking, and owner rows reach the ledger and review queue.
- Contract and payment uncertainty reaches the exception log.
- Private-owner, ambiguous-match, unknown-object, duplicate, and malformed rows block visibly.
- The run can be repeated without duplicate side effects.
