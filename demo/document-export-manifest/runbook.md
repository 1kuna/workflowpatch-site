# Document Export Manifest Demo Runbook

This mock proof pack shows the first safe slice for a CRM document export or transfer:

1. Read source document rows from `source-documents.csv`.
2. Match each document to a destination record in `destination-records.csv`.
3. Block duplicate associations, missing destination records, and restricted files.
4. Treat unsupported destination attachments as export-only until the import path is verified.
5. Write transfer-ready rows to `transfer-manifest.csv`.
6. Write blocked or export-only rows to `exception-report.csv`.
7. Write malformed rows to `error-log.csv`.

Acceptance checks:

- Every transfer-ready row includes source object and destination entity evidence.
- Missing destination records do not move.
- Duplicate file associations are visible before transfer.
- Restricted files are blocked instead of silently skipped.
- Export-only rows remain usable even if destination file attachments are not supported.

This demo uses mock rows only. It does not connect to HubSpot, Nutshell, file storage, email, or any live CRM.
