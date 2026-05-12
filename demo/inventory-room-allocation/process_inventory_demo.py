#!/usr/bin/env python3
"""Generate the WorkflowPatch inventory/room allocation proof outputs."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GENERATED_AT = "2026-05-09T10:20:00Z"


def read_csv(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(name: str, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    items = {row["item_id"]: row for row in read_csv("inventory-items.csv")}
    rooms = {(row["project_id"], row["room_id"]): row for row in read_csv("project-rooms.csv")}
    remaining = {item_id: int(row["available_quantity"]) for item_id, row in items.items()}

    allocation_rows: list[dict[str, str]] = []
    move_rows: list[dict[str, str]] = []
    conflict_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for request in read_csv("selection-requests.csv"):
        request_id = request["request_id"]
        item = items.get(request["item_id"])
        room = rooms.get((request["project_id"], request["room_id"]))
        quantity = int(request["quantity"])

        if item is None:
            error_rows.append(
                {
                    "request_id": request_id,
                    "error_code": "unknown_item",
                    "error_detail": f"Item {request['item_id']} is not in the inventory table.",
                }
            )
            continue

        if room is None:
            error_rows.append(
                {
                    "request_id": request_id,
                    "error_code": "unknown_room",
                    "error_detail": f"Room {request['project_id']} / {request['room_id']} is not in the project-room table.",
                }
            )
            continue

        if room["status"] != "active":
            conflict_rows.append(
                {
                    "request_id": request_id,
                    "project_id": request["project_id"],
                    "room_id": request["room_id"],
                    "item_id": request["item_id"],
                    "reason": "project_not_active",
                    "next_step": "Review project status before reserving or moving inventory.",
                }
            )
            continue

        if item["condition_status"] != "ready":
            conflict_rows.append(
                {
                    "request_id": request_id,
                    "project_id": request["project_id"],
                    "room_id": request["room_id"],
                    "item_id": request["item_id"],
                    "reason": "item_not_ready",
                    "next_step": "Repair or replace item before install planning.",
                }
            )
            continue

        if remaining[item["item_id"]] < quantity:
            conflict_rows.append(
                {
                    "request_id": request_id,
                    "project_id": request["project_id"],
                    "room_id": request["room_id"],
                    "item_id": request["item_id"],
                    "reason": "insufficient_available_quantity",
                    "next_step": "Pick alternate inventory or approve a purchase/rental substitution.",
                }
            )
            continue

        remaining[item["item_id"]] -= quantity
        allocation_rows.append(
            {
                "request_id": request_id,
                "project_id": request["project_id"],
                "project_name": room["project_name"],
                "room_id": request["room_id"],
                "room_name": room["room_name"],
                "item_id": request["item_id"],
                "item_name": item["item_name"],
                "quantity": str(quantity),
                "state": "reserved_for_install",
                "qr_code": item["qr_code"],
                "accepted_at": GENERATED_AT,
            }
        )
        move_rows.append(
            {
                "request_id": request_id,
                "item_id": request["item_id"],
                "from_zone": item["warehouse_zone"],
                "to_project": request["project_id"],
                "to_room": request["room_id"],
                "install_window": room["install_window"],
                "approval": "required",
            }
        )

    write_csv(
        "allocation-ledger.csv",
        allocation_rows,
        [
            "request_id",
            "project_id",
            "project_name",
            "room_id",
            "room_name",
            "item_id",
            "item_name",
            "quantity",
            "state",
            "qr_code",
            "accepted_at",
        ],
    )
    write_csv(
        "move-queue.csv",
        move_rows,
        ["request_id", "item_id", "from_zone", "to_project", "to_room", "install_window", "approval"],
    )
    write_csv(
        "conflict-queue.csv",
        conflict_rows,
        ["request_id", "project_id", "room_id", "item_id", "reason", "next_step"],
    )
    write_csv("error-log.csv", error_rows, ["request_id", "error_code", "error_detail"])

    print(f"selection_rows={len(read_csv('selection-requests.csv'))}")
    print(f"allocation_rows={len(allocation_rows)}")
    print(f"move_rows={len(move_rows)}")
    print(f"conflict_rows={len(conflict_rows)}")
    print(f"error_rows={len(error_rows)}")


if __name__ == "__main__":
    main()
