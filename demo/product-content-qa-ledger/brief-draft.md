# Product content QA ledger brief draft

Generated from mock product catalog rows, content requests, and candidate media-output metadata. No client product files, paid media APIs, ComfyUI server, Merchant Center account, Buffer/Later scheduler, Shopify admin, or live ad account is connected.

## Accepted For Review
- REQ-901 / LAMP-001: identity, approved facts, metadata, and requested draft state are intact. Evidence: source=src/lamp-001-main.jpg; product_status=active; dimension=1600; metadata=yes; publish_status=draft.
- REQ-902 / LAMP-002: identity, approved facts, metadata, and requested draft state are intact. Evidence: source=src/lamp-002-main.jpg; product_status=active; dimension=1500; metadata=yes; publish_status=approval_required.

## Blocked Or Held Before Publishing
- REQ-905 / LAMP-001: live publish requested before QA handoff for Buffer.
- REQ-903 / LAMP-003: product is not active.
- REQ-904 / LAMP-004: candidate changes product, not just scene/background; banned claim detected: crystal; identity score below threshold; AI metadata missing for Google Shopping candidate.

## Errors
- REQ-906: product id missing from source of truth (LAMP-999).

## Boundary

The sprint can prove asset lineage, product-integrity checks, blocked-publish routing, and a handoff. It does not promise creative performance, operate paid media APIs, host generation infrastructure, or publish customer-facing assets without a separate scope.
