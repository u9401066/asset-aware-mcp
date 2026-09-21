"""Build annotation appearances in a disposable PDF, never rewriting source pages."""

from __future__ import annotations

import html
import io
from typing import TYPE_CHECKING

import pikepdf
import pymupdf

from src.infrastructure.native_pdf_package import save_pdf

if TYPE_CHECKING:
    from src.domain.native_pdf_annotations import PdfAnnotationAppearance


def _rotation(page: pikepdf.Page) -> int:
    node: pikepdf.Object = page.obj
    seen = set()
    for _ in range(100):
        if "/Rotate" in node:
            angle = int(node.Rotate)
            if angle % 90:
                raise ValueError("PDF annotation page has non-orthogonal rotation")
            return angle % 360
        if "/Parent" not in node:
            return 0
        node = node.Parent
        if node.objgen in seen:
            raise ValueError("PDF page inheritance contains a cycle")
        seen.add(node.objgen)
    raise ValueError("PDF page inheritance exceeds the depth limit")


def appearance_pdf(source: pikepdf.Page, spec: PdfAnnotationAppearance) -> bytes:
    """Use identical native boxes, rotation and user unit for coordinate conversion."""
    with pikepdf.Pdf.new() as blank:
        page = blank.add_blank_page()
        page.obj.MediaBox = pikepdf.Array(list(source.mediabox))
        page.obj.CropBox = pikepdf.Array(list(source.cropbox))
        page.obj.Rotate = _rotation(source)
        page.obj.UserUnit = source.obj.get("/UserUnit", 1)
        data = save_pdf(blank)
    with pymupdf.open(stream=data, filetype="pdf") as document:
        page = document[0]
        angle = page.rotation
        # Work on the disposable unrotated page: rotated convenience matrices do
        # not include the crop origin / UserUnit needed for native coordinates.
        page.set_rotation(0)
        bounds = page.rect
        if bounds.is_empty or bounds.is_infinite:
            raise ValueError("PDF annotation page has invalid displayed bounds")

        def point(value: list[float]) -> pymupdf.Point:
            x, y = value
            u, v = {0: (x, y), 90: (y, 1 - x), 180: (1 - x, 1 - y), 270: (1 - y, x)}[
                angle
            ]
            return pymupdf.Point(u * bounds.width, v * bounds.height)

        rect = (
            pymupdf.Rect(point(spec.rect[:2]), point(spec.rect[2:])).normalize()
            if spec.rect
            else None
        )
        if spec.kind == "Text":
            assert spec.point is not None
            annotation = page.add_text_annot(point(spec.point), "", icon=spec.icon)
        elif spec.kind == "FreeText":
            assert rect is not None
            color = "#" + "".join(f"{round(c * 255):02x}" for c in spec.text_color)
            annotation = page.add_freetext_annot(
                rect,
                html.escape(spec.text).replace("\n", "<br>"),
                richtext=True,
                style=f"font-family:sans-serif;font-size:{spec.font_size}pt;color:{color};white-space:pre-wrap",
                border_color=spec.stroke_color,
                border_width=spec.border_width,
                fill_color=spec.fill_color,
                opacity=spec.opacity,
                rotate=angle,
            )
        elif spec.kind in {"Square", "Circle"}:
            assert rect is not None
            annotation = (
                page.add_rect_annot(rect)
                if spec.kind == "Square"
                else page.add_circle_annot(rect)
            )
        elif spec.kind == "Line":
            annotation = page.add_line_annot(*[point(p) for p in spec.vertices])
        elif spec.kind in {"Polygon", "PolyLine"}:
            create = (
                page.add_polygon_annot
                if spec.kind == "Polygon"
                else page.add_polyline_annot
            )
            annotation = create([point(p) for p in spec.vertices])
        elif spec.kind == "Ink":
            annotation = page.add_ink_annot(
                [[tuple(point(p)) for p in stroke] for stroke in spec.strokes]
            )
        else:
            quads = [
                pymupdf.Quad([point(q[i : i + 2]) for i in range(0, 8, 2)])
                for q in spec.quads
            ]
            if any(not q.is_convex for q in quads):
                raise ValueError(
                    "Text markup requires convex nondegenerate quads in UL/UR/LL/LR order"
                )
            annotation = {
                "Highlight": page.add_highlight_annot,
                "Underline": page.add_underline_annot,
                "StrikeOut": page.add_strikeout_annot,
                "Squiggly": page.add_squiggly_annot,
            }[spec.kind](quads)
        if spec.kind != "FreeText":
            annotation.set_colors(stroke=spec.stroke_color, fill=spec.fill_color)
            if spec.kind in {"Square", "Circle", "Line", "PolyLine", "Polygon", "Ink"}:
                annotation.set_border(width=spec.border_width)
            annotation.update(opacity=spec.opacity)
        page.set_rotation(angle)
        result = bytes(document.tobytes())
    # Contents must remain literal text, not the rich-text appearance markup.
    if spec.kind == "FreeText":
        with pikepdf.Pdf.open(io.BytesIO(result)) as generated:
            generated.pages[0].obj.Annots[0].Contents = pikepdf.String(spec.text)
            result = save_pdf(generated)
    return result
