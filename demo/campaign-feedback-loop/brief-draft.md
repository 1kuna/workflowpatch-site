# Campaign feedback loop brief draft

Generated from mock campaign briefs, approved asset primitives, performance events, and candidate next-test drafts. No client data, no connected ESP, no CRM, and no social posting.

## Review First
- CFB-101: Approve a small controlled scale test after inventory and brand review. Evidence: brief=CFB-101; asset=AST-201; freshness=5h; confidence=0.84.
- CFB-103: Approve a small controlled scale test after inventory and brand review. Evidence: brief=CFB-103; asset=AST-203; freshness=6h; confidence=0.81.
- CFB-105: Refresh performance data before approving any new variation. Evidence: brief=CFB-105; asset=AST-205; freshness=31h; confidence=0.69.

## Blocked Before External Output
- OUT-304: campaign is not active (paused).
- OUT-306: draft contains banned claim (free forever).

## Boundary

The agent can draft hypotheses and next-test copy, but deterministic checks own campaign status, approved claims, freshness, and banned-claim blocking before a human approves any external output.
