#!/usr/bin/env python3
"""Generate the WorkflowPatch SMS approval state proof outputs."""

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


def draft_message(caregiver_name: str, activity_title: str, prompt: str) -> str:
    return (
        f"Hi {caregiver_name}, here is a gentle option for today: {activity_title}. "
        f"{prompt} Reply STOP if you do not want more messages."
    )


def main() -> int:
    users = {row["phone_token"]: row for row in read_csv("users.csv")}
    activities = {row["activity_id"]: row for row in read_csv("activity-catalog.csv")}
    decisions = {row["approval_id"]: row for row in read_csv("slack-decisions.csv")}

    state_rows: list[dict[str, str]] = []
    approval_rows: list[dict[str, str]] = []
    outbound_rows: list[dict[str, str]] = []
    analytics_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for inbound in read_csv("inbound-messages.csv"):
        message_id = inbound["message_id"]
        phone_token = inbound["phone_token"]
        user = users.get(phone_token)

        if user is None:
            error_rows.append(
                {
                    "message_id": message_id,
                    "status": "blocked",
                    "reason": "unknown phone token",
                    "evidence": f"phone_token={phone_token}",
                }
            )
            continue

        if user["consent_status"] != "opted_in":
            error_rows.append(
                {
                    "message_id": message_id,
                    "status": "blocked",
                    "reason": "user is not opted in",
                    "evidence": f"user_id={user['user_id']} consent_status={user['consent_status']}",
                }
            )
            continue

        if user["state"] == "paused":
            error_rows.append(
                {
                    "message_id": message_id,
                    "status": "blocked",
                    "reason": "conversation is paused",
                    "evidence": f"user_id={user['user_id']} state=paused",
                }
            )
            continue

        if user["state"] == "pending_approval":
            error_rows.append(
                {
                    "message_id": message_id,
                    "status": "blocked",
                    "reason": "existing draft already awaits review",
                    "evidence": f"user_id={user['user_id']} state=pending_approval",
                }
            )
            continue

        activity = activities.get(user["last_activity_id"])
        if activity is None:
            error_rows.append(
                {
                    "message_id": message_id,
                    "status": "error",
                    "reason": "missing activity mapping",
                    "evidence": f"user_id={user['user_id']} last_activity_id={user['last_activity_id']}",
                }
            )
            continue

        approval_id = f"ap_{message_id}"
        draft = draft_message(user["caregiver_name"], activity["title"], activity["draft_prompt"])
        decision = decisions.get(approval_id, {"decision": "pending", "reviewer": "", "notes": "Awaiting review."})
        next_state = "awaiting_review"
        reviewer_action = "Review draft in Slack before any outbound SMS."

        if decision["decision"] == "approved":
            next_state = "outbound_queued"
            reviewer_action = "Approved. Queue for Twilio send after final opt-in check."
            outbound_rows.append(
                {
                    "message_id": message_id,
                    "user_id": user["user_id"],
                    "phone_token": phone_token,
                    "send_status": "approved_not_sent",
                    "approved_text": draft,
                    "evidence": f"approval_id={approval_id} reviewer={decision['reviewer']}",
                }
            )
            analytics_rows.append(
                {
                    "event_id": f"ev_{message_id}_outbound",
                    "user_id": user["user_id"],
                    "event_type": "outbound_queued",
                    "evidence": f"approval_id={approval_id} decision=approved",
                }
            )
        elif decision["decision"] == "revise":
            next_state = "needs_revision"
            reviewer_action = f"Revise before send: {decision['notes']}"

        approval_rows.append(
            {
                "approval_id": approval_id,
                "user_id": user["user_id"],
                "message_id": message_id,
                "activity_id": activity["activity_id"],
                "draft_text": draft,
                "review_status": decision["decision"],
                "reviewer_action": reviewer_action,
            }
        )
        state_rows.append(
            {
                "user_id": user["user_id"],
                "prior_state": user["state"],
                "next_state": next_state,
                "message_id": message_id,
                "evidence": f"activity_id={activity['activity_id']} approval_id={approval_id}",
            }
        )
        analytics_rows.append(
            {
                "event_id": f"ev_{message_id}_draft",
                "user_id": user["user_id"],
                "event_type": "draft_created",
                "evidence": f"message_id={message_id} activity_id={activity['activity_id']}",
            }
        )

    write_csv(
        "conversation-state.csv",
        state_rows,
        ["user_id", "prior_state", "next_state", "message_id", "evidence"],
    )
    write_csv(
        "slack-approval-queue.csv",
        approval_rows,
        ["approval_id", "user_id", "message_id", "activity_id", "draft_text", "review_status", "reviewer_action"],
    )
    write_csv(
        "outbound-queue.csv",
        outbound_rows,
        ["message_id", "user_id", "phone_token", "send_status", "approved_text", "evidence"],
    )
    write_csv(
        "analytics-events.csv",
        analytics_rows,
        ["event_id", "user_id", "event_type", "evidence"],
    )
    write_csv("error-log.csv", error_rows, ["message_id", "status", "reason", "evidence"])

    print(f"state_rows={len(state_rows)}")
    print(f"approval_rows={len(approval_rows)}")
    print(f"outbound_rows={len(outbound_rows)}")
    print(f"analytics_rows={len(analytics_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
