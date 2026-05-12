# AI Ops Adoption Ledger Proof Runbook

## Source

Use redacted or synthetic rows from cross-functional AI operations requests: Sales, Customer Success, Marketing, Support, Finance, RevOps, Product, Internal Ops, Analytics, or similar teams. The useful first sample is 5-10 rows with source, team, requested action, system, owner, success metric, approval state, sensitive-data boundary, and whether a live action was requested. For internal-ops stacks, include agent/tool-action requests from systems such as Claude Code, MCP servers, Clay, Trigger.dev, Obsidian, workflow builders, reporting tools, or CRM previews.

## Transformation

Normalize each request into an AI ops ledger row. Apply owner, success-metric, approval, sensitive-data, live-action, and source-contract policy. Accepted rows move to owner review or scorecard preview. Weak rows go to owner review. Sensitive rows, live writes, and unapproved rollout actions go to a blocked-action queue. Malformed rows fail visibly in the error log.

## Destination

Deliver a written proof pack: source events, adoption policy, AI ops ledger, owner-review queue, blocked-action queue, error log, QA notes, and a handoff describing what can be safely scoped next.

## Excluded Live Actions

No live HubSpot, Salesforce, Zendesk, Intercom, Pylon, Segment, BigQuery, Snowflake, dbt, Retool, Notion, Claude Code, MCP, Clay, Trigger.dev, Obsidian, n8n, Zapier, Make, Gumloop, support-system, CRM, analytics, billing, employee, customer-data, or production writes. No credentials, no customer data, no financial records, no support tickets with personal data, no company-wide rollout, no employee training commitment, no legal/privacy/compliance advice, and no custom legal or HR commitment from the first proof.
