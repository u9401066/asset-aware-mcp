"""Generate bounded form appearances separately from source PDF page content."""

from __future__ import annotations

import html
import io
from typing import TYPE_CHECKING, Any

import pikepdf
import pymupdf

from src.infrastructure.native_pdf_graph import PdfObjectGraph, graph_digest

if TYPE_CHECKING:
    from src.domain.native_pdf_fields import PdfFieldStyle


def _text(
    page: Any, rect: Any, text: str, style: PdfFieldStyle, *, multiline: bool = False
) -> None:
    if not text:
        return
    color = "#" + "".join(f"{round(v * 255):02x}" for v in style.text_color)
    css = (
        "* { margin:0; padding:0; } body { font-family:sans-serif;"
        f"font-size:{style.font_size}pt;color:{color};"
        f"text-align:{('left', 'center', 'right')[style.alignment]};"
        f"white-space:{'pre-wrap' if multiline else 'pre'}; }}"
    )
    spare, _ = page.insert_htmlbox(
        rect,
        "<body>" + html.escape(text).replace("\n", "<br>") + "</body>",
        css=css,
        scale_low=1,
    )
    if spare < 0:
        raise ValueError(
            "PDF field text does not fit the requested bounds and font size"
        )


def _check_text(page: Any) -> None:
    for span in page.get_texttrace():
        for _codepoint, glyph, _, bbox in span["chars"]:
            if glyph == 0:
                raise ValueError("PDF field appearance contains an unsupported glyph")
            bounds = pymupdf.Rect(bbox)
            if (
                bounds.x0 < -0.1
                or bounds.y0 < -0.1
                or bounds.x1 > page.rect.width + 0.1
                or bounds.y1 > page.rect.height + 0.1
            ):
                raise ValueError("PDF field appearance text exceeds its widget bounds")


class FieldAppearanceFactory:
    def __init__(self, pdf: pikepdf.Pdf):
        self.pdf = pdf
        self.fonts: dict[str, pikepdf.Object] = {}
        mapping = {page.obj.objgen: str(index) for index, page in enumerate(pdf.pages)}
        for obj in pdf.objects:
            if (
                isinstance(obj, pikepdf.Dictionary)
                and obj.get("/Type") == pikepdf.Name.Font
            ):
                digest = graph_digest(PdfObjectGraph(mapping).describe(obj))
                self.fonts.setdefault(digest, obj)

    def create(
        self,
        rectangle: list[float],
        style: PdfFieldStyle,
        *,
        user_unit: float = 1,
        rotation: int = 0,
        text: str = "",
        choices: list[tuple[str, bool]] | None = None,
        comb: int | None = None,
        multiline: bool = False,
        checked: bool | None = None,
        radio: bool = False,
    ) -> tuple[pikepdf.Object, pikepdf.Object | None]:
        width, height = rectangle[2] - rectangle[0], rectangle[3] - rectangle[1]
        if (
            width <= 0
            or height <= 0
            or user_unit <= 0
            or rotation not in {0, 90, 180, 270}
        ):
            raise ValueError(
                "PDF field appearance requires finite positive native geometry"
            )
        logical_w, logical_h = (height, width) if rotation % 180 else (width, height)
        w, h = logical_w * user_unit, logical_h * user_unit
        if not 1 <= w <= 20_000 or not 1 <= h <= 20_000:
            raise ValueError("PDF field appearance dimensions exceed rendering bounds")
        with pymupdf.open() as doc:
            page = doc.new_page(width=w, height=h)
            border = style.border_width / 2
            frame = pymupdf.Rect(border, border, w - border, h - border)
            if frame.is_empty:
                raise ValueError("PDF field border exceeds its widget bounds")
            border_color = style.border_color if style.border_width else None
            if radio and (border_color is not None or style.fill_color is not None):
                page.draw_oval(
                    frame,
                    color=border_color,
                    fill=style.fill_color,
                    width=style.border_width,
                )
            elif border_color is not None or style.fill_color is not None:
                page.draw_rect(
                    frame,
                    color=border_color,
                    fill=style.fill_color,
                    width=style.border_width,
                )
            pad = max(2, style.border_width + 1)
            inner = pymupdf.Rect(pad, pad, w - pad, h - pad)
            if inner.is_empty:
                raise ValueError("PDF field has no space inside its border")
            if checked:
                if radio:
                    page.draw_oval(inner, color=style.text_color, fill=style.text_color)
                else:
                    page.draw_polyline(
                        [(pad, h / 2), (w * 0.4, h - pad), (w - pad, pad)],
                        color=style.text_color,
                        width=max(1, style.border_width),
                    )
            elif checked is None:
                if comb is not None:
                    if not 1 <= comb <= 4096 or len(text) > comb:
                        raise ValueError(
                            "PDF comb field requires a bounded valid MaxLen"
                        )
                    step = inner.width / comb
                    centered = style.model_copy(update={"alignment": 1})
                    for index, char in enumerate(text):
                        cell = pymupdf.Rect(
                            inner.x0 + step * index,
                            inner.y0,
                            inner.x0 + step * (index + 1),
                            inner.y1,
                        )
                        _text(page, cell, char, centered)
                elif choices is None:
                    _text(page, inner, text, style, multiline=multiline)
                else:
                    row_height = style.font_size * 1.6
                    for index, (label, selected) in enumerate(choices):
                        top = pad + index * row_height
                        if top + row_height > h - pad:
                            break  # Native scrollable list; off-screen options stay in Opt.
                        row = pymupdf.Rect(pad, top, w - pad, top + row_height)
                        if selected:
                            page.draw_rect(row, color=None, fill=(0.75, 0.85, 1))
                        _text(page, row, label, style)
                    if choices and row_height > inner.height:
                        raise ValueError(
                            "PDF choice widget cannot display one complete option"
                        )
            _check_text(page)
            if checked is None and not page.get_fonts():
                page.insert_font(fontname="helv")
            raw = doc.tobytes()
        with pikepdf.Pdf.open(io.BytesIO(raw), attempt_recovery=False) as generated:
            content = self.pdf.copy_foreign(generated.pages[0].as_form_xobject())
        default_font = self._deduplicate_fonts(content)
        scale = 1 / user_unit
        matrix = {
            0: (scale, 0, 0, scale, 0, 0),
            90: (0, scale, -scale, 0, width, 0),
            180: (-scale, 0, 0, -scale, width, height),
            270: (0, -scale, scale, 0, 0, height),
        }[rotation]
        operators = " ".join(format(v, ".10g") for v in matrix)
        appearance = self.pdf.make_stream(f"q {operators} cm /Content Do Q".encode())
        appearance.Type = pikepdf.Name.XObject
        appearance.Subtype = pikepdf.Name.Form
        appearance.BBox = pikepdf.Array([0, 0, width, height])
        appearance.Resources = pikepdf.Dictionary(
            XObject=pikepdf.Dictionary(Content=content)
        )
        return appearance, default_font

    def _deduplicate_fonts(self, obj: pikepdf.Object) -> pikepdf.Object | None:
        first = None
        resources = obj.get("/Resources", pikepdf.Dictionary())
        fonts = resources.get("/Font", pikepdf.Dictionary())
        for key, font in list(fonts.items()):
            digest = graph_digest(PdfObjectGraph({}).describe(font))
            if digest in self.fonts:
                fonts[key] = self.fonts[digest]
            else:
                self.fonts[digest] = font
            if first is None:
                first = fonts[key]
        for _, child in resources.get("/XObject", pikepdf.Dictionary()).items():  # noqa: PERF102 -- pikepdf has no values() API
            if child.get("/Subtype") == pikepdf.Name.Form:
                nested = self._deduplicate_fonts(child)
                if first is None:
                    first = nested
        return first
