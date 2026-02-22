"""
Infrastructure Layer - PDF Extractor

Implementation using PyMuPDF (fitz) for PDF processing.
Key feature: Extracts images WITH page numbers for verification.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import Any

import fitz  # type: ignore # PyMuPDF

from src.domain.etl_profile import ETLProfile
from src.domain.repositories import PDFExtractorInterface

from .config import settings

logger = logging.getLogger(__name__)


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
    - Configurable via ETLProfile (font thresholds, noise filters, etc.)
    """

    def __init__(
        self,
        profile: ETLProfile | None = None,
        max_image_size_mb: float | None = None,
    ):
        """
        Initialize extractor.

        Args:
            profile: ETL extraction profile (default: ETLProfile.default())
            max_image_size_mb: Maximum image size to extract (default from settings)
        """
        self.profile = profile or ETLProfile.default()
        self.max_image_size_mb = max_image_size_mb or settings.max_image_size_mb

        # Pre-compile regexes from profile (once, at init)
        self._heading_noise_re = self.profile.compile_heading_noise_re()
        self._table_caption_re = self.profile.compile_table_caption_re()
        self._figure_caption_re = self.profile.compile_figure_caption_re()
        self._numbered_section_re = self.profile.compile_numbered_section_re()

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

        raw_markdown = "\n".join(text_parts)

        # Post-process: merge consecutive same-level headings
        # (PDF wraps long headings across multiple lines, each becoming a separate # heading)
        return self._merge_consecutive_headings(raw_markdown)

    def _merge_consecutive_headings(self, markdown: str) -> str:
        """
        Merge consecutive markdown headings of the same level into one.

        PDF text extraction often splits long headings across multiple lines,
        producing fragmented headings like:
            ## Relationship Between the
            ## Intensive Care Unit and the
            ## Operating Room

        This merges them into:
            ## Relationship Between the Intensive Care Unit and the Operating Room

        Also handles standalone chapter numbers (e.g. '# 79') by combining
        them with adjacent chapter titles into 'Chapter {num}: {title}'.
        """
        lines = markdown.split("\n")
        merged: list[str] = []
        i = 0

        while i < len(lines):
            line = lines[i]
            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if header_match:
                level = header_match.group(1)
                title_parts = [header_match.group(2).strip()]

                # Look ahead for consecutive same-level headings
                j = i + 1
                while j < len(lines):
                    next_match = re.match(r"^(#{1,6})\s+(.+)$", lines[j])
                    if next_match and next_match.group(1) == level:
                        title_parts.append(next_match.group(2).strip())
                        j += 1
                    else:
                        break

                merged_title = " ".join(title_parts)
                merged.append(f"{level} {merged_title}")
                i = j
            else:
                merged.append(line)
                i += 1

        # Second pass: handle standalone chapter numbers for H1
        # e.g. '# 79' near '# Pediatric and Neonatal Critical Care'
        #  → '# Chapter 79: Pediatric and Neonatal Critical Care'
        result: list[str] = []
        skip_indices: set[int] = set()

        for idx, line in enumerate(merged):
            if idx in skip_indices:
                continue

            h1_match = re.match(r"^#\s+(.+)$", line)
            if h1_match:
                text = h1_match.group(1).strip()
                # Check if this H1 is just a number (chapter number)
                if re.match(r"^\d+$", text):
                    chapter_num = text
                    # Look nearby (within 5 lines) for another H1 with actual title
                    title_found = None
                    title_idx = None
                    for search_dir in [-1, 1]:  # search before, then after
                        for offset in range(1, 6):
                            check_idx = idx + search_dir * offset
                            if (
                                0 <= check_idx < len(merged)
                                and check_idx not in skip_indices
                            ):
                                check_match = re.match(r"^#\s+(.+)$", merged[check_idx])
                                if check_match:
                                    candidate = check_match.group(1).strip()
                                    if not re.match(r"^\d+$", candidate):
                                        title_found = candidate
                                        title_idx = check_idx
                                        break
                        if title_found:
                            break

                    if title_found and title_idx is not None:
                        skip_indices.add(title_idx)
                        result.append(f"# Chapter {chapter_num}: {title_found}")
                    else:
                        result.append(line)
                else:
                    result.append(line)
            else:
                result.append(line)

        return "\n".join(result)

    @staticmethod
    def _section_level_from_number(text: str) -> int:
        """Determine heading level from numbered section prefix.

        "1. Intro" → 1, "3.1. Methods" → 2, "3.1.1. Detail" → 3
        """
        m = re.match(r"^[A-Z]?(\d+(?:\.\d+)*)", text)
        if not m:
            return 1
        parts = m.group(1).split(".")
        depth = len([p for p in parts if p])  # count non-empty parts
        return min(depth, 3)  # cap at H3

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
                    is_bold = bool(flags & 16)
                    stripped = text.strip()

                    # Detect headings by font size
                    # Filter: must be >= min_heading_length and not noise
                    is_heading_candidate = (
                        len(stripped) >= self.profile.min_heading_length
                        and not self._heading_noise_re.match(stripped)
                    )

                    heading_applied = False
                    if is_heading_candidate:
                        if font_size > self.profile.font_thresholds.h1:
                            text = f"# {text}"
                            heading_applied = True
                        elif font_size > self.profile.font_thresholds.h2:
                            text = f"## {text}"
                            heading_applied = True
                        elif font_size > self.profile.font_thresholds.h3:
                            text = f"### {text}"
                            heading_applied = True

                    # Strategy 2: Bold numbered section headings
                    # (catches double-column papers where headings are same
                    #  font size as body text, just bold)
                    if not heading_applied and is_bold and is_heading_candidate:
                        if self._numbered_section_re.match(stripped):
                            level = self._section_level_from_number(stripped)
                            prefix = "#" * min(level + 1, 4)  # +1 since title is H1/H2
                            text = f"{prefix} {text}"
                            heading_applied = True
                        elif stripped.lower() in self.profile.section_keywords:
                            text = f"## {text}"
                            heading_applied = True

                    # Detect bold (flag bit 2^4 = 16)
                    if is_bold and not heading_applied:
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
                        logger.debug(
                            "Image extraction failed on page %d",
                            page_num,
                            exc_info=True,
                        )
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
                    logger.debug("Vector graphics extraction failed", exc_info=True)

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
                    logger.debug("Region detection failed", exc_info=True)

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
            bbox = r if bbox is None else bbox | r

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
                logger.debug("Cluster rendering failed", exc_info=True)
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
                        logger.debug("Table region rendering failed", exc_info=True)
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
        return bool(variance > 100)  # Threshold for "interesting" content

    def _overlaps_existing_images(
        self, bbox: fitz.Rect, existing_images: list[dict]
    ) -> bool:
        """
        Check if a bounding box overlaps significantly with existing images.
        Used to avoid duplicate extractions.

        Overlap threshold: >50% of smaller area means significant overlap.
        """
        if not existing_images:
            return False

        new_area = bbox.width * bbox.height
        if new_area <= 0:
            return False

        for img in existing_images:
            # Check if existing image has bbox info
            if "bbox" not in img:
                # XObject images don't have bbox, skip overlap check for them
                continue

            existing_bbox = img["bbox"]
            # Handle both fitz.Rect and tuple/list formats
            if isinstance(existing_bbox, (list, tuple)):  # noqa: UP038
                existing_bbox = fitz.Rect(existing_bbox)

            # Calculate intersection
            intersection = bbox & existing_bbox
            if intersection.is_empty:
                continue

            intersection_area = intersection.width * intersection.height
            existing_area = existing_bbox.width * existing_bbox.height

            # Overlap ratio based on smaller of the two areas
            min_area = min(new_area, existing_area)
            if min_area > 0 and intersection_area / min_area > 0.5:
                return True

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

    def get_toc(self, pdf_path: Path) -> list[tuple[int, str, int]]:
        """
        Get PDF built-in Table of Contents (bookmark outline).

        Returns:
            List of (level, title, page_number) tuples.
            Much more reliable than font-size heuristics.
        """
        doc = fitz.open(str(pdf_path))
        try:
            toc: list[tuple[int, str, int]] = (
                doc.get_toc()
            )  # [(level, title, page), ...]
            return toc
        finally:
            doc.close()

    def get_title(self, pdf_path: Path) -> str:
        """
        Get document title from PDF metadata.

        Returns:
            Title string, or empty string if not available.
        """
        meta = self.get_metadata(pdf_path)
        return (meta.get("title") or "").strip()

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
                                try:
                                    df = tab.to_pandas()
                                    markdown = df.to_markdown(index=False)
                                    row_count = len(df)
                                    col_count = len(df.columns)
                                except Exception:
                                    # Fallback when tabulate is missing
                                    markdown = self._table_to_markdown(tab)
                                    row_count = getattr(tab, "row_count", 0)
                                    col_count = getattr(tab, "col_count", 0)
                            else:
                                # Fallback: extract cells manually
                                markdown = self._table_to_markdown(tab)
                                row_count = getattr(tab, "row_count", 0)
                                col_count = getattr(tab, "col_count", 0)

                            # Filter noise tables (empty or single-column)
                            if (
                                row_count < self.profile.filters.min_table_rows
                                or col_count < self.profile.filters.min_table_cols
                            ):
                                table_index -= 1  # Don't count filtered tables
                                continue

                            # Detect caption from text near the table
                            caption = self._detect_table_caption(page, tab, table_index)

                            tables.append(
                                {
                                    "id": f"tab_{table_index}",
                                    "page": page_num + 1,
                                    "markdown": markdown,
                                    "caption": caption,
                                    "row_count": row_count,
                                    "col_count": col_count,
                                    "preview": markdown[:100] if markdown else "",
                                    "has_header": True,
                                    "source": "pymupdf",
                                }
                            )
                        except Exception:
                            logger.debug("Table cell extraction failed", exc_info=True)
                            continue

                except Exception:
                    # find_tables() may not be available in older versions
                    logger.debug(
                        "find_tables() failed on page %d", page_num, exc_info=True
                    )
                    continue

        finally:
            doc.close()

        return tables

    def _detect_table_caption(
        self, page: fitz.Page, table: Any, table_index: int
    ) -> str:
        """
        Detect table caption from text above or below the table.

        Searches for patterns like 'Table 1. ...', 'Table 2: ...' etc.
        in a region above/below the table bounding box.
        """
        if not hasattr(table, "bbox"):
            return ""

        bbox = table.bbox
        page_h = page.rect.height
        margin = 80  # pixels to search above/below

        # Search above first (most common position)
        above = fitz.Rect(
            max(0, bbox[0] - 50),
            max(0, bbox[1] - margin),
            min(page.rect.width, bbox[2] + 50),
            bbox[1],
        )
        # Then below
        below = fitz.Rect(
            max(0, bbox[0] - 50),
            bbox[3],
            min(page.rect.width, bbox[2] + 50),
            min(page_h, bbox[3] + margin),
        )

        for region in (above, below):
            text = page.get_text("text", clip=region).strip()
            if not text:
                continue
            match = self._table_caption_re.search(text)
            if match:
                cap_num = match.group(1)
                # Reject implausible table numbers (e.g. "Table 34733")
                if int(cap_num) > self.profile.filters.max_caption_number:
                    continue
                cap_text = match.group(2).strip()
                # Take first line only (caption may bleed into body text)
                cap_text = cap_text.split("\n")[0].rstrip(".")
                return f"Table {cap_num}. {cap_text}".strip()

        return ""

    def extract_figure_captions(self, pdf_path: Path) -> dict[int, list[dict]]:
        """
        Extract figure captions from all pages.

        Returns:
            Dict mapping page number (1-indexed) to list of caption dicts:
            [{"number": "1", "caption": "Figure 1. Description..."}]
        """
        doc = fitz.open(str(pdf_path))
        captions: dict[int, list[dict]] = {}

        try:
            for page_num, page in enumerate(doc):
                text = page.get_text("text")
                matches = self._figure_caption_re.finditer(text)
                page_captions: list[dict] = []
                seen_numbers: set[str] = set()  # dedup by figure number
                for m in matches:
                    fig_num = m.group(1)
                    # Reject implausible figure numbers
                    if int(fig_num) > self.profile.filters.max_caption_number:
                        continue
                    # Dedup: keep only the first occurrence of each figure number per page
                    if fig_num in seen_numbers:
                        continue
                    fig_text = m.group(2).strip().split("\n")[0].rstrip(".")
                    # Require minimum body length (filter fragments)
                    if len(fig_text) < self.profile.filters.min_caption_body_len:
                        continue
                    seen_numbers.add(fig_num)
                    page_captions.append(
                        {
                            "number": fig_num,
                            "caption": f"Figure {fig_num}. {fig_text}".strip(),
                        }
                    )
                if page_captions:
                    captions[page_num + 1] = page_captions
        finally:
            doc.close()

        return captions

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
