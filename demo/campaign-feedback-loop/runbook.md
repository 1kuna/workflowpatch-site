# Campaign Feedback Loop Demo Runbook

This is a mock WorkflowPatch proof pack. It does not use client data, ESP credentials, ad accounts, CRM credentials, social accounts, or live connected systems.

## Source

- `campaign-briefs.csv`: campaign, channel, segment, offer, goal, and active/paused status.
- `asset-primitives.csv`: approved claims, banned terms, and asset approval status.
- `performance-events.csv`: recent performance rows by campaign.
- `candidate-outputs.csv`: AI-style next-test drafts and proposed external copy.

## Transformation

`process_campaign_feedback_demo.py` joins candidate drafts to campaign briefs, approved asset primitives, and performance rows. It calculates click rate, conversion rate, and ROI after cost, checks data freshness, blocks paused campaigns, and blocks banned claims before review.

## Destination

- `campaign-feedback-ledger.csv`: evidence-backed next-test ledger.
- `review-queue.csv`: human approval queue for candidate campaign changes.
- `blocked-output-queue.csv`: drafts or campaigns that must not be sent.
- `error-log.csv`: missing or mismatched source evidence.
- `brief-draft.md`: sample internal brief grounded in the ledger.

## Acceptance Checks

- Paused campaigns cannot produce external output.
- Drafts with banned claims are blocked before review.
- Stale performance data is routed to review before new tests are approved.
- Every review row cites campaign, asset, data freshness, and model confidence.
- No ESP send, CRM write, ad change, or social post happens automatically.
