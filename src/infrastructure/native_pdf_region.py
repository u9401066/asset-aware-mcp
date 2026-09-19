"""Render a displayed-page fraction rectangle without mutating PDF geometry."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import pymupdf

from src.infrastructure.native_pdf_package import NativePdfPackage

if TYPE_CHECKING:
    from src.domain.native_pdf import NativePdfPageLocator
    from src.domain.native_pdf_region import NativePdfRegionSelector


def render_region(
    data: bytes,
    locator: NativePdfPageLocator,
    selector: NativePdfRegionSelector,
    width: int,
) -> dict[str, Any]:
    if not 64 <= width <= 2048:
        raise ValueError("PDF region render dimension must be 64..2048 pixels")
    with NativePdfPackage(data) as package:
        package.locate(locator)
    with pymupdf.open(stream=data, filetype="pdf") as document:
        if document.is_repaired:
            raise ValueError("PDF region rendering requires repair")
        page = document[locator.page_index]
        viewport = page.rect
        if (
            not all(math.isfinite(v) for v in viewport)
            or viewport.is_empty
            or viewport.is_infinite
        ):
            raise ValueError("PDF region has invalid displayed page geometry")
        left, top, right, bottom = selector.rect
        clip = pymupdf.Rect(
            viewport.x0 + left * viewport.width,
            viewport.y0 + top * viewport.height,
            viewport.x0 + right * viewport.width,
            viewport.y0 + bottom * viewport.height,
        )
        # Use the renderer's effective coordinate precision before deriving zoom.
        clip.transform(pymupdf.Identity)
        if clip.is_empty or clip.is_infinite or not all(math.isfinite(v) for v in clip):
            raise ValueError("PDF region is too small or has invalid geometry")
        scale = width / max(clip.width, clip.height)
        matrix = pymupdf.Matrix(scale, scale)
        scaled = clip * matrix
        if not all(math.isfinite(v) and abs(v) <= 2**30 for v in scaled):
            raise ValueError("PDF region exceeds bounded rendering coordinates")
        pixels = scaled.irect
        if not 1 <= pixels.width <= width + 2 or not 1 <= pixels.height <= width + 2:
            raise ValueError("PDF region pixel bounds exceed the render budget")
        pixmap = page.get_pixmap(
            matrix=matrix, clip=clip, colorspace=pymupdf.csRGB, alpha=False, annots=True
        )
        if tuple(pixmap.irect) != tuple(pixels):
            raise ValueError("PDF renderer disagrees with the requested region bounds")
        png = bytes(pixmap.tobytes("png"))
        if len(png) > 3 * 1024 * 1024:
            raise ValueError(
                "PDF region exceeds image limit; request a smaller render_size"
            )
        return {
            "image_png": png,
            "rendering": {
                "renderer": {"name": "PyMuPDF", "version": pymupdf.VersionBind},
                "display_page_rect_points": list(viewport),
                "display_region_rect_points": list(clip),
                "rotation": page.rotation,
                "requested_render_size": width,
                "pixel_rect": list(pixels),
                "pixel_width": pixmap.width,
                "pixel_height": pixmap.height,
                "annotations": "included",
                "limitations": "Static rendering with installed renderer/fonts; no OCR or semantic review. Partial scan resampling can differ from a full-page raster crop. Preview pixels are not the region reference identity.",
            },
        }
