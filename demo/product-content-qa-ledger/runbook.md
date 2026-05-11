# Product content QA ledger runbook

This is a mock WorkflowPatch proof pack for an ecommerce AI-content workflow. It is designed to prove the operating layer around generated product assets, not to claim ownership of the full creative stack.

## Inputs

- `product-catalog.csv`: approved product facts, banned claims, and product status.
- `content-requests.csv`: requested asset type, source image reference, publishing target, and draft/publish state.
- `candidate-outputs.csv`: candidate output metadata, product-identity check result, background-only check result, image dimension, AI metadata state, and caption draft.

## Outputs

- `product-content-qa-ledger.csv`: row-level decision ledger.
- `review-queue.csv`: repair or provenance rows that need review.
- `blocked-output-queue.csv`: asset rows that cannot become publish-ready.
- `publish-hold-queue.csv`: live-publish requests held before external action.
- `error-log.csv`: missing source-of-truth or failed-render rows.
- `brief-draft.md`: internal handoff summary.

## Acceptance Checks

- Source product id must exist in the product catalog.
- Product status must be active.
- Candidate render must be ready.
- Product identity must match the source product.
- Candidate must preserve the product and only change background/scene where requested.
- Candidate claims must stay inside approved facts.
- Banned claims and promotional overlays are blocked.
- Main commerce images target at least 1500px.
- AI provenance metadata must be preserved for generated assets, especially commerce-channel handoff rows.
- Live publish requests stay in a hold queue until separately approved.

## Exclusions

- No paid media API runs.
- No live Merchant Center, Shopify, Buffer, Later, Meta, TikTok, or Amazon account access.
- No ComfyUI hosting or model-cost commitment.
- No creative-performance guarantee.
- No customer-facing publish action without a separate written scope.
