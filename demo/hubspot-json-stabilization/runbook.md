# HubSpot JSON Stabilization Demo Runbook

This mock proof shows the first safe slice for a landing-page webhook -> OpenAI intent output -> HubSpot review path.

## Inputs

- `landing-webhook-events.csv`: redacted landing-page submissions.
- `openai-intent-responses.csv`: mock model outputs, including nested arrays, malformed JSON, weak confidence, and valid rows.
- `hubspot-field-map.csv`: minimal field map and review rules.

## Outputs

- `normalized-lead-ledger.csv`: rows that passed JSON parsing, required-field checks, nested-array flattening, and confidence threshold.
- `hubspot-review-queue.csv`: review-first HubSpot upsert candidates. These are not live writes.
- `blocked-payload-queue.csv`: rows needing human review before any CRM action.
- `error-log.csv`: hard failures such as malformed JSON or missing required identity fields.

## Guardrails

- No client data or credentials are used.
- No HubSpot account is connected.
- No customer email is sent.
- Nested arrays are flattened before batching.
- Malformed or low-confidence AI output is blocked before HubSpot review.
- Every accepted row keeps a correlation id and source evidence.

## Acceptance Checks

1. Valid nested intent arrays become one normalized lead row.
2. Nested arrays inside nested arrays are flattened.
3. Missing email creates a hard error.
4. Malformed model JSON creates a hard error and a blocked review row.
5. Low-confidence model output is blocked, not written.
6. HubSpot fields are visible in the review queue before any production write.

## Rebuild

```bash
python3 process_hubspot_json_demo.py
```
