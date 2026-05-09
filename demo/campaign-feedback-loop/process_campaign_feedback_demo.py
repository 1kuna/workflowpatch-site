#!/usr/bin/env python3
"""Generate the WorkflowPatch campaign feedback loop demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2%}"


def money(value: float) -> str:
    return f"{value:.2f}"


def contains_banned(copy: str, banned_terms: str) -> str:
    lower = copy.lower()
    for term in [item.strip().lower() for item in banned_terms.split(";") if item.strip()]:
        if term and term in lower:
            return term
    return ""


def main() -> int:
    briefs = {row["campaign_id"]: row for row in read_csv("campaign-briefs.csv")}
    assets = {row["asset_id"]: row for row in read_csv("asset-primitives.csv")}
    performance = {row["campaign_id"]: row for row in read_csv("performance-events.csv")}

    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for candidate in read_csv("candidate-outputs.csv"):
        campaign_id = candidate["campaign_id"]
        asset_id = candidate["asset_id"]
        brief = briefs.get(campaign_id)
        asset = assets.get(asset_id)
        event = performance.get(campaign_id)

        if not brief:
            error_rows.append({"candidate_id": candidate["candidate_id"], "status": "error", "reason": "campaign brief missing", "evidence": campaign_id})
            continue
        if not asset:
            error_rows.append({"candidate_id": candidate["candidate_id"], "status": "error", "reason": "asset primitive missing", "evidence": asset_id})
            continue
        if asset["campaign_id"] != campaign_id:
            error_rows.append({"candidate_id": candidate["candidate_id"], "status": "error", "reason": "asset belongs to another campaign", "evidence": f"{asset_id}->{asset['campaign_id']}"})
            continue
        if not event:
            error_rows.append({"candidate_id": candidate["candidate_id"], "status": "error", "reason": "performance event missing", "evidence": campaign_id})
            continue

        banned_hit = contains_banned(candidate["external_copy"], asset["banned_terms"])
        if brief["status"] != "active":
            blocked_rows.append({"candidate_id": candidate["candidate_id"], "campaign_id": campaign_id, "reason": "campaign is not active", "evidence": brief["status"], "reviewer_action": "Confirm campaign owner before any next test."})
            continue
        if asset["status"] != "approved":
            blocked_rows.append({"candidate_id": candidate["candidate_id"], "campaign_id": campaign_id, "reason": "asset primitive is not approved", "evidence": asset["status"], "reviewer_action": "Approve or replace the source asset before drafting."})
            continue
        if banned_hit:
            blocked_rows.append({"candidate_id": candidate["candidate_id"], "campaign_id": campaign_id, "reason": "draft contains banned claim", "evidence": banned_hit, "reviewer_action": "Rewrite before review; do not send externally."})
            continue

        sends_or_impressions = int(event["sends_or_impressions"])
        clicks = int(event["clicks"])
        conversions = int(event["conversions"])
        revenue = float(event["revenue"])
        cost = float(event["cost"])
        freshness = int(event["data_freshness_hours"])

        click_rate = None if sends_or_impressions == 0 else clicks / sends_or_impressions
        conversion_rate = None if clicks == 0 else conversions / clicks
        roi = None if cost == 0 else (revenue - cost) / cost
        decision = "monitor"
        reviewer_action = "Keep the current test and watch the next window."

        if freshness > 24:
            decision = "refresh_data_before_test"
            reviewer_action = "Refresh performance data before approving any new variation."
        elif click_rate is not None and click_rate < 0.02:
            decision = "rebuild_hook"
            reviewer_action = "Review the opening hook and segment promise before more traffic."
        elif conversion_rate is not None and conversion_rate < 0.04:
            decision = "landing_or_offer_review"
            reviewer_action = "Check landing-page match and offer clarity before scaling."
        elif roi is not None and roi > 5:
            decision = "controlled_scale_candidate"
            reviewer_action = "Approve a small controlled scale test after inventory and brand review."

        evidence = f"brief={campaign_id}; asset={asset_id}; freshness={freshness}h; confidence={candidate['model_confidence']}"
        ledger_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "campaign_id": campaign_id,
                "channel": brief["channel"],
                "segment": brief["segment"],
                "click_rate": pct(click_rate),
                "conversion_rate": pct(conversion_rate),
                "roi_after_cost": "n/a" if roi is None else f"{roi:.2f}",
                "decision": decision,
                "next_test": candidate["next_test"],
                "evidence": evidence,
            }
        )
        if decision != "monitor":
            review_rows.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "campaign_id": campaign_id,
                    "reviewer_action": reviewer_action,
                    "approved_claims": asset["approved_claims"],
                    "external_copy_draft": candidate["external_copy"],
                    "evidence": evidence,
                }
            )

    write_csv(
        "campaign-feedback-ledger.csv",
        ledger_rows,
        [
            "candidate_id",
            "campaign_id",
            "channel",
            "segment",
            "click_rate",
            "conversion_rate",
            "roi_after_cost",
            "decision",
            "next_test",
            "evidence",
        ],
    )
    write_csv("review-queue.csv", review_rows, ["candidate_id", "campaign_id", "reviewer_action", "approved_claims", "external_copy_draft", "evidence"])
    write_csv("blocked-output-queue.csv", blocked_rows, ["candidate_id", "campaign_id", "reason", "evidence", "reviewer_action"])
    write_csv("error-log.csv", error_rows, ["candidate_id", "status", "reason", "evidence"])

    brief_lines = [
        "# Campaign feedback loop brief draft",
        "",
        "Generated from mock campaign briefs, approved asset primitives, performance events, and candidate next-test drafts. No client data, no connected ESP, no CRM, and no social posting.",
        "",
        "## Review First",
    ]
    for row in review_rows:
        brief_lines.append(f"- {row['campaign_id']}: {row['reviewer_action']} Evidence: {row['evidence']}.")
    brief_lines.extend(["", "## Blocked Before External Output"])
    for row in blocked_rows:
        brief_lines.append(f"- {row['candidate_id']}: {row['reason']} ({row['evidence']}).")
    brief_lines.extend(
        [
            "",
            "## Boundary",
            "",
            "The agent can draft hypotheses and next-test copy, but deterministic checks own campaign status, approved claims, freshness, and banned-claim blocking before a human approves any external output.",
        ]
    )
    (ROOT / "brief-draft.md").write_text("\n".join(brief_lines) + "\n", encoding="utf-8")

    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
