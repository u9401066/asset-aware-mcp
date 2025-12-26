"""
Infrastructure Layer - Docling Adapter

PDF extraction using Docling for high-quality table extraction,
caption pairing, and structured document understanding.

MIT Licensed - Compatible with Apache-2.0.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.repositories import PDFExtractorInterface

if TYPE_CHECKING:
    from docling.datamodel.document import ConversionResult
    from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


@dataclass
class DoclingConfig:
    """Configuration for Docling adapter."""

    # Model options
    do_ocr: bool = False  # Enable OCR for scanned PDFs
    do_table_structure: bool = True  # Enable TableFormer
    table_structure_options: dict[str, Any] = field(default_factory=dict)

    # Performance options
    pdf_backend: str = "docling"  # or "pypdfium2" for lighter weight
    num_threads: int = 4

    # Output options
    generate_page_images: bool = False  # We extract images from PDF directly
    generate_picture_images: bool = True  # Extract figures as images


class DoclingAdapter(PDFExtractorInterface):
    """
    PDF extraction using Docling.

    Features:
    - High-quality table extraction (TableFormer)
    - Caption pairing for figures and tables
    - Reading order correction
    - Structured document output
    """

    def __init__(self, config: DoclingConfig | None = None):
        """
        Initialize Docling adapter.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or DoclingConfig()
        self._converter: DocumentConverter | None = None
        self._is_available: bool | None = None

    @property
    def is_available(self) -> bool:
        """Check if Docling is available."""
        if self._is_available is None:
            try:
                from docling.document_converter import DocumentConverter

                self._is_available = True
            except ImportError:
                logger.warning("Docling not installed. Install with: uv add docling")
                self._is_available = False
        return self._is_available

    def _get_converter(self) -> "DocumentConverter":
        """Get or create DocumentConverter instance."""
        if self._converter is None:
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import (
                PdfPipelineOptions,
                TableFormerMode,
            )
            from docling.document_converter import DocumentConverter, PdfFormatOption

            # Configure pipeline options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self.config.do_ocr
            pipeline_options.do_table_structure = self.config.do_table_structure

            if self.config.do_table_structure:
                pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE

            pipeline_options.generate_page_images = self.config.generate_page_images
            pipeline_options.generate_picture_images = (
                self.config.generate_picture_images
            )

            # Create converter
            self._converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

        return self._converter

    def convert_document(self, pdf_path: Path) -> "ConversionResult":
        """
        Convert PDF to Docling document.

        This is the main entry point for full document conversion.

        Args:
            pdf_path: Path to PDF file

        Returns:
            ConversionResult with structured document
        """
        if not self.is_available:
            raise ImportError("Docling not installed")

        converter = self._get_converter()
        result = converter.convert(str(pdf_path))
        return result

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF as markdown.

        Uses Docling's high-quality conversion with:
        - Correct reading order
        - Table structure preserved
        - Figure captions linked

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown-formatted text with page markers
        """
        if not self.is_available:
            raise ImportError("Docling not installed")

        result = self.convert_document(pdf_path)
        doc = result.document

        # Export to markdown
        markdown = doc.export_to_markdown()

        # Add page markers for compatibility with our chunking system
        # Docling doesn't add page markers by default, so we inject them
        markdown_with_pages = self._inject_page_markers(markdown, doc)

        return markdown_with_pages

    def _inject_page_markers(self, markdown: str, doc: Any) -> str:
        """
        Inject page markers into markdown.

        Docling's markdown doesn't include page markers,
        so we add them based on element locations.
        """
        # For now, add a simple page 1 marker at the start
        # TODO: Enhance with proper page tracking from doc.pages
        lines = markdown.split("\n")
        result = ["\n<!-- Page 1 -->\n"]

        current_page = 1
        for line in lines:
            # Check if we need to insert a new page marker
            # This is a simplified heuristic
            result.append(line)

        return "\n".join(result)

    def extract_images(self, pdf_path: Path) -> list[dict]:
        """
        Extract images/figures from PDF.

        Uses Docling's figure detection which includes:
        - Caption pairing
        - Better figure boundary detection

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with image info including captions
        """
        if not self.is_available:
            raise ImportError("Docling not installed")

        result = self.convert_document(pdf_path)
        doc = result.document

        images = []
        fig_index = 0

        # Extract pictures from Docling document
        for element in doc.iterate_items():
            if hasattr(element, "image") and element.image is not None:
                fig_index += 1
                page_no = getattr(element.prov[0], "page_no", 1) if element.prov else 1

                # Get image data
                image_data = element.image
                if hasattr(image_data, "pil_image"):
                    import io

                    pil_img = image_data.pil_image
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    image_bytes = buf.getvalue()

                    images.append(
                        {
                            "page": page_no,
                            "image_bytes": image_bytes,
                            "ext": "png",
                            "width": pil_img.width,
                            "height": pil_img.height,
                            "index_on_page": fig_index,
                            "caption": self._get_caption(element),
                        }
                    )

        return images

    def _get_caption(self, element: Any) -> str:
        """Extract caption from a Docling element."""
        # Docling pairs captions automatically
        if hasattr(element, "caption") and element.caption:
            return str(element.caption)
        if hasattr(element, "text") and element.text:
            # Check if this looks like a caption
            text = str(element.text)
            if text.lower().startswith(("figure", "fig.", "fig ")):
                return text
        return ""

    def extract_tables(self, pdf_path: Path) -> list[dict]:
        """
        Extract tables with structure recognition.

        Uses TableFormer for accurate table structure.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with table info including:
            - markdown: Full table in Markdown
            - caption: Table caption
            - row_count, col_count: Dimensions
            - page: Page number
        """
        if not self.is_available:
            raise ImportError("Docling not installed")

        result = self.convert_document(pdf_path)
        doc = result.document

        tables = []
        table_index = 0

        for element in doc.iterate_items():
            # Check if this is a table element
            element_type = type(element).__name__
            if element_type == "TableItem" or (
                hasattr(element, "data") and hasattr(element.data, "table_cells")
            ):
                table_index += 1
                page_no = getattr(element.prov[0], "page_no", 1) if element.prov else 1

                # Export table to markdown
                if hasattr(element, "export_to_markdown"):
                    table_md = element.export_to_markdown()
                elif hasattr(element, "text"):
                    table_md = str(element.text)
                else:
                    table_md = ""

                # Count rows and columns
                row_count, col_count = self._count_table_dimensions(table_md)

                tables.append(
                    {
                        "id": f"tab_{table_index}",
                        "page": page_no,
                        "markdown": table_md,
                        "caption": self._get_caption(element),
                        "row_count": row_count,
                        "col_count": col_count,
                        "preview": table_md[:100] if table_md else "",
                    }
                )

        return tables

    def _count_table_dimensions(self, table_md: str) -> tuple[int, int]:
        """Count rows and columns in a markdown table."""
        lines = [l for l in table_md.strip().split("\n") if l.strip()]
        if not lines:
            return 0, 0

        # Count rows (excluding separator line)
        rows = [l for l in lines if not l.strip().startswith("|--") and "|" in l]
        row_count = len(rows)

        # Count columns from first row
        if rows:
            col_count = rows[0].count("|") - 1  # Subtract edge pipes
            col_count = max(col_count, 0)
        else:
            col_count = 0

        return row_count, col_count

    def get_page_count(self, pdf_path: Path) -> int:
        """Get total page count of PDF."""
        if not self.is_available:
            raise ImportError("Docling not installed")

        result = self.convert_document(pdf_path)
        return len(result.document.pages) if hasattr(result.document, "pages") else 0

    def get_metadata(self, pdf_path: Path) -> dict:
        """Get PDF metadata (title, author, etc.)."""
        if not self.is_available:
            raise ImportError("Docling not installed")

        result = self.convert_document(pdf_path)
        doc = result.document

        metadata = {}
        if hasattr(doc, "name"):
            metadata["title"] = doc.name
        if hasattr(doc, "origin") and doc.origin:
            if hasattr(doc.origin, "filename"):
                metadata["filename"] = doc.origin.filename

        return metadata

    def get_document_structure(self, pdf_path: Path) -> dict:
        """
        Get structured document representation.

        Returns Docling's rich document structure including:
        - Sections with headings
        - Tables with captions
        - Figures with captions
        - Reading order

        Args:
            pdf_path: Path to PDF file

        Returns:
            Dict with structured document info
        """
        if not self.is_available:
            raise ImportError("Docling not installed")

        result = self.convert_document(pdf_path)
        doc = result.document

        structure = {
            "title": getattr(doc, "name", ""),
            "sections": [],
            "tables": [],
            "figures": [],
        }

        for element in doc.iterate_items():
            element_type = type(element).__name__

            if element_type == "SectionHeaderItem":
                structure["sections"].append(
                    {
                        "title": str(element.text) if hasattr(element, "text") else "",
                        "level": getattr(element, "level", 1),
                    }
                )
            elif element_type == "TableItem":
                structure["tables"].append(
                    {
                        "caption": self._get_caption(element),
                        "has_content": True,
                    }
                )
            elif element_type == "PictureItem":
                structure["figures"].append(
                    {
                        "caption": self._get_caption(element),
                        "has_image": hasattr(element, "image"),
                    }
                )

        return structure


# Singleton instance for convenience
_default_adapter: DoclingAdapter | None = None


def get_docling_adapter() -> DoclingAdapter:
    """Get default Docling adapter instance."""
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = DoclingAdapter()
    return _default_adapter
