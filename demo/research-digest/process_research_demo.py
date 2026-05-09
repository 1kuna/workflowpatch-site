#!/usr/bin/env python3
"""Generate the WorkflowPatch research digest demo outputs."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TODAY = date(2026, 5, 9)


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def score_item(text: str, watchlist: list[dict[str, str]]) -> tuple[int, list[str], str]:
    normalized = text.lower()
    matches: list[tuple[str, str, int]] = []
    for row in watchlist:
        keyword = row["keyword"].strip()
        if keyword.lower() in normalized:
            matches.append((keyword, row["topic"], int(row["weight"])))
    score = min(sum(weight for _, _, weight in matches), 100)
    if not matches:
        return 0, [], "unmatched"
    top_topic = Counter(topic for _, topic, _ in matches).most_common(1)[0][0]
    return score, [keyword for keyword, _, _ in matches], top_topic


def main() -> int:
    items = read_csv("source-items.csv")
    watchlist = read_csv("watchlist.csv")
    seen_urls: set[str] = set()

    digest_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []
    ledger_rows: list[dict[str, str]] = []

    for row in items:
        item_id = row["item_id"].strip()
        title = row["title"].strip()
        url = row["url"].strip()
        published = parse_date(row["published_at"])

        if not item_id or not title or not url or published is None:
            error_rows.append(
                {
                    "item_id": item_id or "missing",
                    "source": row["source"],
                    "error": "missing required source, URL, title, or valid published date",
                    "evidence": f"title={title or 'missing'} url={url or 'missing'} published_at={row['published_at'] or 'missing'}",
                }
            )
            continue

        text = f"{title} {row['summary']}"
        score, matched_keywords, topic = score_item(text, watchlist)
        age_days = (TODAY - published).days
        duplicate = url in seen_urls
        seen_urls.add(url)

        if duplicate:
            decision = "review"
            review_rows.append(
                {
                    "item_id": item_id,
                    "issue": "duplicate source URL",
                    "score": str(score),
                    "evidence": f"url={url} matched_keywords={';'.join(matched_keywords) or 'none'}",
                    "reviewer_action": "Compare against the first seen item before adding to outreach.",
                }
            )
        elif age_days > 30:
            decision = "review"
            review_rows.append(
                {
                    "item_id": item_id,
                    "issue": "stale source",
                    "score": str(score),
                    "evidence": f"published_at={published.isoformat()} age_days={age_days}",
                    "reviewer_action": "Use only as market signal unless the buyer renewed the request.",
                }
            )
        elif score >= 60:
            decision = "digest"
            digest_rows.append(
                {
                    "item_id": item_id,
                    "topic": topic,
                    "score": str(score),
                    "status": "ready for teardown",
                    "digest_line": f"{row['source']}: {title}",
                    "source_url": url,
                    "evidence": ";".join(matched_keywords),
                }
            )
        elif score >= 35:
            decision = "review"
            review_rows.append(
                {
                    "item_id": item_id,
                    "issue": "medium-fit source",
                    "score": str(score),
                    "evidence": f"matched_keywords={';'.join(matched_keywords)}",
                    "reviewer_action": "Manually decide whether budget and urgency are strong enough.",
                }
            )
        else:
            decision = "review"
            review_rows.append(
                {
                    "item_id": item_id,
                    "issue": "low-fit or too generic",
                    "score": str(score),
                    "evidence": f"matched_keywords={';'.join(matched_keywords) or 'none'}",
                    "reviewer_action": "Do not add to outreach unless a clearer workflow or budget appears.",
                }
            )

        ledger_rows.append(
            {
                "item_id": item_id,
                "decision": decision,
                "score": str(score),
                "matched_keywords": ";".join(matched_keywords) or "none",
                "published_at": published.isoformat(),
                "source_url": url,
            }
        )

    write_csv(
        "digest-queue.csv",
        digest_rows,
        ["item_id", "topic", "score", "status", "digest_line", "source_url", "evidence"],
    )
    write_csv(
        "review-queue.csv",
        review_rows,
        ["item_id", "issue", "score", "evidence", "reviewer_action"],
    )
    write_csv(
        "source-ledger.csv",
        ledger_rows,
        ["item_id", "decision", "score", "matched_keywords", "published_at", "source_url"],
    )
    write_csv(
        "error-log.csv",
        error_rows,
        ["item_id", "source", "error", "evidence"],
    )

    print(f"digest_rows={len(digest_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
