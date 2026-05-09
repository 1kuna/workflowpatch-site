#!/usr/bin/env python3
"""Generate the WorkflowPatch support reply approval demo outputs."""

from __future__ import annotations

import csv
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


def topic_for(row: dict[str, str]) -> str:
    hinted = row["category_hint"].strip().lower()
    if hinted:
        return hinted
    text = f"{row['subject']} {row['body']}".lower()
    if "price" in text or "subscription" in text or "plan" in text:
        return "pricing"
    if "booking" in text or "move" in text or "session" in text:
        return "booking"
    if "refund" in text or "dispute" in text or "charge" in text:
        return "refund"
    return "unknown"


def main() -> int:
    emails = read_csv("support-emails.csv")
    kb = {row["topic_key"]: row for row in read_csv("knowledge-base.csv")}
    already_drafted = {row["email_id"] for row in read_csv("send-history.csv")}
    seen_ids: set[str] = set()

    draft_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    ledger_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for email in emails:
        email_id = email["email_id"].strip()
        customer_email = email["customer_email"].strip()
        body = email["body"].strip()

        if not email_id or not customer_email or not body:
            error_rows.append(
                {
                    "email_id": email_id or "missing",
                    "error": "missing required email id, customer email, or body",
                    "evidence": f"customer_email={customer_email or 'missing'} body_present={'yes' if body else 'no'}",
                }
            )
            continue

        if email_id in seen_ids:
            error_rows.append(
                {
                    "email_id": email_id,
                    "error": "duplicate source email id",
                    "evidence": f"second row attempted customer_email={customer_email}",
                }
            )
            continue
        seen_ids.add(email_id)

        topic = topic_for(email)
        kb_row = kb.get(topic)
        if email_id in already_drafted:
            review_rows.append(
                {
                    "email_id": email_id,
                    "customer_email": customer_email,
                    "review_reason": "draft already exists",
                    "suggested_next_step": "Reviewer should decide whether to resend the prior approved answer.",
                    "evidence": "send-history contains this email_id",
                }
            )
            ledger_rows.append(
                {
                    "email_id": email_id,
                    "topic_key": topic,
                    "kb_source": kb_row["source_title"] if kb_row else "none",
                    "decision": "held for duplicate-send review",
                    "evidence": "send-history match",
                }
            )
            continue

        if kb_row is None:
            review_rows.append(
                {
                    "email_id": email_id,
                    "customer_email": customer_email,
                    "review_reason": "no approved knowledge source",
                    "suggested_next_step": "Support lead should write or approve the answer before automation drafts customer copy.",
                    "evidence": f"topic_key={topic}",
                }
            )
            ledger_rows.append(
                {
                    "email_id": email_id,
                    "topic_key": topic,
                    "kb_source": "none",
                    "decision": "held for source review",
                    "evidence": "no matching approved answer",
                }
            )
            continue

        if kb_row["requires_human_review"].strip().lower() == "yes":
            review_rows.append(
                {
                    "email_id": email_id,
                    "customer_email": customer_email,
                    "review_reason": "human review required",
                    "suggested_next_step": kb_row["approved_answer"],
                    "evidence": f"kb_source={kb_row['source_title']}",
                }
            )
            ledger_rows.append(
                {
                    "email_id": email_id,
                    "topic_key": topic,
                    "kb_source": kb_row["source_title"],
                    "decision": "held for staff review",
                    "evidence": "knowledge-base review flag",
                }
            )
            continue

        draft_rows.append(
            {
                "email_id": email_id,
                "customer_email": customer_email,
                "draft_subject": f"Re: {email['subject']}",
                "draft_body": (
                    f"Hi {email['customer_name']}, thanks for writing in. "
                    f"{kb_row['approved_answer']} I left this as a draft for review before it goes out."
                ),
                "approval_status": "needs human approval",
                "evidence": f"topic_key={topic}; kb_source={kb_row['source_title']}",
            }
        )
        ledger_rows.append(
            {
                "email_id": email_id,
                "topic_key": topic,
                "kb_source": kb_row["source_title"],
                "decision": "draft queued for approval",
                "evidence": "approved answer matched",
            }
        )

    write_csv(
        "draft-reply-queue.csv",
        draft_rows,
        ["email_id", "customer_email", "draft_subject", "draft_body", "approval_status", "evidence"],
    )
    write_csv(
        "review-queue.csv",
        review_rows,
        ["email_id", "customer_email", "review_reason", "suggested_next_step", "evidence"],
    )
    write_csv("source-ledger.csv", ledger_rows, ["email_id", "topic_key", "kb_source", "decision", "evidence"])
    write_csv("error-log.csv", error_rows, ["email_id", "error", "evidence"])

    print(f"draft_rows={len(draft_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
