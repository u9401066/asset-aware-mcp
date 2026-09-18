"""Strict PDF packages, source-scoped page records and checked serialization."""

from __future__ import annotations

import io
from typing import Any

import pikepdf
import pymupdf

from src.domain.native_assets import MAX_NATIVE_BYTES
from src.domain.native_pdf import MAX_PDF_PAGES, NativePdfPageLocator
from src.infrastructure.native_pdf_graph import (
    MAX_GRAPH_NODES,
    PdfObjectGraph,
    canonical,
)


class NativePdfPackage:
    def __init__(self, data: bytes):
        if not data or len(data) > MAX_NATIVE_BYTES:
            raise ValueError("PDF input exceeds the native byte limit or is empty")
        try:
            self.pdf = pikepdf.Pdf.open(io.BytesIO(data), attempt_recovery=False)
        except (pikepdf.PdfError, pikepdf.PasswordError) as exc:
            raise ValueError(f"Cannot open native PDF without repair: {exc}") from exc
        self.data = data
        try:
            self._check()
        except Exception:
            self.pdf.close()
            raise

    def _check(self) -> None:
        if self.pdf.is_encrypted:
            raise ValueError("Encrypted PDF requires a separate explicit workflow")
        if not 1 <= len(self.pdf.pages) <= MAX_PDF_PAGES:
            raise ValueError("Native PDF requires 1..2000 pages")
        if len(self.pdf.objects) > MAX_GRAPH_NODES:
            raise ValueError("Native PDF exceeds the object limit")
        if len({page.obj.objgen for page in self.pdf.pages}) != len(self.pdf.pages):
            raise ValueError("Native PDF has duplicate page object identities")
        if self.pdf.get_warnings():
            raise ValueError("Native PDF parser reported warnings; repair separately")

    def __enter__(self) -> NativePdfPackage:
        return self

    def __exit__(self, *args: Any) -> None:
        self.pdf.close()

    def locate(self, locator: NativePdfPageLocator) -> pikepdf.Page:
        if locator.page_index >= len(self.pdf.pages):
            raise ValueError("Native PDF page index does not resolve")
        page = self.pdf.pages[locator.page_index]
        if page.obj.objgen != (locator.object_id, locator.generation):
            raise ValueError("Native PDF page object locator does not match revision")
        return page

    def check_editable(self) -> None:
        if "/Perms" in self.pdf.Root:
            raise ValueError("Signed or permission-certified PDF cannot be edited")
        for obj in self.pdf.objects:
            if isinstance(obj, pikepdf.Dictionary) and (
                obj.get("/Type") == pikepdf.Name.Sig
                or obj.get("/FT") == pikepdf.Name.Sig
                or "/ByteRange" in obj
            ):
                raise ValueError("Signed PDF or signature fields cannot be edited")
        if "/XFA" in self.pdf.Root.get("/AcroForm", {}):
            raise ValueError("XFA forms require an unsupported dynamic-layout workflow")

    def page_map(self) -> dict[tuple[int, int], str]:
        return {
            page.obj.objgen: str(index) for index, page in enumerate(self.pdf.pages)
        }

    def record(self, index: int) -> dict[str, Any]:
        page = self.pdf.pages[index]
        graph = PdfObjectGraph(self.page_map()).describe(page.obj, root_page=True)
        record = {
            "schema_version": "native-pdf-page-v1",
            "locator": {
                "page_index": index,
                "object_id": page.obj.objgen[0],
                "generation": page.obj.objgen[1],
            },
            "label": page.label,
            "media_box": [float(v) for v in page.mediabox],
            "crop_box": [float(v) for v in page.cropbox],
            "rotation": int(page.obj.get("/Rotate", 0)) % 360,
            "user_unit": float(page.obj.get("/UserUnit", 1)),
            "coordinate_systems": {
                "page_boxes": "native PDF user space; bottom-left origin; units scaled by UserUnit",
                "text_blocks": "PyMuPDF unrotated page coordinates in points",
            },
            "native_graph": graph,
            "text_blocks": self._text(index),
            "extraction_scope": "native_text_blocks_and_pdf_object_graph; no_OCR_or_semantic_segmentation",
        }
        if len(canonical(record)) > 16 * 1024 * 1024:
            raise ValueError("Native PDF page representation exceeds 16 MiB")
        return record

    def _text(self, index: int) -> list[Any]:
        with pymupdf.open(stream=self.data, filetype="pdf") as document:
            if document.is_repaired or document.page_count != len(self.pdf.pages):
                raise ValueError(
                    "Independent PDF reader requires repair or disagrees on page count"
                )
            blocks = document[index].get_text(
                "blocks", flags=pymupdf.TEXTFLAGS_BLOCKS & ~pymupdf.TEXT_PRESERVE_IMAGES
            )
            if (
                len(blocks) > 20_000
                or sum(len(b[4].encode("utf-8")) for b in blocks) > 4 * 1024 * 1024
            ):
                raise ValueError("Native PDF text extraction exceeds its limit")
            return [list(block) for block in blocks]


def save_pdf(pdf: pikepdf.Pdf, min_version: str = "") -> bytes:
    if not 1 <= len(pdf.pages) <= MAX_PDF_PAGES:
        raise ValueError("Native PDF output requires 1..2000 pages")
    output = io.BytesIO()
    pdf.save(
        output,
        compress_streams=False,
        stream_decode_level=pikepdf.StreamDecodeLevel.none,
        fix_metadata_version=False,
        deterministic_id=True,
        min_version=min_version,
    )
    if pdf.get_warnings():
        raise ValueError("PDF writer reported warnings; no managed revision committed")
    data = output.getvalue()
    if len(data) > MAX_NATIVE_BYTES:
        raise ValueError("Native PDF output exceeds the byte limit")
    return data
