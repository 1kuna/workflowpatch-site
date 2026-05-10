# HTML Review Queue Demo Runbook

Purpose: prove a first batch of HTML pages can be reviewed as an approval queue instead of promising a full-site rewrite or upload.

Inputs:

- `html-pages.csv`: mock page paths, titles, and small HTML excerpts.
- `review-rules.csv`: review rules for SEO, code, stale copy, and upload blockers.

Outputs:

- `issue-queue.csv`: every issue found by page.
- `fix-draft-queue.csv`: rows safe enough for a proposed fix draft.
- `blocked-review.csv`: rows needing human review before a page is changed or uploaded.
- `run-log.csv`: page-level run summary.
- `error-log.csv`: malformed input rows.

Acceptance checks:

1. Missing file paths are blocked.
2. Empty links are blocked before upload.
3. Missing image alt text becomes a fix draft row.
4. Generic or thin meta descriptions become fix draft rows.
5. Stale or held pages route to human review.
6. No page is published or uploaded from this first proof.

Paid implementation boundary:

- Start with 10 to 20 approved sample pages and the buyer's review criteria.
- Produce an issue queue, fix draft queue, blocked-review rows, run log, and written handoff.
- Do not guarantee rankings, publish pages, process the full site, or make final brand/editorial calls in the first proof.
