#!/usr/bin/env python3
"""Generate the WorkflowPatch product content QA ledger proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MIN_IMAGE_DIMENSION = 1500
MIN_IDENTITY_SCORE = 0.88


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fields: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def terms(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(";") if item.strip()]


def find_banned_hit(text: str, banned_terms: str) -> str:
    lower = text.lower()
    for term in terms(banned_terms):
        if term in lower:
            return term
    return ""


def missing_claims(candidate_terms: str, approved_facts: str) -> str:
    approved = set(terms(approved_facts))
    missing = [term for term in terms(candidate_terms) if term not in approved]
    return "; ".join(missing)


def append_ledger(
    ledger_rows: list[dict[str, str]],
    request: dict[str, str],
    product: dict[str, str],
    candidate: dict[str, str],
    decision: str,
    reason: str,
    next_step: str,
) -> None:
    ledger_rows.append(
        {
            "request_id": request["request_id"],
            "product_id": product["product_id"],
            "channel": request["channel"],
            "asset_type": request["asset_type"],
            "identity_score": candidate["clip_similarity"],
            "decision": decision,
            "reason": reason,
            "next_step": next_step,
            "evidence": (
                f"source={request['source_image_ref']}; product_status={product['status']}; "
                f"dimension={candidate['dimension_px']}; metadata={candidate['metadata_preserved']}; "
                f"publish_status={request['requested_status']}"
            ),
        }
    )


def main() -> int:
    products = {row["product_id"]: row for row in read_csv("product-catalog.csv")}
    candidates = {row["request_id"]: row for row in read_csv("candidate-outputs.csv")}

    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    hold_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for request in read_csv("content-requests.csv"):
        product = products.get(request["product_id"])
        candidate = candidates.get(request["request_id"])

        if not product:
            error_rows.append(
                {
                    "request_id": request["request_id"],
                    "status": "error",
                    "reason": "product id missing from source of truth",
                    "evidence": request["product_id"],
                }
            )
            continue
        if not candidate:
            error_rows.append(
                {
                    "request_id": request["request_id"],
                    "status": "error",
                    "reason": "candidate output missing",
                    "evidence": request["request_id"],
                }
            )
            continue
        if candidate["render_status"] != "ready":
            error_rows.append(
                {
                    "request_id": request["request_id"],
                    "status": "error",
                    "reason": "candidate render is not ready",
                    "evidence": candidate["render_status"],
                }
            )
            continue

        if request["requested_status"] == "live_publish_requested":
            reason = "live publish requested before QA handoff"
            hold_rows.append(
                {
                    "request_id": request["request_id"],
                    "product_id": product["product_id"],
                    "publish_target": request["publish_target"],
                    "reason": reason,
                    "reviewer_action": "Keep the asset in draft until product identity, claims, metadata, and channel policy are approved.",
                }
            )
            append_ledger(ledger_rows, request, product, candidate, "publish_hold", reason, "Route to blocked-publish queue.")
            continue

        if product["status"] != "active":
            reason = "product is not active"
            blocked_rows.append(
                {
                    "request_id": request["request_id"],
                    "product_id": product["product_id"],
                    "reason": reason,
                    "evidence": product["status"],
                    "reviewer_action": "Confirm product owner before any media work continues.",
                }
            )
            append_ledger(ledger_rows, request, product, candidate, "blocked", reason, "Confirm product status.")
            continue

        banned_hit = find_banned_hit(candidate["caption_draft"], product["banned_terms"])
        unsupported_claims = missing_claims(candidate["approved_claim_terms"], product["approved_facts"])
        score = float(candidate["clip_similarity"])
        dimension = int(candidate["dimension_px"])
        review_reasons: list[str] = []

        if candidate["product_identity_match"] != "yes":
            review_reasons.append("product identity mismatch")
        if candidate["background_only_change"] != "yes":
            review_reasons.append("candidate changes product, not just scene/background")
        if banned_hit:
            review_reasons.append(f"banned claim detected: {banned_hit}")
        if unsupported_claims:
            review_reasons.append(f"unsupported claim terms: {unsupported_claims}")
        if score < MIN_IDENTITY_SCORE:
            review_reasons.append("identity score below threshold")
        if dimension < MIN_IMAGE_DIMENSION:
            review_reasons.append("image below 1500px target")
        if request["channel"] == "Google Shopping" and candidate["metadata_preserved"] != "yes":
            review_reasons.append("AI metadata missing for Google Shopping candidate")

        if review_reasons:
            reason = "; ".join(review_reasons)
            blocked_rows.append(
                {
                    "request_id": request["request_id"],
                    "product_id": product["product_id"],
                    "reason": reason,
                    "evidence": f"score={score}; dimension={dimension}; metadata={candidate['metadata_preserved']}",
                    "reviewer_action": "Regenerate or repair before any publish-ready state is allowed.",
                }
            )
            append_ledger(ledger_rows, request, product, candidate, "blocked", reason, "Regenerate or route to manual QA.")
            continue

        if candidate["metadata_preserved"] != "yes":
            reason = "AI provenance metadata missing"
            review_rows.append(
                {
                    "request_id": request["request_id"],
                    "product_id": product["product_id"],
                    "reason": reason,
                    "reviewer_action": "Attach generation metadata before channel handoff.",
                    "evidence": f"metadata={candidate['metadata_preserved']}",
                }
            )
            append_ledger(ledger_rows, request, product, candidate, "review", reason, "Attach metadata evidence.")
            continue

        append_ledger(
            ledger_rows,
            request,
            product,
            candidate,
            "accepted_for_review",
            "identity, approved facts, metadata, and requested draft state are intact",
            "Add to asset review packet.",
        )

    write_csv(
        "product-content-qa-ledger.csv",
        ledger_rows,
        [
            "request_id",
            "product_id",
            "channel",
            "asset_type",
            "identity_score",
            "decision",
            "reason",
            "next_step",
            "evidence",
        ],
    )
    write_csv("review-queue.csv", review_rows, ["request_id", "product_id", "reason", "reviewer_action", "evidence"])
    write_csv("blocked-output-queue.csv", blocked_rows, ["request_id", "product_id", "reason", "evidence", "reviewer_action"])
    write_csv("publish-hold-queue.csv", hold_rows, ["request_id", "product_id", "publish_target", "reason", "reviewer_action"])
    write_csv("error-log.csv", error_rows, ["request_id", "status", "reason", "evidence"])

    brief_lines = [
        "# Product content QA ledger brief draft",
        "",
        "Generated from mock product catalog rows, content requests, and candidate media-output metadata. No client product files, paid media APIs, ComfyUI server, Merchant Center account, Buffer/Later scheduler, Shopify admin, or live ad account is connected.",
        "",
        "## Accepted For Review",
    ]
    for row in ledger_rows:
        if row["decision"] == "accepted_for_review":
            brief_lines.append(f"- {row['request_id']} / {row['product_id']}: {row['reason']}. Evidence: {row['evidence']}.")
    brief_lines.extend(["", "## Blocked Or Held Before Publishing"])
    for row in hold_rows:
        brief_lines.append(f"- {row['request_id']} / {row['product_id']}: {row['reason']} for {row['publish_target']}.")
    for row in blocked_rows:
        brief_lines.append(f"- {row['request_id']} / {row['product_id']}: {row['reason']}.")
    brief_lines.extend(["", "## Errors"])
    for row in error_rows:
        brief_lines.append(f"- {row['request_id']}: {row['reason']} ({row['evidence']}).")
    brief_lines.extend(
        [
            "",
            "## Boundary",
            "",
            "The sprint can prove asset lineage, product-integrity checks, blocked-publish routing, and a handoff. It does not promise creative performance, operate paid media APIs, host generation infrastructure, or publish customer-facing assets without a separate scope.",
        ]
    )
    (ROOT / "brief-draft.md").write_text("\n".join(brief_lines) + "\n", encoding="utf-8")

    print(f"ledger_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"publish_hold_rows={len(hold_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
