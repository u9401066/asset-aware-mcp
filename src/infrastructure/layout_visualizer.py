"""Render page overlays from normalized document segmentation data."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import fitz  # type: ignore
from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from src.domain.segmentation import DocumentSegment, DocumentSegmentation

COLOR_BY_TYPE = {
    "Caption": "#ef4444",
    "Formula": "#f97316",
    "List item": "#f59e0b",
    "Page footer": "#84cc16",
    "Page header": "#22c55e",
    "Picture": "#06b6d4",
    "Section header": "#3b82f6",
    "Table": "#8b5cf6",
    "Text": "#64748b",
    "Title": "#ec4899",
}


@dataclass
class LayoutOverlayResult:
    image_base64: str
    width: int
    height: int
    output_path: str | None = None


class LayoutVisualizer:
    """Create a labeled overlay image for a specific document page."""

    def render_page_overlay(
        self,
        doc_dir: Path,
        segmentation: DocumentSegmentation,
        page_number: int,
        *,
        show_labels: bool = True,
        include_reading_order: bool = True,
        output_path: str | None = None,
    ) -> LayoutOverlayResult:
        page_segments = [
            segment
            for segment in segmentation.segments
            if segment.page_number == page_number
        ]
        if not page_segments:
            raise ValueError(f"No segments found for page {page_number}")

        image = self._load_page_image(doc_dir, page_number, page_segments)
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        scale_x = 1.0
        scale_y = 1.0
        original_pdf = doc_dir / "original.pdf"
        if original_pdf.exists():
            pdf = fitz.open(str(original_pdf))
            try:
                page = pdf.load_page(page_number - 1)
                page_width = page.rect.width or image.width
                page_height = page.rect.height or image.height
            finally:
                pdf.close()
            scale_x = image.width / page_width if page_width else 1.0
            scale_y = image.height / page_height if page_height else 1.0

        for segment in page_segments:
            if (
                segment.left is None
                or segment.top is None
                or segment.width is None
                or segment.height is None
            ):
                continue
            left = segment.left * scale_x
            top = segment.top * scale_y
            right = (segment.left + segment.width) * scale_x
            bottom = (segment.top + segment.height) * scale_y
            color = COLOR_BY_TYPE.get(segment.segment_type, "#e11d48")
            draw.rectangle((left, top, right, bottom), outline=color, width=3)
            if show_labels:
                prefix = f"#{segment.reading_order} " if include_reading_order else ""
                label = f"{prefix}{segment.segment_type}"
                if segment.asset_id:
                    label += f" [{segment.asset_id}]"
                self._draw_label(draw, font, label, left, top, color)

        output = io.BytesIO()
        image.save(output, format="PNG")
        image_bytes = output.getvalue()
        target_path: str | None = None
        if output_path:
            target = Path(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(image_bytes)
            target_path = str(target)

        return LayoutOverlayResult(
            image_base64=base64.b64encode(image_bytes).decode("utf-8"),
            width=image.width,
            height=image.height,
            output_path=target_path,
        )

    def _load_page_image(
        self,
        doc_dir: Path,
        page_number: int,
        page_segments: list[DocumentSegment],
    ) -> Image.Image:
        original_pdf = doc_dir / "original.pdf"
        if original_pdf.exists():
            pdf = fitz.open(str(original_pdf))
            try:
                page = pdf.load_page(page_number - 1)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                return Image.frombytes(
                    "RGB",
                    (pixmap.width, pixmap.height),
                    pixmap.samples,
                )
            finally:
                pdf.close()

        width = 1200
        height = 1600
        valid_segments = [
            segment
            for segment in page_segments
            if segment.left is not None
            and segment.top is not None
            and segment.width is not None
            and segment.height is not None
        ]
        if valid_segments:
            width = int(
                max(
                    (segment.left or 0) + (segment.width or 0)
                    for segment in valid_segments
                )
                + 80
            )
            height = int(
                max(
                    (segment.top or 0) + (segment.height or 0)
                    for segment in valid_segments
                )
                + 80
            )
        return Image.new("RGB", (max(width, 800), max(height, 1000)), "white")

    @staticmethod
    def _draw_label(
        draw: ImageDraw.ImageDraw,
        font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
        label: str,
        left: float,
        top: float,
        color: str,
    ) -> None:
        bbox = draw.textbbox((left, top), label, font=font)
        draw.rectangle(
            (bbox[0] - 4, bbox[1] - 2, bbox[2] + 4, bbox[3] + 2),
            fill=color,
        )
        draw.text((left, top), label, fill="white", font=font)
