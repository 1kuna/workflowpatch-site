#!/usr/bin/env python3
"""Generate the WorkflowPatch HTML review queue proof outputs."""

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


def detect_issues(page: dict[str, str]) -> list[dict[str, str]]:
    html = page["html_excerpt"]
    path = page["path"].strip()
    status = page["status"].strip()
    issues: list[dict[str, str]] = []

    if not path:
        issues.append(
            {
                "issue_type": "missing_path",
                "severity": "high",
                "evidence": "path is empty",
                "proposed_fix": "Block the row until the original file path is supplied.",
                "decision": "blocked",
            }
        )
    if "<img" in html and " alt=" not in html:
        issues.append(
            {
                "issue_type": "missing_alt_text",
                "severity": "medium",
                "evidence": "image tag has no alt attribute",
                "proposed_fix": "Add concise descriptive alt text tied to the page topic.",
                "decision": "fix_draft",
            }
        )
    if "meta name='description'" in html and len(html.split("content='", 1)[1].split("'", 1)[0]) < 80:
        issues.append(
            {
                "issue_type": "thin_meta_description",
                "severity": "medium",
                "evidence": "meta description is generic and under 80 characters",
                "proposed_fix": "Draft a page-specific description with the offer, audience, and outcome.",
                "decision": "fix_draft",
            }
        )
    if "href=''" in html or 'href=""' in html:
        issues.append(
            {
                "issue_type": "empty_link",
                "severity": "high",
                "evidence": "link target is empty",
                "proposed_fix": "Block upload until the destination URL is chosen.",
                "decision": "blocked",
            }
        )
    if status == "hold" or "2021" in html:
        issues.append(
            {
                "issue_type": "stale_copy",
                "severity": "medium",
                "evidence": "page is marked hold or contains stale launch copy",
                "proposed_fix": "Route to editorial review before any rewrite or upload.",
                "decision": "needs_review",
            }
        )
    if not issues:
        issues.append(
            {
                "issue_type": "no_blocking_issue",
                "severity": "low",
                "evidence": "required checks passed on the mock excerpt",
                "proposed_fix": "Keep page in the ready queue.",
                "decision": "ready",
            }
        )
    return issues


def main() -> int:
    issue_rows: list[dict[str, str]] = []
    fix_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    run_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for page in read_csv("html-pages.csv"):
        page_id = page["page_id"].strip()
        if not page_id or not page["title"].strip() or not page["html_excerpt"].strip():
            error_rows.append(
                {
                    "page_id": page_id or "missing",
                    "error": "missing page id, title, or HTML excerpt",
                    "evidence": f"title={page['title'] or 'missing'} path={page['path'] or 'missing'}",
                }
            )
            continue

        issues = detect_issues(page)
        run_rows.append(
            {
                "page_id": page_id,
                "path": page["path"] or "missing",
                "issues_found": str(len([issue for issue in issues if issue["issue_type"] != "no_blocking_issue"])),
                "decision": "blocked" if any(issue["decision"] == "blocked" for issue in issues) else "review_or_ready",
            }
        )
        for issue in issues:
            row = {
                "page_id": page_id,
                "path": page["path"] or "missing",
                "title": page["title"],
                "issue_type": issue["issue_type"],
                "severity": issue["severity"],
                "decision": issue["decision"],
                "evidence": issue["evidence"],
                "proposed_fix": issue["proposed_fix"],
            }
            issue_rows.append(row)
            if issue["decision"] == "fix_draft":
                fix_rows.append(row)
            if issue["decision"] in {"blocked", "needs_review"}:
                blocked_rows.append(row)

    write_csv(
        "issue-queue.csv",
        issue_rows,
        ["page_id", "path", "title", "issue_type", "severity", "decision", "evidence", "proposed_fix"],
    )
    write_csv(
        "fix-draft-queue.csv",
        fix_rows,
        ["page_id", "path", "title", "issue_type", "severity", "decision", "evidence", "proposed_fix"],
    )
    write_csv(
        "blocked-review.csv",
        blocked_rows,
        ["page_id", "path", "title", "issue_type", "severity", "decision", "evidence", "proposed_fix"],
    )
    write_csv("run-log.csv", run_rows, ["page_id", "path", "issues_found", "decision"])
    write_csv("error-log.csv", error_rows, ["page_id", "error", "evidence"])

    print(f"issue_rows={len(issue_rows)}")
    print(f"fix_rows={len(fix_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
