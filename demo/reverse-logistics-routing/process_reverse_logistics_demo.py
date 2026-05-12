#!/usr/bin/env python3
"""Generate the WorkflowPatch reverse logistics routing proof outputs."""

from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-09T12:20:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def money(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal("0")


def boolish(value: str) -> bool:
    return value.strip().lower() == "yes"


def route_for(event: dict[str, str], guardrail: dict[str, str], value: Decimal) -> tuple[str, str]:
    condition = event["condition"].strip().lower()
    event_type = event["event_type"].strip().lower()
    current_channel = event["current_channel"].strip().lower()
    blocked_channels = {item.strip().lower() for item in guardrail["blocked_channels"].split(";") if item.strip()}
    min_resale_value = money(guardrail["min_resale_value"])

    if current_channel in blocked_channels:
        return "blocked", f"current channel {current_channel} is blocked by brand guardrails"
    if condition == "damaged":
        if boolish(guardrail["allow_repair"]):
            return "repair_review", "damaged item can enter repair review before resale decision"
        return "blocked", "damaged item but repair is not approved for this brand"
    if value >= min_resale_value and boolish(guardrail["allow_resale"]):
        return "resale_review", f"value {value} meets resale threshold {min_resale_value}"
    if event_type == "overstock" and boolish(guardrail["allow_liquidation"]):
        return "controlled_liquidation_review", "overstock below resale threshold can enter controlled liquidation review"
    return "blocked", "no approved route for condition, value, and event type"


def main() -> None:
    guardrails = {row["brand"]: row for row in read_csv("brand-guardrails.csv")}
    seen_event_ids: set[str] = set()

    ledger_rows: list[dict[str, str]] = []
    review_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    kpi_rows: list[dict[str, str]] = []
    totals: dict[str, Decimal] = {}

    for event in read_csv("recovery-events.csv"):
        event_id = event["event_id"].strip()
        brand = event["brand"].strip()
        sku = event["sku"].strip()
        value = money(event["estimated_value"])

        if not event_id or not brand or not sku:
            exception_rows.append(
                {
                    "event_id": event_id or "missing",
                    "sku": sku or "missing",
                    "brand": brand or "missing",
                    "reason": "missing required event id, sku, or brand",
                    "next_step": "Repair source row before routing.",
                }
            )
            continue

        if event_id in seen_event_ids:
            exception_rows.append(
                {
                    "event_id": event_id,
                    "sku": sku,
                    "brand": brand,
                    "reason": "duplicate event id",
                    "next_step": "Keep the first event ledger row and review the duplicate source.",
                }
            )
            continue
        seen_event_ids.add(event_id)

        guardrail = guardrails.get(brand)
        if guardrail is None:
            exception_rows.append(
                {
                    "event_id": event_id,
                    "sku": sku,
                    "brand": brand,
                    "reason": "missing brand guardrail",
                    "next_step": "Add brand route policy before any recovery action.",
                }
            )
            continue

        if not event["inventory_status"].strip():
            exception_rows.append(
                {
                    "event_id": event_id,
                    "sku": sku,
                    "brand": brand,
                    "reason": "missing inventory status",
                    "next_step": "Confirm warehouse receipt/status before routing.",
                }
            )
            continue

        route, evidence = route_for(event, guardrail, value)
        if route == "blocked":
            exception_rows.append(
                {
                    "event_id": event_id,
                    "sku": sku,
                    "brand": brand,
                    "reason": evidence,
                    "next_step": "Hold for operations review; do not expose inventory to a channel.",
                }
            )
            continue

        ledger_rows.append(
            {
                "event_id": event_id,
                "sku": sku,
                "brand": brand,
                "route": route,
                "estimated_value": f"{value:.2f}",
                "approval_status": "needs human approval",
                "evidence": evidence,
                "accepted_at": GENERATED_AT,
            }
        )
        review_rows.append(
            {
                "event_id": event_id,
                "sku": sku,
                "brand": brand,
                "recommended_route": route,
                "review_prompt": f"Confirm {route.replace('_', ' ')} for {sku} under {brand} guardrails.",
                "blocked_live_action": "no warehouse, marketplace, pricing, or brand-partner write",
            }
        )
        totals[route] = totals.get(route, Decimal("0")) + value

    for route, total in sorted(totals.items()):
        kpi_rows.append(
            {
                "route": route,
                "events_ready_for_review": str(sum(row["route"] == route for row in ledger_rows)),
                "estimated_value_in_review": f"{total:.2f}",
                "approval_status": "pending human approval",
            }
        )
    kpi_rows.append(
        {
            "route": "exceptions",
            "events_ready_for_review": str(len(exception_rows)),
            "estimated_value_in_review": "0.00",
            "approval_status": "blocked until corrected",
        }
    )

    write_csv(
        "routing-ledger.csv",
        ledger_rows,
        ["event_id", "sku", "brand", "route", "estimated_value", "approval_status", "evidence", "accepted_at"],
    )
    write_csv(
        "route-review-queue.csv",
        review_rows,
        ["event_id", "sku", "brand", "recommended_route", "review_prompt", "blocked_live_action"],
    )
    write_csv("exception-log.csv", exception_rows, ["event_id", "sku", "brand", "reason", "next_step"])
    write_csv(
        "kpi-summary.csv",
        kpi_rows,
        ["route", "events_ready_for_review", "estimated_value_in_review", "approval_status"],
    )

    print(f"recovery_events={len(read_csv('recovery-events.csv'))}")
    print(f"routing_rows={len(ledger_rows)}")
    print(f"review_rows={len(review_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"kpi_rows={len(kpi_rows)}")


if __name__ == "__main__":
    main()
