#!/usr/bin/env python3
"""Generate the WorkflowPatch shipping notification demo outputs."""

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


def main() -> int:
    orders = read_csv("orders.csv")
    statuses = {
        (row["carrier"].strip().upper(), row["tracking_number"].strip()): row
        for row in read_csv("carrier-status.csv")
    }
    seen_order_ids: set[str] = set()

    notification_rows: list[dict[str, str]] = []
    alert_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for order in orders:
        order_id = order["order_id"].strip()
        customer_email = order["customer_email"].strip()
        ready = order["ready_flag"].strip().lower() == "yes"
        tracking_number = order["tracking_number"].strip()
        carrier = order["carrier"].strip().upper()

        if not order_id or not customer_email or not tracking_number or not carrier:
            error_rows.append(
                {
                    "order_id": order_id or "missing",
                    "error": "missing required order id, customer email, carrier, or tracking number",
                    "evidence": f"email={customer_email or 'missing'} carrier={carrier or 'missing'} tracking={tracking_number or 'missing'}",
                }
            )
            continue

        if order_id in seen_order_ids:
            error_rows.append(
                {
                    "order_id": order_id,
                    "error": "duplicate order id",
                    "evidence": f"second row attempted tracking={tracking_number} customer_email={customer_email}",
                }
            )
            continue
        seen_order_ids.add(order_id)

        if not ready:
            alert_rows.append(
                {
                    "order_id": order_id,
                    "production_rep": order["production_rep"],
                    "alert_type": "order not ready",
                    "evidence": "ready_flag is not yes",
                    "next_check": "Confirm production status before customer notification.",
                }
            )
            continue

        status = statuses.get((carrier, tracking_number))
        if status is None:
            error_rows.append(
                {
                    "order_id": order_id,
                    "error": "carrier status missing",
                    "evidence": f"carrier={carrier} tracking={tracking_number}",
                }
            )
            continue

        eta = status["eta"].strip()
        carrier_status = status["status"].strip()
        if carrier_status != "in_transit" or not eta:
            alert_rows.append(
                {
                    "order_id": order_id,
                    "production_rep": order["production_rep"],
                    "alert_type": "tracking not live",
                    "evidence": f"carrier_status={carrier_status or 'missing'} eta={eta or 'missing'}",
                    "next_check": "Recheck carrier status in 12 hours before drafting the customer email.",
                }
            )
            continue

        notification_rows.append(
            {
                "order_id": order_id,
                "customer_email": customer_email,
                "draft_subject": f"Shipping update for {order['product_name']}",
                "draft_body": (
                    f"Hi {order['customer_name']}, your {order['product_name']} is in transit "
                    f"with {carrier}. Current ETA is {eta}. Weather note: {status['weather_summary']}."
                ),
                "approval_status": "needs human approval",
                "evidence": f"{carrier} {tracking_number} checked at {status['last_checked_at']}",
            }
        )

    write_csv(
        "notification-queue.csv",
        notification_rows,
        ["order_id", "customer_email", "draft_subject", "draft_body", "approval_status", "evidence"],
    )
    write_csv(
        "ops-alerts.csv",
        alert_rows,
        ["order_id", "production_rep", "alert_type", "evidence", "next_check"],
    )
    write_csv("error-log.csv", error_rows, ["order_id", "error", "evidence"])

    print(f"notification_rows={len(notification_rows)}")
    print(f"alert_rows={len(alert_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
