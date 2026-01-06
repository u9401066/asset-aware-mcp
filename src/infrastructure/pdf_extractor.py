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
        Extract all images from PDF with page numbers using multi-strategy approach.

        Strategy:
        1. XObject images (standard embedded images)
        2. Vector graphics rendering (for charts/diagrams drawn with paths)
        3. Smart region detection (finds non-text areas and renders them)

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
                page_images_found = []

                # Strategy 1: Extract XObject images (standard)
                page_images = page.get_images(full=True)
                for img_index, img in enumerate(page_images):
                    try:
                        image_data = self._extract_single_image(doc, img)
                        if image_data:
                            img_dict = {
                                "page": page_num + 1,
                                "image_bytes": image_data["image"],
                                "ext": image_data["ext"],
                                "width": image_data["width"],
                                "height": image_data["height"],
                                "index_on_page": img_index + 1,
                            }
                            images.append(img_dict)
                            page_images_found.append(img_dict)
                    except Exception:
                        continue

                # Strategy 2: Vector graphics detection
                try:
                    vector_images = self._extract_vector_graphics_regions(page)
                    for idx, vector_image in enumerate(vector_images):
                        # Check if this overlaps with existing XObject images
                        if not self._overlaps_existing_images(
                            vector_image["bbox"], page_images_found
                        ):
                            images.append(
                                {
                                    "page": page_num + 1,
                                    "image_bytes": vector_image["image"],
                                    "ext": vector_image["ext"],
                                    "width": vector_image["width"],
                                    "height": vector_image["height"],
                                    "index_on_page": 900 + idx,  # 900+ for vector
                                }
                            )
                except Exception:
                    pass

                # Strategy 3: Smart region detection (find non-text areas)
                try:
                    region_images = self._extract_non_text_regions(page)
                    for idx, region_image in enumerate(region_images):
                        # Check if already captured
                        if not self._overlaps_existing_images(
                            region_image["bbox"], page_images_found
                        ):
                            images.append(
                                {
                                    "page": page_num + 1,
                                    "image_bytes": region_image["image"],
                                    "ext": region_image["ext"],
                                    "width": region_image["width"],
                                    "height": region_image["height"],
                                    "index_on_page": 800 + idx,  # 800+ for regions
                                }
                            )
                except Exception:
                    pass

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

    def _extract_vector_graphics_regions(self, page: fitz.Page) -> list[dict[str, Any]]:
        """
        Detect and extract multiple vector graphics regions as separate images.
        More aggressive than _extract_vector_graphics.
        """
        drawings = page.get_drawings()
        if not drawings or len(drawings) < 10:
            return []

        # Group drawings by spatial proximity (cluster analysis)
        clusters = self._cluster_drawings(drawings)
        results = []

        for cluster_bbox in clusters:
            # Skip small regions
            if cluster_bbox.width < 80 or cluster_bbox.height < 80:
                continue

            try:
                # Render the region
                zoom = 2.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat, clip=cluster_bbox, alpha=False)

                image_bytes = pix.tobytes("png")
                size_mb = len(image_bytes) / (1024 * 1024)

                if size_mb <= self.max_image_size_mb:
                    results.append(
                        {
                            "image": image_bytes,
                            "ext": "png",
                            "width": pix.width,
                            "height": pix.height,
                            "bbox": cluster_bbox,
                        }
                    )
            except Exception:
                continue

        return results

    def _cluster_drawings(self, drawings: list) -> list[fitz.Rect]:
        """
        Cluster drawings into regions based on spatial proximity.
        Simple algorithm: merge bboxes that are close to each other.
        """
        if not drawings:
            return []

        # Get all rects
        rects = []
        for d in drawings:
            r = d["rect"]
            if r.width > 1 or r.height > 1:  # Skip tiny artifacts
                rects.append(r)

        if not rects:
            return []

        # Sort by y-coordinate (top to bottom)
        rects.sort(key=lambda r: r.y0)

        clusters = []
        current_cluster = rects[0]

        for rect in rects[1:]:
            # Check if rect is close to current cluster (within 50 points)
            distance = max(
                0,
                rect.y0 - current_cluster.y1,  # vertical distance
                rect.x0 - current_cluster.x1,  # horizontal distance
            )

            if distance < 50:
                # Merge into current cluster
                current_cluster = current_cluster | rect
            else:
                # Start new cluster if current is significant
                if current_cluster.width > 80 and current_cluster.height > 80:
                    clusters.append(current_cluster)
                current_cluster = rect

        # Don't forget the last cluster
        if current_cluster.width > 80 and current_cluster.height > 80:
            clusters.append(current_cluster)

        return clusters

    def _extract_non_text_regions(self, page: fitz.Page) -> list[dict[str, Any]]:
        """
        Extract non-text regions from the page.
        Strategy: Find areas without text blocks and render them as images.
        """
        # Get text blocks
        text_blocks = page.get_text("blocks")
        page_rect = page.rect

        # Create a set of text bboxes
        text_rects = []
        for block in text_blocks:
            if block[6] == 0:  # Type 0 = text block
                bbox = fitz.Rect(block[:4])
                text_rects.append(bbox)

        # If page is mostly text, skip this strategy
        if len(text_rects) > 20:
            return []

        # Find potential image regions (areas with significant empty space)
        # Divide page into grid and check coverage
        results = []
        grid_size = 4
        cell_width = page_rect.width / grid_size
        cell_height = page_rect.height / grid_size

        for row in range(grid_size):
            for col in range(grid_size):
                cell = fitz.Rect(
                    col * cell_width,
                    row * cell_height,
                    (col + 1) * cell_width,
                    (row + 1) * cell_height,
                )

                # Check if this cell has minimal text coverage
                text_coverage = 0
                for text_rect in text_rects:
                    intersection = cell & text_rect
                    if not intersection.is_empty:
                        text_coverage += intersection.get_area()

                cell_area = cell.get_area()
                if cell_area > 0 and text_coverage / cell_area < 0.1:
                    # Less than 10% text coverage - might be an image region
                    try:
                        # Check if there's actual content (not just white space)
                        zoom = 1.5
                        mat = fitz.Matrix(zoom, zoom)
                        pix = page.get_pixmap(matrix=mat, clip=cell, alpha=False)

                        # Simple heuristic: check if region has color variation
                        if self._has_visual_content(pix):
                            image_bytes = pix.tobytes("png")
                            size_mb = len(image_bytes) / (1024 * 1024)

                            if size_mb <= self.max_image_size_mb:
                                results.append(
                                    {
                                        "image": image_bytes,
                                        "ext": "png",
                                        "width": pix.width,
                                        "height": pix.height,
                                        "bbox": cell,
                                    }
                                )
                    except Exception:
                        continue

        return results

    def _has_visual_content(self, pix: fitz.Pixmap) -> bool:
        """
        Check if a pixmap has actual visual content (not just blank/white).
        Simple heuristic based on color variance.
        """
        # Sample some pixels
        samples = pix.samples
        if len(samples) < 100:
            return False

        # Check variance in pixel values
        sample_size = min(1000, len(samples))
        sample_bytes = samples[:sample_size]

        # Calculate simple variance
        mean_val = sum(sample_bytes) / len(sample_bytes)
        variance = sum((b - mean_val) ** 2 for b in sample_bytes) / len(sample_bytes)

        # If variance is too low, it's probably blank
        return variance > 100  # Threshold for "interesting" content

    def _overlaps_existing_images(
        self, bbox: fitz.Rect, existing_images: list[dict]
    ) -> bool:
        """
        Check if a bounding box overlaps significantly with existing images.
        Used to avoid duplicate extractions.
        """
        for _img in existing_images:
            # We don't have bbox info for XObject images, so we skip this check
            # In practice, XObject images are usually separate from vector graphics
            pass

        # For now, assume no overlap (conservative approach)
        return False

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
