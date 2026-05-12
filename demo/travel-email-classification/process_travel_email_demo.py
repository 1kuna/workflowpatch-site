#!/usr/bin/env python3
"""Generate the WorkflowPatch travel email classification proof outputs."""

from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def keyword_hits(text: str, keywords: str) -> list[str]:
    hits: list[str] = []
    for keyword in keywords.split("|"):
        keyword = keyword.strip()
        if keyword and re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])", text):
            hits.append(keyword)
    return hits


def score_email(row: dict[str, str], rules: list[dict[str, str]]) -> list[dict[str, str]]:
    text = f"{row['subject']} {row['body_excerpt']}".lower()
    scored: list[dict[str, str]] = []
    for rule in rules:
        hits = keyword_hits(text, rule["keywords"].lower())
        if not hits:
            continue
        base = float(rule["min_confidence"])
        confidence = min(0.97, base + (len(hits) - 1) * 0.05)
        scored.append(
            {
                "label": rule["label"],
                "confidence": f"{confidence:.2f}",
                "hits": ";".join(hits),
                "sheets_status": rule["sheets_status"],
                "slack_required": rule["slack_required"],
            }
        )
    scored.sort(key=lambda item: float(item["confidence"]), reverse=True)
    return scored


def main() -> int:
    emails = read_csv("gmail-sample-emails.csv")
    rules = read_csv("classification-rules.csv")

    ledger: list[dict[str, str]] = []
    sheets_rows: list[dict[str, str]] = []
    slack_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for email in emails:
        message_id = email["message_id"]
        if not email["received_at"] or not email["from_email"]:
            errors.append(
                {
                    "message_id": message_id,
                    "error": "missing required Gmail metadata",
                    "evidence": f"received_at={email['received_at'] or 'missing'} from={email['from_email'] or 'missing'}",
                }
            )
            continue

        if email["auto_submitted"].strip().lower() == "true":
            review_rows.append(
                {
                    "message_id": message_id,
                    "reason": "auto-reply loop protection",
                    "suggested_action": "Do not auto-reply or forward. Mark thread as protected.",
                    "evidence": f"thread_id={email['thread_id']} subject={email['subject']}",
                }
            )
            continue

        if not email["client_account"].strip():
            errors.append(
                {
                    "message_id": message_id,
                    "error": "missing client account key",
                    "evidence": f"from={email['from_email']} language={email['language']} subject={email['subject']}",
                }
            )
            continue

        scored = score_email(email, rules)
        if not scored:
            review_rows.append(
                {
                    "message_id": message_id,
                    "reason": "no confident category",
                    "suggested_action": "Review manually and add a rule only after approval.",
                    "evidence": f"language={email['language']} subject={email['subject']}",
                }
            )
            continue

        top = scored[0]
        second = scored[1] if len(scored) > 1 else None
        if second and float(top["confidence"]) - float(second["confidence"]) < 0.08:
            review_rows.append(
                {
                    "message_id": message_id,
                    "reason": "ambiguous category",
                    "suggested_action": "Human chooses invoice, booking change, or split handling before Sheets or Slack action.",
                    "evidence": f"top={top['label']} {top['confidence']} second={second['label']} {second['confidence']}",
                }
            )
            continue

        reference = f"TRV-{email['received_at'][:10].replace('-', '')}-{message_id[-4:]}"
        ledger.append(
            {
                "message_id": message_id,
                "thread_id": email["thread_id"],
                "reference": reference,
                "client_account": email["client_account"],
                "language": email["language"],
                "label": top["label"],
                "confidence": top["confidence"],
                "status": top["sheets_status"],
                "evidence": f"hits={top['hits']}",
            }
        )
        sheets_rows.append(
            {
                "reference": reference,
                "message_id": message_id,
                "client_account": email["client_account"],
                "stage": top["sheets_status"],
                "category": top["label"],
                "received_at": email["received_at"],
                "next_owner": "sales_ops" if top["label"] == "hotel_update" else "operations",
            }
        )
        if top["slack_required"].lower() == "true":
            slack_rows.append(
                {
                    "message_id": message_id,
                    "channel": "#sales-ops",
                    "draft_text": f"{top['label']} for {email['client_account']}: {email['subject']}",
                    "review_required": "true",
                    "evidence": reference,
                }
            )

    write_csv(
        "classification-ledger.csv",
        ledger,
        ["message_id", "thread_id", "reference", "client_account", "language", "label", "confidence", "status", "evidence"],
    )
    write_csv(
        "sheets-status-queue.csv",
        sheets_rows,
        ["reference", "message_id", "client_account", "stage", "category", "received_at", "next_owner"],
    )
    write_csv(
        "slack-escalation-drafts.csv",
        slack_rows,
        ["message_id", "channel", "draft_text", "review_required", "evidence"],
    )
    write_csv(
        "review-queue.csv",
        review_rows,
        ["message_id", "reason", "suggested_action", "evidence"],
    )
    write_csv(
        "error-log.csv",
        errors,
        ["message_id", "error", "evidence"],
    )
    print(f"classified_rows={len(ledger)}")
    print(f"sheets_rows={len(sheets_rows)}")
    print(f"slack_drafts={len(slack_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"error_rows={len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
