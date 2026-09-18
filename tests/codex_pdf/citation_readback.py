"""Audit complete canonical references actually delivered to the live agent."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from tests.codex_pdf.trace import require, result_text


def _final_reads(calls: list[dict], table_id: str) -> list[dict]:
    last_change = -1
    for index, call in enumerate(calls):
        args = call["arguments"]
        if args.get("table_id") != table_id:
            continue
        if (
            call["tool"] == "table_data"
            and args.get("operation")
            in {
                "add_rows",
                "update_cell",
                "update_row",
                "clear_cell",
                "delete_row",
            }
        ) or (
            call["tool"] == "table_cite" and args.get("operation") in {"add", "remove"}
        ):
            last_change = index
    return [
        call
        for call in calls[last_change + 1 :]
        if call["tool"] == "table_cite"
        and call["arguments"].get("operation") == "read"
        and call["arguments"].get("table_id") == table_id
    ]


def _collect_pages(calls: list[dict]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for call in calls:
        page = json.loads(result_text(call))
        require(
            page.get("schema_version") == "a2t-citation-page-v1",
            "Not a canonical citation page",
        )
        start, end = page["excerpt_char_range"]
        text, size, digest = (
            page["text_excerpt"],
            page["text_length"],
            page["citation_sha256"],
        )
        require(
            0 <= start < end <= size and end - start == len(text),
            "Invalid citation page range",
        )
        require(
            page["next_text_offset"] == (end if end < size else None),
            "Invalid citation continuation",
        )
        require(
            page["representation_complete"] == (start == 0 and end == size),
            "False citation completeness",
        )
        args = call["arguments"]
        require(
            start == args.get("text_offset", 0), "Citation request/page range mismatch"
        )
        if start or args.get("citation_sha256"):
            require(
                args.get("citation_sha256") == digest,
                "Citation continuation lost hash pin",
            )
        group = groups.setdefault(digest, {"size": size, "pages": {}, "requests": []})
        require(group["size"] == size, "Mixed citation lengths")
        previous = group["pages"].setdefault(start, text)
        require(previous == text, "Conflicting citation page retry")
        group["requests"].append(args)
    return groups


def _assemble(digest: str, group: dict[str, Any]) -> dict[str, Any]:
    offset, chunks = 0, []
    for start, text in sorted(group["pages"].items()):
        require(start == offset, "Missing or overlapping citation pages")
        offset += len(text)
        chunks.append(text)
    text = "".join(chunks)
    require(offset == group["size"], "Incomplete canonical citation readback")
    require(
        hashlib.sha256(text.encode("utf-8")).hexdigest() == digest,
        "Citation readback hash mismatch",
    )
    record = json.loads(text)
    for args in group["requests"]:
        require(
            args.get("column_name") == record["column_name"], "Citation column mismatch"
        )
        if args.get("row_id"):
            require(
                args["row_id"] == record["row_id"], "Citation row identity mismatch"
            )
    return record


def validate_citation_readbacks(
    table: dict, calls: list[dict], *, require_paging: bool = False
) -> None:
    expected = {
        row_id: {
            "schema_version": "a2t-cell-citation-v1",
            "table_id": table["id"],
            "row_id": row_id,
            "column_name": "Reading",
            "value": row["Reading"],
            "citation": table["citations"].get(f"rid:{row_id}:Reading"),
        }
        for row, row_id in zip(table["rows"], table["row_ids"], strict=True)
    }
    groups = _collect_pages(_final_reads(calls, table["id"]))
    seen = set()
    for digest, group in groups.items():
        record = _assemble(digest, group)
        row_id = record.get("row_id")
        require(
            record == expected.get(row_id),
            "Readback differs from final persisted citation/value",
        )
        for args in group["requests"]:
            if not args.get("row_id"):
                require(
                    args.get("row_index") == table["row_ids"].index(row_id),
                    "Citation row index mismatch",
                )
        seen.add(row_id)
    require(seen == set(expected), "Missing final canonical citation readbacks")
    if require_paging:
        require(
            any(len(group["pages"]) > 1 for group in groups.values()),
            "No actual hash-pinned citation continuation was exercised",
        )
