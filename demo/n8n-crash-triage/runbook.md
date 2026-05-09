# n8n Crash Triage Runbook

This is a mock WorkflowPatch proof surface. It uses no client data, no credentials, no live n8n instance, and no database connection.

## First Slice

One self-hosted n8n incident family:

1. Collect a small evidence pack: compose/env snapshot, Docker restart timestamps, n8n logs around crashes, database table counts, slow-query samples, retention settings, and current backup notes.
2. Build a triage ledger that separates restart storms, database bloat, missing queue mode, unproven backups, and credential boundaries.
3. Produce a migration-readiness gate list before any MySQL to Postgres cutover is discussed.

## Guardrails

- No production migration from a public thread.
- No credential export in the first proof.
- No claim of zero data loss until backup and restore evidence exists.
- No live workflow edits during the crash diagnosis window.
- No compliance, government, or financial guarantee.

## Acceptance Checks

- Every incident signal maps to a triage row.
- Any unproven restore path is blocked.
- Credential movement is blocked unless the owner provides a safe test path.
- The cutover gate stays `not_ready` until root-cause, backup, row-parity, and rollback evidence exist.
