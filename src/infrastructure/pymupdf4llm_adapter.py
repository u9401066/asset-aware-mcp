"""
Infrastructure Layer - PyMuPDF4LLM Adapter

Layout-aware drop-in upgrade of :class:`PyMuPDFExtractor`.

``pymupdf4llm`` reconstructs multi-column reading order and converts tables to
GitHub-flavoured Markdown while staying entirely inside the PyMuPDF/MuPDF C
ecosystem: no GPU, no model download, and no Pillow conflict (unlike marker-pdf
which pins ``Pillow<11``).

This adapter overrides only text extraction. It inherits PyMuPDF's proven
multi-strategy image extraction, page counting, and ETL-profile heuristics, so
it is a safe ``pdf_extractor`` slot replacement that degrades gracefully back to
the parent implementation whenever the optional backend is missing or errors.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.infrastructure.pdf_extractor import PyMuPDFExtractor

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

PYMUPDF4LLM_INSTALL_HINT = (
    "PyMuPDF4LLM backend not installed. Install the optional extra via "
    "`uv tool install --upgrade 'asset-aware-mcp[pdf-plus]'` "
    "(or `uv pip install pymupdf4llm`), or set ETL_ENGINE=pymupdf."
)


class PyMuPDF4LLMBackendUnavailable(RuntimeError):
    """Raised when the optional ``pymupdf4llm`` backend cannot be imported."""


class PyMuPDF4LLMExtractor(PyMuPDFExtractor):
    """Layout-aware text extraction via pymupdf4llm; images via PyMuPDF.

    The class deliberately subclasses :class:`PyMuPDFExtractor` so that
    ``extract_images`` (multi-strategy, subprocess-timeout protected) and
    ``get_page_count`` are reused verbatim. Only ``extract_text`` is upgraded to
    the layout-aware Markdown reconstruction.
    """

    ENGINE_NAME: str = "pymupdf4llm"

    @staticmethod
    def require_backend_available() -> None:
        """Preflight the pymupdf4llm import without processing a document."""
        try:
            import pymupdf4llm  # type: ignore # noqa: F401
        except ImportError as exc:
            raise PyMuPDF4LLMBackendUnavailable(PYMUPDF4LLM_INSTALL_HINT) from exc

    def extract_text(self, pdf_path: Path) -> str:
        """Extract layout-aware Markdown with per-page ``<!-- Page N -->`` markers.

        Falls back to the inherited PyMuPDF text extraction if ``pymupdf4llm`` is
        unavailable or errors out, preserving the page-marker convention the
        downstream segmentation/manifest pipeline relies on.
        """
        try:
            import pymupdf4llm  # type: ignore
        except ImportError:
            logger.warning(
                "pymupdf4llm not installed; falling back to PyMuPDF text extraction"
            )
            return super().extract_text(pdf_path)

        try:
            chunks = pymupdf4llm.to_markdown(
                str(pdf_path),
                page_chunks=True,
                show_progress=False,
            )
        except Exception:
            logger.warning(
                "pymupdf4llm extraction failed for %s; falling back to PyMuPDF",
                pdf_path,
                exc_info=True,
            )
            return super().extract_text(pdf_path)

        parts: list[str] = []
        # page_chunks yields one entry per page in reading order; the list index
        # is the authoritative 1-indexed page number (matches the parent's
        # ``<!-- Page N -->`` convention without relying on backend metadata keys).
        for index, chunk in enumerate(chunks):
            page_number = index + 1
            if isinstance(chunk, dict):
                text = str(chunk.get("text", "") or "")
            else:
                text = str(chunk or "")
            parts.append(f"\n<!-- Page {page_number} -->\n")
            if text.strip():
                parts.append(text.strip())

        markdown = "\n".join(parts).strip()
        if not markdown:
            return super().extract_text(pdf_path)
        return markdown
