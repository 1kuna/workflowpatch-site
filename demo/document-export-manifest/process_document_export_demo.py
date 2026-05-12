#!/usr/bin/env python3
"""Generate the WorkflowPatch document export manifest proof outputs."""

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
    targets = {
        (row["source_object_type"], row["source_object_id"]): row
        for row in read_csv("destination-records.csv")
    }
    seen_document_keys: set[tuple[str, str, str]] = set()
    manifest_rows: list[dict[str, str]] = []
    exception_rows: list[dict[str, str]] = []
    error_rows: list[dict[str, str]] = []

    for row in read_csv("source-documents.csv"):
        doc_id = row["doc_id"].strip()
        object_type = row["source_object_type"].strip()
        object_id = row["source_object_id"].strip()
        file_name = row["file_name"].strip()
        document_key = (object_type, object_id, file_name.lower())

        if not doc_id or not object_type or not object_id or not file_name:
            error_rows.append(
                {
                    "doc_id": doc_id or "missing",
                    "status": "error",
                    "reason": "missing document id, source object, or file name",
                    "evidence": f"source_object_type={object_type or 'missing'} source_object_id={object_id or 'missing'}",
                }
            )
            continue

        if document_key in seen_document_keys:
            exception_rows.append(
                {
                    "doc_id": doc_id,
                    "status": "blocked",
                    "reason": "duplicate document association",
                    "evidence": f"source_object={object_type}:{object_id} file_name={file_name}",
                    "reviewer_action": "Confirm whether this is a true duplicate before moving.",
                }
            )
            continue
        seen_document_keys.add(document_key)

        target = targets.get((object_type, object_id))
        if target is None:
            exception_rows.append(
                {
                    "doc_id": doc_id,
                    "status": "blocked",
                    "reason": "no destination record match",
                    "evidence": f"source_object={object_type}:{object_id}",
                    "reviewer_action": "Map or create destination record before transfer.",
                }
            )
            continue

        if row["download_status"] != "downloadable":
            exception_rows.append(
                {
                    "doc_id": doc_id,
                    "status": "blocked",
                    "reason": "source file is not downloadable",
                    "evidence": f"download_status={row['download_status']} visibility={row['visibility']}",
                    "reviewer_action": "Export manually or refresh source permissions before replay.",
                }
            )
            continue

        if target["file_import_supported"] != "true":
            exception_rows.append(
                {
                    "doc_id": doc_id,
                    "status": "export_only",
                    "reason": "destination file attachment not verified",
                    "evidence": f"nutshell_entity_id={target['nutshell_entity_id']} file_import_supported=false",
                    "reviewer_action": "Deliver file plus manifest unless destination import path is confirmed.",
                }
            )
            continue

        manifest_rows.append(
            {
                "doc_id": doc_id,
                "file_name": file_name,
                "source_object": f"{object_type}:{object_id}",
                "destination_entity": target["nutshell_entity_id"],
                "transfer_status": "ready_for_test_transfer",
                "manifest_evidence": (
                    f"association_name={row['association_name']} "
                    f"file_type={row['file_type']} size_mb={row['size_mb']}"
                ),
            }
        )

    write_csv(
        "transfer-manifest.csv",
        manifest_rows,
        ["doc_id", "file_name", "source_object", "destination_entity", "transfer_status", "manifest_evidence"],
    )
    write_csv(
        "exception-report.csv",
        exception_rows,
        ["doc_id", "status", "reason", "evidence", "reviewer_action"],
    )
    write_csv("error-log.csv", error_rows, ["doc_id", "status", "reason", "evidence"])

    print(f"manifest_rows={len(manifest_rows)}")
    print(f"exception_rows={len(exception_rows)}")
    print(f"error_rows={len(error_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
