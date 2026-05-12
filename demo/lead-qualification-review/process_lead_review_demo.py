#!/usr/bin/env python3
"""Generate the WorkflowPatch lead qualification review proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
APPROVED_SOURCES = {"form", "referral", "community_reply", "partner_sheet"}


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    rules = read_csv("qualification-rules.csv")
    keyword_rules = [rule for rule in rules if rule["rule_type"] == "keyword"]
    existing = {row["email"].lower(): row for row in read_csv("existing-crm.csv")}

    ledger_rows: list[dict[str, str]] = []
    approval_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for lead in read_csv("lead-sources.csv"):
        lead_id = lead["lead_id"]
        company = lead["company"].strip()
        email = lead["email"].strip().lower()
        source = lead["source"].strip()
        need = lead["raw_need"].strip()

        if not company or not email or not source:
            error_rows.append(
                {
                    "lead_id": lead_id,
                    "status": "error",
                    "reason": "missing required routing field",
                    "evidence": "company, email, and source are required before review",
                }
            )
            continue

        matched_keywords = [
            rule["value"]
            for rule in keyword_rules
            if rule["value"].lower() in need.lower()
        ]
        score = sum(int(rule["weight"]) for rule in keyword_rules if rule["value"].lower() in need.lower())
        if lead["consent_status"] == "explicit":
            score += 2
        if source in APPROVED_SOURCES:
            score += 1
        if lead["crm_status"] == "not_found":
            score += 1
        if int(lead["last_activity_days"]) <= 14:
            score += 1

        decision = "review_ready" if score >= 5 else "context_review"
        reviewer_action = "Map source fields, qualification criteria, and CRM destination before any write."
        evidence = f"source={source}; consent={lead['consent_status']}; crm_status={lead['crm_status']}; keywords={'|'.join(matched_keywords) or 'none'}"

        if email in existing:
            decision = "blocked_duplicate"
            reviewer_action = f"Existing CRM contact {existing[email]['crm_contact_id']} owned by {existing[email]['owner']}; route to owner before any update."
            blocked_rows.append(
                {
                    "lead_id": lead_id,
                    "company": company,
                    "reason": "duplicate existing CRM contact",
                    "reviewer_action": reviewer_action,
                }
            )
        elif lead["consent_status"] != "explicit":
            decision = "blocked_consent"
            reviewer_action = "Confirm permission or buyer-created context before any outreach, enrichment, or CRM write."
            blocked_rows.append(
                {
                    "lead_id": lead_id,
                    "company": company,
                    "reason": "consent or source permission not confirmed",
                    "reviewer_action": reviewer_action,
                }
            )
        elif source == "scraped_list":
            decision = "blocked_source"
            reviewer_action = "Do not use scraped-list rows for first-contact automation."
            blocked_rows.append(
                {
                    "lead_id": lead_id,
                    "company": company,
                    "reason": "source is not approved for first-contact automation",
                    "reviewer_action": reviewer_action,
                }
            )
        elif decision in {"review_ready", "context_review"}:
            approval_rows.append(
                {
                    "lead_id": lead_id,
                    "company": company,
                    "owner": "sales ops",
                    "approved_action": "prepare CRM update and reporting handoff only",
                    "draft_note": f"{company}: review {', '.join(matched_keywords) or 'lead'} evidence before any CRM write or outreach.",
                    "reviewer_action": reviewer_action,
                }
            )

        ledger_rows.append(
            {
                "lead_id": lead_id,
                "company": company,
                "source": source,
                "score": str(score),
                "decision": decision,
                "evidence": evidence,
                "next_step": reviewer_action,
            }
        )

    write_csv(
        "lead-review-ledger.csv",
        ledger_rows,
        ["lead_id", "company", "source", "score", "decision", "evidence", "next_step"],
    )
    write_csv(
        "approval-queue.csv",
        approval_rows,
        ["lead_id", "company", "owner", "approved_action", "draft_note", "reviewer_action"],
    )
    write_csv("blocked-leads.csv", blocked_rows, ["lead_id", "company", "reason", "reviewer_action"])
    write_csv("error-log.csv", error_rows, ["lead_id", "status", "reason", "evidence"])

    print(f"ledger_rows={len(ledger_rows)}")
    print(f"approval_rows={len(approval_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
