# MVP Governance Review Runbook

## Scope

This mock proof turns one redacted or synthetic MVP communication source into:

- a review-state ledger,
- an approved communication draft queue,
- a blocked communication queue,
- a hard-error log.

## Inputs

- One redacted or synthetic investor-update, compliance-note, or product-map source.
- Airtable or Softr review states.
- Draft-output requirements.
- Brand and compliance boundaries.
- Blocked/error examples.

## First-Proof Boundaries

- No live investor data.
- No external investor messages.
- No compliance claim, legal advice, or regulatory judgment.
- No live Airtable, Softr, Zapier, or Make access.
- No whole-MVP ownership or local collaboration promise.

## Acceptance Checks

- Clean rows become review-state and draft-queue rows.
- Unsupported claims, off-brand text, external-send steps, sensitive investor data, unclear review states, duplicates, and malformed rows block visibly.
- Draft outputs stay approval-required and dry-run only.
