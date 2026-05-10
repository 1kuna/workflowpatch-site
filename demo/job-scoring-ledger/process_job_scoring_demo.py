#!/usr/bin/env python3
"""Generate the WorkflowPatch job scoring ledger demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T09:16:00Z"

TITLE_TERMS = ("automation", "workflow", "revops", "reliability", "n8n")
CORE_SKILLS = ("n8n", "airtable", "google sheets", "telegram", "api", "monitoring", "error handling")


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_int(value: str) -> int:
    try:
        return int(value)
    except ValueError:
        return 0


def score_row(row: dict[str, str]) -> tuple[int, dict[str, int]]:
    title = row["title"].lower()
    skills = row["required_skills"].lower()
    remote_policy = row["remote_policy"].lower()
    seniority = row["seniority"].lower()
    compensation_max = parse_int(row["compensation_max"])
    posted_days = parse_int(row["posted_days_ago"])

    score_parts = {
        "title_match": 25 if any(term in title for term in TITLE_TERMS) else 5,
        "skill_match": min(30, sum(6 for skill in CORE_SKILLS if skill in skills)),
        "remote_match": 15 if remote_policy == "remote" else 10 if remote_policy == "hybrid" else 0,
        "seniority_match": 10 if seniority in {"mid", "senior"} else 3,
        "compensation_match": 10 if compensation_max >= 50000 else 5 if compensation_max >= 35000 else 0,
        "freshness_match": 10 if posted_days <= 5 else 6 if posted_days <= 10 else 0,
    }
    return sum(score_parts.values()), score_parts


def blocked(row: dict[str, str], reason: str, detail: str) -> dict[str, str]:
    return {
        "job_id": row["job_id"] or "missing",
        "company": row["company"] or "missing",
        "title": row["title"] or "missing",
        "reason": reason,
        "detail": detail,
        "next_step": "review_before_any_live_source_or_telegram_action",
    }


def main() -> int:
    rows = read_csv("job-export.csv")
    seen_keys: set[str] = set()
    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in rows:
        required = ("job_id", "company", "title", "apply_url", "duplicate_key", "source_boundary")
        missing = [field for field in required if not row[field].strip()]
        if missing:
            error_rows.append(
                {
                    "job_id": row["job_id"] or "missing",
                    "error_code": "missing_required_job_field",
                    "error_detail": ",".join(missing),
                }
            )
            continue

        if row["source_boundary"] != "approved_export_only":
            blocked_rows.append(blocked(row, "live_source_or_scrape_scope", "Use an approved export or API result before scoring."))
            continue

        duplicate_key = row["duplicate_key"].strip()
        if duplicate_key in seen_keys:
            blocked_rows.append(blocked(row, "duplicate_job_key", f"duplicate_key={duplicate_key}"))
            continue
        seen_keys.add(duplicate_key)

        score, parts = score_row(row)
        decision = "telegram_review_draft" if score >= 80 else "ledger_only_review" if score >= 65 else "reject_below_threshold"

        if score < 65:
            blocked_rows.append(blocked(row, "below_score_threshold", f"score={score}"))
            continue

        ledger_rows.append(
            {
                "job_id": row["job_id"],
                "company": row["company"],
                "title": row["title"],
                "score": str(score),
                "decision": decision,
                "score_parts": ";".join(f"{key}={value}" for key, value in parts.items()),
                "destination": row["destination"],
                "processed_at": GENERATED_AT,
            }
        )

        if decision == "telegram_review_draft" and row["telegram_preview_allowed"] == "true":
            review_rows.append(
                {
                    "job_id": row["job_id"],
                    "telegram_channel": "operator-review-draft",
                    "message_status": "draft_only_not_sent",
                    "message_preview": f"{score} fit: {row['title']} at {row['company']} - {row['apply_url']}",
                    "approval_needed": "human_review_before_any_telegram_send",
                }
            )

    write_csv(
        "job-scoring-ledger.csv",
        ledger_rows,
        ["job_id", "company", "title", "score", "decision", "score_parts", "destination", "processed_at"],
    )
    write_csv(
        "telegram-review-queue.csv",
        review_rows,
        ["job_id", "telegram_channel", "message_status", "message_preview", "approval_needed"],
    )
    write_csv(
        "blocked-job-queue.csv",
        blocked_rows,
        ["job_id", "company", "title", "reason", "detail", "next_step"],
    )
    write_csv("error-log.csv", error_rows, ["job_id", "error_code", "error_detail"])

    print(f"source_rows={len(rows)}")
    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
