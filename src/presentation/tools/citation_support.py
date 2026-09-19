"""Citation evidence helpers shared by document MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from src.application.citation_artifacts import (
    load_citation_status as _load_citation_status,
)
from src.application.citation_index_service import CitationIndexService
from src.application.etl_references import (
    asset_ref_from_span as asset_ref_from_span,
)
from src.application.etl_references import (
    coerce_range as coerce_range,
)
from src.application.etl_references import (
    display_line_range as display_line_range,
)
from src.application.etl_references import (
    format_line_range as format_line_range,
)

if TYPE_CHECKING:
    from src.domain.citation import EvidenceSpan

__all__ = [
    "asset_ref_for_mcp_response",
    "asset_ref_from_span",
    "asset_ref_preview_from_span",
    "coerce_range",
    "display_line_range",
    "format_line_range",
    "load_citation_status",
    "load_or_build_evidence_spans",
]

MCP_CANONICAL_QUOTE_MAX_CHARS = 1_000
MCP_QUOTE_PREVIEW_CHARS = 500


def asset_ref_preview_from_span(span: EvidenceSpan) -> dict[str, Any]:
    """Build an explicitly non-canonical transport preview for a large span.

    The preview deliberately omits the canonical locator fields and uses a
    distinct source type. It therefore cannot be mistaken for, or submitted as,
    a complete self-verifying ``AssetRef``.
    """
    quote_preview = span.text[:MCP_QUOTE_PREVIEW_CHARS]
    return {
        "preview_version": "asset-ref-preview-v1",
        "canonical_asset_ref": False,
        "source_type": "span_preview",
        "doc_id": span.doc_id,
        "span_id": span.span_id,
        "block_id": span.block_id,
        "page": span.page,
        "quote_preview": quote_preview,
        "quote_preview_chars": len(quote_preview),
        "quote_chars": len(span.text),
        "quote_sha256": span.text_sha256,
        "quote_omitted_chars": len(span.text) - len(quote_preview),
        "canonical_ref_available_in": (
            "persisted citation/agent-asset bundles; export or write the bundle "
            "to retrieve the complete self-verifying AssetRef"
        ),
    }


def asset_ref_for_mcp_response(span: EvidenceSpan) -> dict[str, Any]:
    """Return a canonical small ref or a safe non-canonical large preview."""
    if len(span.text) <= MCP_CANONICAL_QUOTE_MAX_CHARS:
        return asset_ref_from_span(span)
    return asset_ref_preview_from_span(span)


def load_or_build_evidence_spans(repository: Any, doc_id: str) -> list[EvidenceSpan]:
    return cast(
        "list[EvidenceSpan]",
        CitationIndexService(repository).load_or_rebuild(doc_id),
    )


def load_citation_status(repository: Any, doc_id: str) -> dict[str, Any] | None:
    return _load_citation_status(repository, doc_id)
