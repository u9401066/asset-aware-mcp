"""
Infrastructure Layer - PDF Extractor Factory

Selects PDF extraction engines from configuration (``settings.etl_engine``).

Two slots:

- **Base extractor** (:class:`PDFExtractorInterface`): always available, used
  for text/image extraction and as the fast fallback. ``pymupdf`` (default) or
  ``pymupdf4llm`` (layout-aware, self-degrading).
- **Structured extractor** (:class:`StructuredPDFExtractor` | ``None``):
  high-fidelity engine with ``parse() -> MarkerParseResult``, injected into the
  document service's ``marker_extractor`` slot. ``docling``, ``mineru``, or
  ``marker`` (legacy). ``None`` when the selected engine is base-only or its
  optional backend is not installed (graceful degradation to PyMuPDF).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.marker_errors import (
    MARKER_INSTALL_HINT,
    MINERU_INSTALL_HINT,
    MarkerBackendUnavailable,
)
from src.infrastructure.pdf_extractor import PyMuPDFExtractor

if TYPE_CHECKING:
    from src.domain.etl_profile import ETLProfile
    from src.domain.repositories import PDFExtractorInterface
    from src.infrastructure.structured_extractor import StructuredPDFExtractor

logger = logging.getLogger(__name__)

BASE_ENGINES = frozenset({"pymupdf", "pymupdf4llm"})
ACTIVE_STRUCTURED_ENGINES = frozenset({"docling"})
HELD_STRUCTURED_ENGINES = frozenset({"mineru", "marker"})
STRUCTURED_ENGINES = ACTIVE_STRUCTURED_ENGINES | HELD_STRUCTURED_ENGINES


def held_structured_backend_error(engine: str) -> MarkerBackendUnavailable:
    """Return the canonical fail-closed error for a held production backend."""
    if engine == "mineru":
        return MarkerBackendUnavailable(MINERU_INSTALL_HINT)
    return MarkerBackendUnavailable(MARKER_INSTALL_HINT)


def build_base_extractor(
    engine: str | None,
    profile: ETLProfile,
) -> PDFExtractorInterface:
    """Build the always-available base extractor for the selected engine.

    ``pymupdf4llm`` self-degrades to PyMuPDF text extraction when the optional
    backend is missing, so it is safe to return unconditionally.
    """
    normalized = (engine or "pymupdf").lower()
    if normalized == "pymupdf4llm":
        from src.infrastructure.pymupdf4llm_adapter import PyMuPDF4LLMExtractor

        logger.info("Base PDF engine: pymupdf4llm (layout-aware)")
        return PyMuPDF4LLMExtractor(profile=profile)

    if normalized not in BASE_ENGINES and normalized not in STRUCTURED_ENGINES:
        logger.warning(
            "Unknown ETL_ENGINE=%r; falling back to pymupdf base extractor",
            engine,
        )
    return PyMuPDFExtractor(profile=profile)


def build_structured_extractor(engine: str | None) -> StructuredPDFExtractor | None:
    """Build the optional high-fidelity structured extractor, or ``None``.

    Returns ``None`` when the engine is base-only (``pymupdf``/``pymupdf4llm``)
    or the active Docling backend is unavailable. Marker and MinerU adapters are
    retained for isolated upstream evaluation only: production composition
    rejects them before importing or probing locally installed packages.
    """
    normalized = (engine or "").lower()

    if normalized in HELD_STRUCTURED_ENGINES:
        raise held_structured_backend_error(normalized)

    if normalized == "docling":
        from src.infrastructure.docling_adapter import DoclingExtractor

        return _preflight_or_none(DoclingExtractor(), "docling")

    return None


def _preflight_or_none(
    extractor: StructuredPDFExtractor,
    name: str,
) -> StructuredPDFExtractor | None:
    """Return the extractor if its backend is importable, else ``None``."""
    try:
        extractor.require_backend_available()
    except Exception as exc:
        logger.info(
            "Structured engine %r unavailable (%s); degrading to PyMuPDF",
            name,
            exc,
        )
        return None
    logger.info("Structured PDF engine: %s", name)
    return extractor
