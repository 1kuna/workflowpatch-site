# Campaign Feedback Loop Proof Runbook

This WorkflowPatch proof pack uses redacted or synthetic campaign inputs. It does not use client data, ESP credentials, ad accounts, CRM credentials, social accounts, or live connected systems.

## Source

- `campaign-briefs.csv`: campaign, channel, segment, offer, goal, and active/paused status.
- `asset-primitives.csv`: approved claims, banned terms, and asset approval status.
- `performance-events.csv`: recent performance rows by campaign.
- `candidate-outputs.csv`: AI-style next-test drafts and proposed external copy.

Useful buyer sample:

- one campaign family or lifecycle segment,
- a redacted performance export,
- approved and banned claim examples,
- the review destination where proposed outputs should land.

## Transformation

`process_campaign_feedback_demo.py` joins candidate drafts to campaign briefs, approved asset primitives, and performance rows. It calculates click rate, conversion rate, and ROI after cost, checks data freshness, blocks paused campaigns, and blocks banned claims before review.

## Destination

- `campaign-feedback-ledger.csv`: evidence-backed next-test ledger.
- `review-queue.csv`: human approval queue for candidate campaign changes.
- `blocked-output-queue.csv`: drafts or campaigns that must not be sent.
- `error-log.csv`: missing or mismatched source evidence.
- `brief-draft.md`: sample internal brief grounded in the ledger.

## Live Boundary

The first slice stops at internal review artifacts. It does not publish, schedule, send, update CRM records, modify ads, change social posts, touch customer data, or claim campaign lift.

## Acceptance Checks

- Paused campaigns cannot produce external output.
- Drafts with banned claims are blocked before review.
- Stale performance data is routed to review before new tests are approved.
- Every review row cites campaign, asset, data freshness, and model confidence.
- No ESP send, CRM write, ad change, or social post happens automatically.
