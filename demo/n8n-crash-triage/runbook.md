# n8n Crash Triage Runbook

This proof surface uses redacted or synthetic evidence. It uses no client data, no credentials, no live n8n instance, and no database connection.

## First Slice

One self-hosted n8n incident family:

1. Collect a small evidence pack: compose/env snapshot, Docker restart timestamps, n8n logs around crashes, database table counts, slow-query samples, retention settings, and current backup notes.
2. Build a triage ledger that separates restart storms, database bloat, missing queue mode, unproven backups, and credential boundaries.
3. Produce a migration-readiness gate list before any MySQL to Postgres cutover is discussed.

## Safe Evidence Pack

- Secrets-removed compose and env shape.
- Crash-window logs and restart timestamps.
- Execution table counts, retention settings, and slow-query clues.
- Backup notes, restore proof, and main or queue mode state.

## Returned Artifacts

- Crash-signal triage ledger.
- Migration-readiness checklist.
- Backup and restore verification queue.
- Blocked-action/error log for unsafe credential movement, unproven restore paths, and missing rollback approval.

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
