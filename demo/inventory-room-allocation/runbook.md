# Inventory Room Allocation Demo Runbook

Purpose: prove an Airtable-style inventory workflow can reserve items to project rooms, generate a move queue, and hold bad selections before warehouse or install teams act.

Inputs:

- `inventory-items.csv`: mock item records with quantity, condition, warehouse zone, QR code, and photo folder.
- `project-rooms.csv`: mock project and room records with install windows and active/paused state.
- `selection-requests.csv`: mock item selections for rooms and projects.

Outputs:

- `allocation-ledger.csv`: accepted item-room reservations with QR evidence and room context.
- `move-queue.csv`: approval-required warehouse/install move rows.
- `conflict-queue.csv`: paused projects, unavailable inventory, and repair-hold items.
- `error-log.csv`: malformed selections such as unknown items or rooms.

Acceptance checks:

1. Ready inventory with available quantity becomes a reservation row and a move-queue row.
2. Quantity is decremented so the same item cannot be over-reserved.
3. Repair-hold, zero-quantity, and paused-project rows are blocked before move planning.
4. Unknown inventory or project-room references become hard errors.
5. No live Airtable, Google Drive, QR, email, warehouse, or installer action is used.

Paid implementation boundary:

- Start with one inventory table, one project-room table, and one selection source.
- Keep move instructions approval-required until the team accepts the rules.
- Treat QR scans as evidence/state updates, not as automatic inventory moves, unless the live process is explicitly approved.
