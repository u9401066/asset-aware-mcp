"""
Infrastructure Layer - Structured PDF Extractor Protocol

Marker, Docling, and MinerU are all high-fidelity structured parsers that
produce a :class:`MarkerParseResult` and share the same public surface. The
document service depends on this Protocol instead of a concrete class, so the
``marker_extractor`` slot is engine-agnostic and any of the three can be
injected interchangeably.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path

    from src.infrastructure.marker_adapter import MarkerParseResult


@runtime_checkable
class StructuredPDFExtractor(Protocol):
    """High-fidelity parser producing MarkerParseResult-compatible output."""

    def require_backend_available(self) -> None:
        """Raise a backend-unavailable error if the engine cannot run."""
        ...

    def parse(
        self,
        pdf_path: Path,
        *,
        extract_images: bool = ...,
        max_pages_per_chunk: int | None = ...,
        page_map: list[int] | None = ...,
        reported_page_count: int | None = ...,
    ) -> MarkerParseResult:
        """Parse a PDF into a structured MarkerParseResult."""
        ...


# Prefixes carried by IngestResult.backend / DocumentManifest.source_engine
# whenever a structured engine (rather than the fast PyMuPDF/PyMuPDF4LLM path)
# produced a document. MinerU appends its sub-backend (e.g. "mineru:pipeline"),
# hence a prefix check rather than an exact-match set.
STRUCTURED_ENGINE_PREFIXES: tuple[str, ...] = ("marker", "docling", "mineru")


def is_structured_engine(engine_name: str) -> bool:
    """True when ``engine_name`` came from a StructuredPDFExtractor.

    Use this instead of ``== "marker"`` so Docling/MinerU results are treated
    the same as Marker's for "was a high-fidelity engine used" checks (e.g.
    ``require_marker`` enforcement, "blocks.json has real bbox" reporting).
    """
    return engine_name.startswith(STRUCTURED_ENGINE_PREFIXES)
