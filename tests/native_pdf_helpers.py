"""Mixed native PDF fixtures with independent text, pixels and dependencies."""

from __future__ import annotations

import io

import pikepdf
import pymupdf
from PIL import Image


def build_pdf(*, links=False, forms=False, labels=False):
    image = io.BytesIO()
    Image.new("RGB", (12, 9), (20, 170, 80)).save(image, format="PNG")
    with pymupdf.open() as document:
        for i in range(3):
            page = document.new_page(width=400, height=500)
            page.insert_text((40, 50), f"Native page {i + 1}: 003 / 18 / 12.5%")
            page.draw_rect(
                pymupdf.Rect(50, 80, 200, 150),
                color=(0.2, 0.4, 0.6),
                fill=(0.9, 0.8, 0.7),
            )
            page.add_text_annot((250, 80), f"Keep annotation {i}").update()
            page.insert_image(pymupdf.Rect(260, 300, 380, 390), stream=image.getvalue())
        document[1].set_rotation(90)
        document[2].set_cropbox(pymupdf.Rect(10, 20, 390, 480))
        if links:
            document[0].insert_link(
                {
                    "kind": pymupdf.LINK_GOTO,
                    "from": pymupdf.Rect(30, 30, 180, 65),
                    "page": 1,
                }
            )
            document.set_toc([[1, "Second page", 2]])
        if forms:
            widget = pymupdf.Widget()
            widget.field_name = "KeepField"
            widget.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
            widget.field_value = "preserved value"
            widget.rect = pymupdf.Rect(50, 200, 250, 240)
            document[0].add_widget(widget)
        if labels:
            document.set_page_labels(
                [{"startpage": 0, "prefix": "A-", "style": "r", "firstpagenum": 2}]
            )
        document.set_metadata({"title": "Preserve this metadata", "author": "Fixture"})
        document.embfile_add("original.txt", b"exact attachment\n")
        return document.tobytes()


def rewrite(data, change):
    with pikepdf.Pdf.open(io.BytesIO(data)) as pdf:
        change(pdf)
        output = io.BytesIO()
        pdf.save(
            output,
            compress_streams=False,
            stream_decode_level=pikepdf.StreamDecodeLevel.none,
            fix_metadata_version=False,
        )
        return output.getvalue()


def pixels(data):
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        return [
            (p.get_pixmap().width, p.get_pixmap().height, p.get_pixmap().samples)
            for p in pdf
        ]


def page_reference(data, index, asset_id="file_" + "a" * 32):
    import hashlib

    from src.domain.native_pdf import NativePdfPageLocator, NativePdfReference
    from src.infrastructure.native_pdf import NativePdf
    from src.infrastructure.native_pdf_graph import graph_digest

    adapter = NativePdf()
    locator = NativePdfPageLocator.model_validate(
        adapter.inspect(data)["pages"][index]["locator"]
    )
    record = adapter.read_page(data, locator)
    return NativePdfReference(
        asset_id=asset_id,
        revision=hashlib.sha256(data).hexdigest(),
        locator=locator,
        value_sha256=graph_digest(record),
    )
