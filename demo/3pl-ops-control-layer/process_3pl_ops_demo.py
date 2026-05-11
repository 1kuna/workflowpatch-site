#!/usr/bin/env python3
"""Generate the WorkflowPatch 3PL operations control-layer demo outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-10T23:32:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def exceeds(value: str, threshold: str) -> bool:
    try:
        return float(value) > float(threshold)
    except ValueError:
        return False


def main() -> int:
    events = read_csv("ops-events.csv")
    policies = {row["requested_action"]: row for row in read_csv("control-policy.csv")}
    standards = {row["metric_name"]: row for row in read_csv("standards.csv")}
    seen_correlations: set[str] = set()

    action_rows: list[dict[str, str]] = []
    approval_rows: list[dict[str, str]] = []
    standards_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    def block(event: dict[str, str], reason: str, next_step: str) -> None:
        blocked_rows.append(
            {
                "event_id": event["event_id"],
                "source_system": event["source_system"],
                "work_order_id": event["work_order_id"],
                "requested_action": event["requested_action"],
                "reason": reason,
                "next_step": next_step,
                "processed_at": GENERATED_AT,
            }
        )

    for event in events:
        event_id = event["event_id"]
        if not event["work_order_id"]:
            error_rows.append(
                {
                    "event_id": event_id,
                    "source_system": event["source_system"],
                    "error_code": "missing_work_order_id",
                    "error_detail": "A control-layer event needs a stable work_order_id before routing or action review.",
                }
            )
            continue

        if event["correlation_id"] in seen_correlations:
            block(event, "duplicate_correlation_id", "Attach evidence to the existing review row before any second action.")
            continue
        seen_correlations.add(event["correlation_id"])

        policy = policies.get(event["requested_action"])
        if policy is None:
            error_rows.append(
                {
                    "event_id": event_id,
                    "source_system": event["source_system"],
                    "error_code": "unknown_action_policy",
                    "error_detail": f"No policy exists for {event['requested_action']}.",
                }
            )
            continue

        if policy["policy"] == "blocked":
            block(event, "blocked_by_policy", policy["blocked_reason"])
            continue

        standard_exceeded = False
        for metric_name in ("cycle_minutes", "dwell_minutes", "error_count"):
            standard = standards[metric_name]
            if exceeds(event[metric_name], standard["threshold"]):
                standard_exceeded = True
                standards_rows.append(
                    {
                        "event_id": event_id,
                        "work_order_id": event["work_order_id"],
                        "metric_name": metric_name,
                        "observed_value": event[metric_name],
                        "threshold": standard["threshold"],
                        "unit": standard["unit"],
                        "review_rule": standard["review_rule"],
                        "processed_at": GENERATED_AT,
                    }
                )

        action_id = f"ACT-{event_id.split('-')[-1]}"
        action_rows.append(
            {
                "action_id": action_id,
                "event_id": event_id,
                "source_system": event["source_system"],
                "site_area": event["site_area"],
                "work_order_id": event["work_order_id"],
                "item_id": event["item_id"],
                "quantity": event["quantity"],
                "current_state": event["current_state"],
                "proposed_action": event["requested_action"],
                "target_state": event["target_state"],
                "write_status": "dry_run_only",
                "decision_detail": f"Prepare {event['requested_action']} review from {event['source_system']} signal.",
                "processed_at": GENERATED_AT,
            }
        )

        if policy["human_review_required"] == "yes" or standard_exceeded:
            approval_rows.append(
                {
                    "approval_id": f"APP-{event_id.split('-')[-1]}",
                    "action_id": action_id,
                    "work_order_id": event["work_order_id"],
                    "review_reason": policy["blocked_reason"] or "Operational standard exceeded; supervisor review required.",
                    "review_prompt": f"Review {event['requested_action']} for {event['work_order_id']} before any live system or floor action.",
                    "post_approval_step": "If approved, create an explicit implementation ticket; this demo performs no production write.",
                    "processed_at": GENERATED_AT,
                }
            )

    write_csv(
        "action-ledger.csv",
        action_rows,
        [
            "action_id",
            "event_id",
            "source_system",
            "site_area",
            "work_order_id",
            "item_id",
            "quantity",
            "current_state",
            "proposed_action",
            "target_state",
            "write_status",
            "decision_detail",
            "processed_at",
        ],
    )
    write_csv(
        "approval-queue.csv",
        approval_rows,
        [
            "approval_id",
            "action_id",
            "work_order_id",
            "review_reason",
            "review_prompt",
            "post_approval_step",
            "processed_at",
        ],
    )
    write_csv(
        "standards-review-ledger.csv",
        standards_rows,
        [
            "event_id",
            "work_order_id",
            "metric_name",
            "observed_value",
            "threshold",
            "unit",
            "review_rule",
            "processed_at",
        ],
    )
    write_csv(
        "blocked-action-queue.csv",
        blocked_rows,
        ["event_id", "source_system", "work_order_id", "requested_action", "reason", "next_step", "processed_at"],
    )
    write_csv("error-log.csv", error_rows, ["event_id", "source_system", "error_code", "error_detail"])

    handoff = [
        "# 3PL Ops Control Layer Handoff",
        "",
        f"Generated: {GENERATED_AT}",
        "",
        f"- Source events: {len(events)}",
        f"- Dry-run action rows: {len(action_rows)}",
        f"- Approval rows: {len(approval_rows)}",
        f"- Standards review rows: {len(standards_rows)}",
        f"- Blocked action rows: {len(blocked_rows)}",
        f"- Hard errors: {len(error_rows)}",
        "",
        "This proof treats WMS, ERP, MES, edge scanner, and operator-sheet signals as production-sensitive inputs. It prepares dry-run proposed actions, standards review evidence, approval rows, blocked action rows, and hard errors before any live system, inventory, fulfillment, line-side, or floor-control action.",
    ]
    (ROOT / "handoff.md").write_text("\n".join(handoff) + "\n", encoding="utf-8")

    runbook = [
        "# 3PL Ops Control Layer Runbook",
        "",
        "1. Export a redacted or synthetic event slice from the relevant WMS, ERP, MES, scanner, or operator source.",
        "2. Confirm every event has a work_order_id, action, current state, target state, and correlation id.",
        "3. Run `python3 process_3pl_ops_demo.py`.",
        "4. Review `action-ledger.csv` for dry-run proposed actions.",
        "5. Review `standards-review-ledger.csv` and `approval-queue.csv` before any physical or production-system action.",
        "6. Resolve `blocked-action-queue.csv` and `error-log.csv` before considering live integration.",
        "",
        "Proof boundary: no live WMS, ERP, MES, scanner, inventory, fulfillment, line-side, safety, or floor-control write is performed by this demo.",
    ]
    (ROOT / "runbook.md").write_text("\n".join(runbook) + "\n", encoding="utf-8")

    print(f"source_rows={len(events)}")
    print(f"action_rows={len(action_rows)}")
    print(f"approval_rows={len(approval_rows)}")
    print(f"standards_rows={len(standards_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
