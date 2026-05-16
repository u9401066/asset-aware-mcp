"""Citation evidence helpers shared by document MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from src.application.citation_artifacts import (
    load_citation_status as _load_citation_status,
)
from src.application.citation_index_service import CitationIndexService

if TYPE_CHECKING:
    from src.domain.citation import EvidenceSpan

__all__ = [
    "asset_ref_from_span",
    "coerce_range",
    "display_line_range",
    "format_line_range",
    "load_citation_status",
    "load_or_build_evidence_spans",
]

ASSET_REF_QUOTE_MAX_CHARS = 1_000


def display_line_range(start_line: int, end_line: int) -> str:
    if start_line < 0 or end_line < 0 or end_line < start_line:
        return "L?"
    return f"L{start_line + 1}-{end_line}"


def format_line_range(start_line: int | None, end_line: int | None) -> str | None:
    if (
        start_line is None
        or end_line is None
        or start_line < 0
        or end_line < start_line
    ):
        return None
    return display_line_range(start_line, end_line)


def coerce_range(value: Any) -> list[int | None] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    coerced: list[int | None] = []
    for item in value:
        if item is None:
            coerced.append(None)
        elif isinstance(item, int):
            coerced.append(item)
        else:
            return None
    return coerced


def asset_ref_from_span(span: EvidenceSpan) -> dict[str, Any]:
    quote = span.text
    quote_truncated = len(quote) > ASSET_REF_QUOTE_MAX_CHARS
    ref: dict[str, Any] = {
        "source_type": "span",
        "doc_id": span.doc_id,
        "span_id": span.span_id,
        "block_id": span.block_id,
        "page": span.page,
        "source_revision_id": span.source_revision_id,
        "locator_version": span.locator_version,
        "locator_source_sha256": span.locator_source_sha256,
        "quote": quote[:ASSET_REF_QUOTE_MAX_CHARS],
        "quote_sha256": span.text_sha256,
        "excerpt": span.text[:200],
        "quote_chars": len(quote),
        "quote_truncated": quote_truncated,
        "craap": span.craap.model_dump(exclude_none=True),
    }
    if span.asset_id:
        ref["asset_id"] = span.asset_id
    if span.line_start is not None and span.line_end is not None:
        ref["line_range"] = [span.line_start, span.line_end]
    if span.char_start is not None and span.char_end is not None:
        ref["char_range"] = [span.char_start, span.char_end]
    if span.byte_start is not None and span.byte_end is not None:
        ref["byte_range"] = [span.byte_start, span.byte_end]
    if span.bbox:
        ref["bbox"] = span.bbox
    return ref


def load_or_build_evidence_spans(repository: Any, doc_id: str) -> list[EvidenceSpan]:
    return cast(
        "list[EvidenceSpan]",
        CitationIndexService(repository).load_or_rebuild(doc_id),
    )


def load_citation_status(repository: Any, doc_id: str) -> dict[str, Any] | None:
    return _load_citation_status(repository, doc_id)
