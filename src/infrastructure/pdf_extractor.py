"""
Infrastructure Layer - PDF Extractor

Implementation using PyMuPDF (fitz) for PDF processing.
Key feature: Extracts images WITH page numbers for verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz  # type: ignore # PyMuPDF

from src.domain.repositories import PDFExtractorInterface

from .config import settings


@dataclass
class ExtractedImage:
    """Data class for extracted image information."""

    page: int  # 1-indexed page number
    image_bytes: bytes
    ext: str
    width: int
    height: int
    index_on_page: int  # Image index on this page


class PyMuPDFExtractor(PDFExtractorInterface):
    """
    PDF extraction using PyMuPDF.

    Features:
    - Text extraction with formatting hints
    - Image extraction with page number tracking
    - Page comments in markdown for traceability
    """

    def __init__(self, max_image_size_mb: float | None = None):
        """
        Initialize extractor.

        Args:
            max_image_size_mb: Maximum image size to extract (default from settings)
        """
        self.max_image_size_mb = max_image_size_mb or settings.max_image_size_mb

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from PDF as markdown.

        Includes page markers as HTML comments for traceability:
        <!-- Page 1 -->

        Args:
            pdf_path: Path to PDF file

        Returns:
            Markdown-formatted text with page markers
        """
        doc = fitz.open(str(pdf_path))
        text_parts = []

        try:
            for page_num, page in enumerate(doc):
                # Add page marker
                text_parts.append(f"\n<!-- Page {page_num + 1} -->\n")

                # Get text with formatting info
                page_text = self._extract_page_text(page)
                if page_text:
                    text_parts.append(page_text)
        finally:
            doc.close()

        return "\n".join(text_parts)

    def _extract_page_text(self, page: fitz.Page) -> str:
        """Extract text from a single page with basic formatting."""
        blocks = page.get_text("dict")["blocks"]
        lines = []

        for block in blocks:
            if block["type"] != 0:  # Skip non-text blocks
                continue

            for line in block.get("lines", []):
                line_text = ""

                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue

                    font_size = span.get("size", 12)
                    flags = span.get("flags", 0)

                    # Detect headings by font size
                    if font_size > 16:
                        text = f"# {text}"
                    elif font_size > 14:
                        text = f"## {text}"
                    elif font_size > 12:
                        text = f"### {text}"

                    # Detect bold (flag bit 2^4 = 16)
                    if flags & 16 and not text.startswith("#"):
                        text = f"**{text}**"

                    line_text += text

                if line_text.strip():
                    lines.append(line_text)

        return "\n".join(lines)

    def extract_images(self, pdf_path: Path) -> list[dict]:
        """
        Extract all images from PDF with page numbers.
        Also detects and renders vector graphics (drawings) as images.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with:
            - page: int (1-indexed)
            - image_bytes: bytes
            - ext: str
            - width: int
            - height: int
            - index_on_page: int
        """
        doc = fitz.open(str(pdf_path))
        images = []

        try:
            for page_num, page in enumerate(doc):
                # 1. Extract XObject images (standard)
                page_images = page.get_images(full=True)

                for img_index, img in enumerate(page_images):
                    try:
                        image_data = self._extract_single_image(doc, img)
                        if image_data:
                            images.append(
                                {
                                    "page": page_num + 1,
                                    "image_bytes": image_data["image"],
                                    "ext": image_data["ext"],
                                    "width": image_data["width"],
                                    "height": image_data["height"],
                                    "index_on_page": img_index + 1,
                                }
                            )
                    except Exception:
                        continue

                # 2. Fallback: Extract vector graphics if no images found or many drawings exist
                # This handles cases where figures are composed of vector paths
                try:
                    vector_image = self._extract_vector_graphics(page)
                    if vector_image:
                        # If we already found XObjects, only add vector if it's "significant"
                        # or if it's likely a separate figure.
                        # For now, we add it as a separate "image" with a special index.
                        images.append(
                            {
                                "page": page_num + 1,
                                "image_bytes": vector_image["image"],
                                "ext": vector_image["ext"],
                                "width": vector_image["width"],
                                "height": vector_image["height"],
                                "index_on_page": 999,  # Special index for vector graphics
                            }
                        )
                except Exception:
                    continue

        finally:
            doc.close()

        return images

    def _extract_vector_graphics(self, page: fitz.Page) -> dict | None:
        """
        Detect and render vector graphics (drawings) as an image.
        Useful for PDFs where figures are not stored as XObject images.
        """
        drawings = page.get_drawings()
        # Threshold for "significant" graphics (e.g., more than 20 paths)
        if not drawings or len(drawings) < 20:
            return None

        # Calculate bounding box of all drawings
        bbox = None
        for d in drawings:
            # Skip very small or thin lines that might be artifacts
            r = d["rect"]
            if r.width < 1 and r.height < 1:
                continue
            if bbox is None:
                bbox = r
            else:
                bbox = bbox | r

        # If bbox is too small or empty, skip
        if not bbox or bbox.is_empty or bbox.width < 50 or bbox.height < 50:
            return None

        # Render the area with a reasonable resolution (zoom=2 for 144 DPI)
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, clip=bbox, alpha=False)

        image_bytes = pix.tobytes("png")

        # Check size limit
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > self.max_image_size_mb:
            return None

        return {
            "image": image_bytes,
            "ext": "png",
            "width": pix.width,
            "height": pix.height,
        }

    def _extract_single_image(self, doc: fitz.Document, img: tuple) -> dict | None:
        """Extract a single image from document."""
        xref = img[0]
        base_image = doc.extract_image(xref)

        if not base_image:
            return None

        image_bytes = base_image["image"]

        # Check size limit
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > self.max_image_size_mb:
            return None

        return {
            "image": image_bytes,
            "ext": base_image.get("ext", "png"),
            "width": base_image.get("width", 0),
            "height": base_image.get("height", 0),
        }

    def get_page_count(self, pdf_path: Path) -> int:
        """Get total page count of PDF."""
        doc = fitz.open(str(pdf_path))
        try:
            return len(doc)
        finally:
            doc.close()

    def get_metadata(self, pdf_path: Path) -> dict:
        """Get PDF metadata (title, author, etc.)."""
        doc = fitz.open(str(pdf_path))
        try:
            return doc.metadata or {}
        finally:
            doc.close()

    def extract_tables(self, pdf_path: Path) -> list[dict]:
        """
        Extract tables from PDF using PyMuPDF's find_tables().

        Note: This is a heuristic-based approach, not as accurate as
        Docling's TableFormer model. Works best for simple grid tables.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with table info
        """
        doc = fitz.open(str(pdf_path))
        tables = []
        table_index = 0

        try:
            for page_num, page in enumerate(doc):
                try:
                    # PyMuPDF's experimental table finder
                    page_tables = page.find_tables()

                    for tab in page_tables:
                        table_index += 1

                        # Extract table data
                        try:
                            # Get table as pandas DataFrame if available
                            if hasattr(tab, "to_pandas"):
                                df = tab.to_pandas()
                                markdown = df.to_markdown(index=False)
                                row_count = len(df)
                                col_count = len(df.columns)
                            else:
                                # Fallback: extract cells manually
                                markdown = self._table_to_markdown(tab)
                                row_count = (
                                    tab.row_count if hasattr(tab, "row_count") else 0
                                )
                                col_count = (
                                    tab.col_count if hasattr(tab, "col_count") else 0
                                )

                            tables.append(
                                {
                                    "id": f"tab_{table_index}",
                                    "page": page_num + 1,
                                    "markdown": markdown,
                                    "caption": "",  # PyMuPDF doesn't detect captions
                                    "row_count": row_count,
                                    "col_count": col_count,
                                    "preview": markdown[:100] if markdown else "",
                                    "has_header": True,
                                    "source": "pymupdf",
                                }
                            )
                        except Exception:
                            continue

                except Exception:
                    # find_tables() may not be available in older versions
                    continue

        finally:
            doc.close()

        return tables

    def _table_to_markdown(self, table: Any) -> str:
        """Convert PyMuPDF table to markdown format."""
        if not hasattr(table, "extract"):
            return ""

        try:
            cells = table.extract()
            if not cells:
                return ""

            lines = []
            for i, row in enumerate(cells):
                # Clean cells
                clean_row = [str(cell).strip() if cell else "" for cell in row]
                lines.append("| " + " | ".join(clean_row) + " |")

                # Add header separator after first row
                if i == 0:
                    separator = "| " + " | ".join(["---"] * len(clean_row)) + " |"
                    lines.append(separator)

            return "\n".join(lines)

        except Exception:
            return ""
