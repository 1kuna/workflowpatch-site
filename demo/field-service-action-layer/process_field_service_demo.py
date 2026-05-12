#!/usr/bin/env python3
"""Generate the WorkflowPatch field-service action-layer proof outputs."""

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


def main() -> int:
    customers_by_phone = {row["phone"].strip(): row for row in read_csv("customers.csv")}
    work_orders_by_customer = {row["customer_id"].strip(): row for row in read_csv("work-orders.csv")}
    action_policy = {row["requested_action"].strip(): row for row in read_csv("action-policy.csv")}

    action_rows: list[dict[str, str]] = []
    approval_rows: list[dict[str, str]] = []
    blocked_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []
    seen_request_keys: set[tuple[str, str, str]] = set()

    for request in read_csv("voiceflow-requests.csv"):
        request_id = request["request_id"].strip()
        phone = request["customer_phone"].strip()
        requested_action = request["requested_action"].strip()
        requested_time = request["requested_time"].strip()

        if not request_id or not phone or not requested_action:
            error_rows.append(
                {
                    "request_id": request_id or "missing",
                    "status": "error",
                    "reason": "missing request id, phone, or requested action",
                    "evidence": f"phone={phone or 'missing'} requested_action={requested_action or 'missing'}",
                }
            )
            continue

        request_key = (phone, requested_action, requested_time)
        if request_key in seen_request_keys:
            blocked_rows.append(
                {
                    "request_id": request_id,
                    "status": "blocked",
                    "reason": "duplicate action request",
                    "evidence": f"phone={phone} action={requested_action} requested_time={requested_time or 'none'}",
                    "next_step": "Do not create a second work-order update. Attach to the existing review item.",
                }
            )
            continue
        seen_request_keys.add(request_key)

        policy = action_policy.get(requested_action)
        if policy is None:
            blocked_rows.append(
                {
                    "request_id": request_id,
                    "status": "blocked",
                    "reason": "unknown action type",
                    "evidence": f"requested_action={requested_action}",
                    "next_step": "Map the requested action before allowing any downstream write.",
                }
            )
            continue

        if policy["policy"] != "allowed":
            blocked_rows.append(
                {
                    "request_id": request_id,
                    "status": "blocked",
                    "reason": "action type not allowed for automation",
                    "evidence": f"requested_action={requested_action} policy={policy['policy']}",
                    "next_step": "Route to a human. Do not modify pricing, refunds, or contract terms automatically.",
                }
            )
            continue

        customer = customers_by_phone.get(phone)
        if customer is None:
            blocked_rows.append(
                {
                    "request_id": request_id,
                    "status": "blocked",
                    "reason": "unknown customer phone",
                    "evidence": f"phone={phone}",
                    "next_step": "Verify identity or create a new-customer intake record before scheduling.",
                }
            )
            continue

        work_order = work_orders_by_customer.get(customer["customer_id"])
        if work_order is None:
            blocked_rows.append(
                {
                    "request_id": request_id,
                    "status": "blocked",
                    "reason": "no open work order found",
                    "evidence": f"customer_id={customer['customer_id']}",
                    "next_step": "Create or select the work order before taking action.",
                }
            )
            continue

        if customer["account_status"] != "active":
            blocked_rows.append(
                {
                    "request_id": request_id,
                    "status": "blocked",
                    "reason": "customer account is on hold",
                    "evidence": f"customer_id={customer['customer_id']} status={customer['account_status']} open_balance={work_order['open_balance']}",
                    "next_step": "Resolve account hold before scheduling or rescheduling service.",
                }
            )
            continue

        if requested_action in {"schedule", "reschedule"} and not requested_time:
            error_rows.append(
                {
                    "request_id": request_id,
                    "status": "error",
                    "reason": "schedule action missing requested time",
                    "evidence": f"customer_id={customer['customer_id']} work_order_id={work_order['work_order_id']}",
                }
            )
            continue

        action_id = f"ACT-{request_id.split('-')[-1]}"
        action_rows.append(
            {
                "action_id": action_id,
                "request_id": request_id,
                "customer_id": customer["customer_id"],
                "work_order_id": work_order["work_order_id"],
                "jobtread_job_id": work_order["jobtread_job_id"],
                "dry_run_action": f"{requested_action} {work_order['service_type']}",
                "proposed_value": requested_time or "cancel requested",
                "write_status": "dry_run_only",
                "evidence": f"phone_match=true policy=allowed current_status={work_order['current_status']}",
            }
        )
        approval_rows.append(
            {
                "approval_id": f"APP-{request_id.split('-')[-1]}",
                "action_id": action_id,
                "reviewer": work_order["technician"],
                "approval_status": "needs human approval",
                "review_prompt": (
                    f"Approve {requested_action} for {customer['customer_name']} "
                    f"on {work_order['work_order_id']}?"
                ),
                "post_approval_step": "Write to JobTread only after reviewer approval.",
            }
        )

    write_csv(
        "action-ledger.csv",
        action_rows,
        [
            "action_id",
            "request_id",
            "customer_id",
            "work_order_id",
            "jobtread_job_id",
            "dry_run_action",
            "proposed_value",
            "write_status",
            "evidence",
        ],
    )
    write_csv(
        "approval-queue.csv",
        approval_rows,
        ["approval_id", "action_id", "reviewer", "approval_status", "review_prompt", "post_approval_step"],
    )
    write_csv("blocked-actions.csv", blocked_rows, ["request_id", "status", "reason", "evidence", "next_step"])
    write_csv("error-log.csv", error_rows, ["request_id", "status", "reason", "evidence"])

    print(f"action_rows={len(action_rows)}")
    print(f"approval_rows={len(approval_rows)}")
    print(f"blocked_rows={len(blocked_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
