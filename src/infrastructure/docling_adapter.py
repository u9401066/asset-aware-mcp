"""
Infrastructure Layer - Docling Adapter

High-fidelity structured PDF extraction via IBM Docling, exposed through the
same ``parse() -> MarkerParseResult`` contract as :class:`MarkerPDFExtractor`.
This lets Docling drop straight into the existing ``marker_extractor`` slot and
reuse the whole ``_ingest_single_with_marker`` asset pipeline (blocks.json,
section hierarchy, figure/table assets) with zero changes to the service layer.

Why Docling:
- MIT licensed (cleanest for this Apache-2.0 project).
- Page layout + reading order + table structure + formula + figure
  classification in one ``DoclingDocument``.
- Verified compatible with the secure ``Pillow>=12.2.0`` floor.
- Ships the lightweight GraniteDocling VLM, aligned with the granite backend.

The backend is heavy and optional, so every docling import is lazy and guarded;
the module always imports even when docling is not installed.
"""

from __future__ import annotations

import contextlib
import io
import logging
from pathlib import Path
from typing import Any

from src.infrastructure.marker_adapter import MarkerBlock, MarkerParseResult

logger = logging.getLogger(__name__)

DOCLING_INSTALL_HINT = (
    "Docling backend not installed. Install the optional extra via "
    "`uv tool install --upgrade 'asset-aware-mcp[docling]'` "
    "(or `uv pip install docling`), or set ETL_ENGINE=pymupdf."
)

# Docling ``DocItemLabel`` -> Marker block_type convention consumed downstream
# (annotate_marker_blocks / manifest generation). Unknown labels fall back to
# "Text" so no content is dropped.
_DOCLING_LABEL_MAP: dict[str, str] = {
    "section_header": "SectionHeader",
    "title": "SectionHeader",
    "table": "Table",
    "picture": "Figure",
    "chart": "Figure",
    "figure": "Figure",
    "caption": "Caption",
    "formula": "Equation",
    "equation": "Equation",
    "code": "Code",
    "footnote": "Footnote",
    "page_header": "PageHeader",
    "page_footer": "PageFooter",
    "list_item": "ListItem",
    "text": "Text",
    "paragraph": "Text",
}


class DoclingBackendUnavailable(RuntimeError):
    """Raised when the optional ``docling`` backend cannot be imported."""


class DoclingExtractor:
    """Docling structured parser emitting Marker-compatible results.

    Mirrors :class:`MarkerPDFExtractor`'s public surface
    (``require_backend_available`` + ``parse``) so it can be injected wherever a
    structured extractor is expected.
    """

    def __init__(
        self,
        output_dir: Path | None = None,
        *,
        images_scale: float = 2.0,
    ) -> None:
        """Initialise the Docling extractor.

        Args:
            output_dir: Optional working directory for image spill-over.
            images_scale: Render scale for extracted page/figure images
                (2.0 ~= 144 DPI, a good quality/size trade-off).
        """
        self.output_dir = output_dir or Path("./temp_output")
        self.images_scale = images_scale

    @staticmethod
    def require_backend_available() -> None:
        """Preflight the docling import without loading heavy models."""
        try:
            from docling.document_converter import (  # type: ignore # noqa: F401
                DocumentConverter,
            )
        except (ImportError, OSError) as exc:
            raise DoclingBackendUnavailable(DOCLING_INSTALL_HINT) from exc

    def _build_converter(self, *, extract_images: bool) -> Any:
        """Create a DocumentConverter with picture generation toggled."""
        from docling.datamodel.base_models import InputFormat  # type: ignore
        from docling.datamodel.pipeline_options import (  # type: ignore
            PdfPipelineOptions,
        )
        from docling.document_converter import (  # type: ignore
            DocumentConverter,
            PdfFormatOption,
        )

        pipeline_options = PdfPipelineOptions()
        # Enable image byte generation only when figures are requested.
        for attr in ("generate_picture_images", "generate_page_images"):
            if hasattr(pipeline_options, attr):
                setattr(pipeline_options, attr, extract_images)
        if hasattr(pipeline_options, "images_scale"):
            pipeline_options.images_scale = self.images_scale
        if hasattr(pipeline_options, "do_table_structure"):
            pipeline_options.do_table_structure = True

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def parse(
        self,
        pdf_path: Path,
        *,
        extract_images: bool = True,
        max_pages_per_chunk: int | None = None,
        page_map: list[int] | None = None,
        reported_page_count: int | None = None,
    ) -> MarkerParseResult:
        """Parse a PDF into a Marker-compatible structured result.

        Signature mirrors :meth:`MarkerPDFExtractor.parse` so the two are
        interchangeable in the document service. ``max_pages_per_chunk`` is
        accepted for parity; Docling manages memory internally and processes the
        document in one pass.
        """
        self.require_backend_available()
        converter = self._build_converter(extract_images=extract_images)
        result = converter.convert(str(pdf_path))
        document = getattr(result, "document", None)
        if document is None:
            raise DoclingBackendUnavailable(
                "Docling returned no document; the file may be unsupported."
            )

        markdown = self._export_markdown(document)
        blocks = self._extract_blocks(document)
        images = self._extract_images(document) if extract_images else {}
        page_count = self._resolve_page_count(document, reported_page_count)

        if page_map:
            self._apply_page_map(blocks, page_map)

        toc = self._extract_toc(blocks)
        metadata: dict[str, Any] = {
            "backend": "docling",
            "block_count": len(blocks),
            "image_count": len(images),
        }
        return MarkerParseResult(
            markdown=markdown,
            blocks=blocks,
            toc=toc,
            images=images,
            metadata=metadata,
            page_count=page_count,
        )

    @staticmethod
    def _export_markdown(document: Any) -> str:
        """Export DoclingDocument to Markdown, defensively."""
        exporter = getattr(document, "export_to_markdown", None)
        if callable(exporter):
            try:
                return str(exporter() or "")
            except Exception:
                logger.warning("Docling export_to_markdown failed", exc_info=True)
        return ""

    def _extract_blocks(self, document: Any) -> list[MarkerBlock]:
        """Map DoclingDocument items to Marker-compatible blocks."""
        blocks: list[MarkerBlock] = []
        try:
            iterator = document.iterate_items()
        except Exception:
            logger.warning("Docling iterate_items unavailable", exc_info=True)
            return blocks

        for counter, entry in enumerate(iterator, start=1):
            item = entry[0] if isinstance(entry, tuple) else entry
            label = str(getattr(item, "label", "") or "").lower()
            block_type = _DOCLING_LABEL_MAP.get(label, "Text")
            text = str(getattr(item, "text", "") or "")
            page, bbox = self._first_provenance(item)
            blocks.append(
                MarkerBlock(
                    block_id=f"docling_{counter}",
                    block_type=block_type,
                    page=page,
                    text=text,
                    bbox=bbox,
                    metadata={"docling_label": label},
                )
            )
        return blocks

    @staticmethod
    def _first_provenance(item: Any) -> tuple[int, list[float]]:
        """Extract (1-indexed page, [x0,y0,x1,y1] bbox) from a Docling item."""
        prov = getattr(item, "prov", None) or []
        if not prov:
            return 1, []
        first = prov[0]
        page = int(getattr(first, "page_no", 1) or 1)
        bbox: list[float] = []
        bb = getattr(first, "bbox", None)
        if bb is not None:
            try:
                bbox = [float(bb.l), float(bb.t), float(bb.r), float(bb.b)]
            except Exception:
                bbox = []
        return page, bbox

    def _extract_images(self, document: Any) -> dict[str, bytes]:
        """Render Docling picture items to PNG bytes keyed by a stable name."""
        images: dict[str, bytes] = {}
        pictures = getattr(document, "pictures", None) or []
        for idx, picture in enumerate(pictures):
            page, _bbox = self._first_provenance(picture)
            pil_image = self._picture_pil(picture, document)
            if pil_image is None:
                continue
            try:
                buffer = io.BytesIO()
                pil_image.save(buffer, format="PNG")
            except Exception:
                logger.debug("Docling picture %d not serialisable", idx, exc_info=True)
                continue
            # Marker-like key: ``_page_<0-indexed>_Figure_<n>.png``
            images[f"_page_{page - 1}_Figure_{idx}.png"] = buffer.getvalue()
        return images

    @staticmethod
    def _picture_pil(picture: Any, document: Any) -> Any:
        """Best-effort retrieval of a PIL image from a Docling picture item."""
        image_ref = getattr(picture, "image", None)
        pil_image = getattr(image_ref, "pil_image", None) if image_ref else None
        if pil_image is not None:
            return pil_image
        getter = getattr(picture, "get_image", None)
        if callable(getter):
            try:
                return getter(document)
            except Exception:
                return None
        return None

    @staticmethod
    def _apply_page_map(blocks: list[MarkerBlock], page_map: list[int]) -> None:
        """Remap subset-local page numbers back to original PDF pages in place."""
        for block in blocks:
            if 1 <= block.page <= len(page_map):
                block.page = page_map[block.page - 1]

    @staticmethod
    def _extract_toc(blocks: list[MarkerBlock]) -> list[dict[str, Any]]:
        """Derive a simple TOC from section-header blocks."""
        toc: list[dict[str, Any]] = []
        for block in blocks:
            if block.block_type == "SectionHeader" and block.text.strip():
                toc.append(
                    {"title": block.text.strip(), "page": block.page, "level": 1}
                )
        return toc

    @staticmethod
    def _resolve_page_count(document: Any, reported_page_count: int | None) -> int:
        """Resolve the reported page count."""
        if reported_page_count:
            return reported_page_count
        pages = getattr(document, "pages", None)
        if pages is not None:
            with contextlib.suppress(Exception):
                return len(pages)
        return 0
