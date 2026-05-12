#!/usr/bin/env python3
"""Generate the WorkflowPatch HubSpot JSON stabilization proof outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MIN_CONFIDENCE = 0.7


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def flatten_intents(value: Any) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list):
        return flattened
    for item in value:
        if isinstance(item, dict):
            flattened.append(item)
        elif isinstance(item, list):
            flattened.extend(flatten_intents(item))
    return flattened


def first_name(full_name: str) -> str:
    return (full_name.strip().split() or [""])[0]


def main() -> int:
    webhook_rows = read_csv("landing-webhook-events.csv")
    response_rows = {row["request_id"]: row for row in read_csv("openai-intent-responses.csv")}

    normalized: list[dict[str, str]] = []
    review_queue: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for webhook in webhook_rows:
        request_id = webhook["request_id"]
        correlation_id = f"{request_id}:{webhook['tracking_id']}"
        email = webhook["email"].strip().lower()
        response_row = response_rows.get(request_id)
        if not response_row:
            errors.append(
                {
                    "request_id": request_id,
                    "error": "missing OpenAI response",
                    "evidence": correlation_id,
                    "blocked_at": webhook["received_at"],
                }
            )
            continue

        try:
            payload = json.loads(response_row["model_output_json"])
        except json.JSONDecodeError as exc:
            errors.append(
                {
                    "request_id": request_id,
                    "error": "malformed OpenAI JSON",
                    "evidence": f"{correlation_id} char={exc.pos}",
                    "blocked_at": response_row["response_received_at"],
                }
            )
            blocked.append(
                {
                    "request_id": request_id,
                    "block_reason": "model output is not valid JSON",
                    "evidence": correlation_id,
                    "reviewer_action": "Regenerate or manually correct the model output before HubSpot review.",
                }
            )
            continue

        lead = payload.get("lead", {})
        intents = flatten_intents(lead.get("intents"))
        if not email:
            errors.append(
                {
                    "request_id": request_id,
                    "error": "missing required email",
                    "evidence": correlation_id,
                    "blocked_at": webhook["received_at"],
                }
            )
            continue
        if not intents:
            blocked.append(
                {
                    "request_id": request_id,
                    "block_reason": "no usable intent array",
                    "evidence": correlation_id,
                    "reviewer_action": "Review payload shape before creating a HubSpot task.",
                }
            )
            continue

        top_intent = max(intents, key=lambda row: float(row.get("confidence", 0) or 0))
        confidence = float(top_intent.get("confidence", 0) or 0)
        if confidence < MIN_CONFIDENCE:
            blocked.append(
                {
                    "request_id": request_id,
                    "block_reason": "intent confidence below review threshold",
                    "evidence": f"{correlation_id} top_intent={top_intent.get('label', 'unknown')} confidence={confidence:.2f}",
                    "reviewer_action": "Review manually; do not prepare a HubSpot update from weak AI output.",
                }
            )
            continue

        draft = lead.get("recommended_email", {})
        hubspot_fields = {
            "email": email,
            "firstname": first_name(webhook["full_name"]),
            "company": webhook["company"],
            "lead_intent": top_intent.get("label", ""),
            "lead_urgency": lead.get("urgency", ""),
            "workflowpatch_evidence": correlation_id,
        }
        normalized.append(
            {
                "request_id": request_id,
                "email": email,
                "company": webhook["company"],
                "top_intent": str(top_intent.get("label", "")),
                "confidence": f"{confidence:.2f}",
                "urgency": str(lead.get("urgency", "")),
                "source_page": webhook["source_page"],
                "correlation_id": correlation_id,
                "status": "ready for HubSpot review",
                "evidence": f"intents={len(intents)} source_notes={len(lead.get('source_notes', []))}",
            }
        )
        review_queue.append(
            {
                "request_id": request_id,
                "action": "review HubSpot upsert",
                "email": email,
                "hubspot_fields_json": json.dumps(hubspot_fields, sort_keys=True),
                "review_reason": "human review before CRM write or email draft use",
                "draft_subject": str(draft.get("subject", "")),
            }
        )

    write_csv(
        "normalized-lead-ledger.csv",
        normalized,
        [
            "request_id",
            "email",
            "company",
            "top_intent",
            "confidence",
            "urgency",
            "source_page",
            "correlation_id",
            "status",
            "evidence",
        ],
    )
    write_csv(
        "hubspot-review-queue.csv",
        review_queue,
        ["request_id", "action", "email", "hubspot_fields_json", "review_reason", "draft_subject"],
    )
    write_csv(
        "blocked-payload-queue.csv",
        blocked,
        ["request_id", "block_reason", "evidence", "reviewer_action"],
    )
    write_csv(
        "error-log.csv",
        errors,
        ["request_id", "error", "evidence", "blocked_at"],
    )
    print(f"normalized_rows={len(normalized)}")
    print(f"review_rows={len(review_queue)}")
    print(f"blocked_rows={len(blocked)}")
    print(f"error_rows={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
