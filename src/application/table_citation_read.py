"""Exact, bounded citation readback; this does not verify the cited source."""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.domain.table_entities import TableContext

MAX_CITATION_BYTES = 16 * 1024 * 1024


def citation_text(context: TableContext, row_index: int, column: str) -> str:
    citation = context.get_citation(row_index, column)
    record = {
        "schema_version": "a2t-cell-citation-v1",
        "table_id": context.id,
        "row_id": context.row_id_for_index(row_index),
        "column_name": column,
        "value": context.rows[row_index].get(column),
        "citation": citation.to_dict() if citation is not None else None,
    }
    encoder = json.JSONEncoder(
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    chunks, size = [], 0
    try:
        for chunk in encoder.iterencode(record):
            size += len(chunk.encode("utf-8"))
            if size > MAX_CITATION_BYTES:
                raise ValueError("Canonical citation exceeds the 16 MiB limit")
            chunks.append(chunk)
    except (TypeError, UnicodeError, RecursionError) as exc:
        raise ValueError("Citation requires finite UTF-8 JSON values") from exc
    return "".join(chunks)


def _validate_page(text_offset: int, text_limit: int, citation_sha256: str) -> None:
    if type(text_offset) is not int or text_offset < 0:
        raise ValueError("text_offset must be a non-negative integer")
    if type(text_limit) is not int or not 1 <= text_limit <= 4000:
        raise ValueError("text_limit must be an integer in 1..4000")
    if citation_sha256 and not re.fullmatch(r"[0-9a-f]{64}", citation_sha256):
        raise ValueError("citation_sha256 must be a lowercase SHA-256 digest")
    if text_offset and not citation_sha256:
        raise ValueError("Continuation requires citation_sha256 from the first page")


def _envelope(text: str, digest: str, start: int, end: int) -> dict[str, Any]:
    return {
        "success": True,
        "schema_version": "a2t-citation-page-v1",
        "citation_sha256": digest,
        "text_excerpt": text[start:end],
        "text_length": len(text),
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "representation_complete": start == 0 and end == len(text),
        "serialization": "sorted compact JSON; UTF-8 SHA-256",
        "integrity_scope": "stored cell snapshot; source and meaning not verified",
    }


def read_citation_page(
    context: TableContext,
    row_index: int,
    column: str,
    *,
    text_offset: int = 0,
    text_limit: int = 4000,
    citation_sha256: str = "",
    max_response_chars: int = 12_000,
) -> dict[str, Any]:
    _validate_page(text_offset, text_limit, citation_sha256)
    text = citation_text(context, row_index, column)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if citation_sha256 and citation_sha256 != digest:
        raise ValueError("Citation changed or cell differs; restart citation read")
    if text_offset > len(text):
        raise ValueError("text_offset is beyond the citation representation")
    end = min(text_offset + text_limit, len(text))
    while True:
        page = _envelope(text, digest, text_offset, end)
        if (
            not max_response_chars
            or len(json.dumps(page, ensure_ascii=False)) <= max_response_chars
        ):
            return page
        if end == text_offset or end == text_offset + 1:
            raise ValueError("MCP response cap is too small for a citation page")
        end = text_offset + (end - text_offset) // 2
