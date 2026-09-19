"""PDF page CRUD through identity-preserving QPDF edits and independent readback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pikepdf
import pymupdf

from src.domain.native_pdf import MAX_PDF_BATCH, MAX_PDF_PAGES
from src.infrastructure.native_pdf_checks import verify_reference
from src.infrastructure.native_pdf_graph import canonical
from src.infrastructure.native_pdf_mutation import PdfMutation, insert_pages
from src.infrastructure.native_pdf_package import NativePdfPackage
from src.infrastructure.native_pdf_region import render_region

if TYPE_CHECKING:
    from src.domain.native_assets import NativeEditResult
    from src.domain.native_pdf import (
        NativePdfCreate,
        NativePdfInsert,
        NativePdfPageEdit,
        NativePdfPageLocator,
        NativePdfReference,
    )


def _targets(
    package: NativePdfPackage,
    references: list[NativePdfReference],
    limit: int = MAX_PDF_BATCH,
) -> list[pikepdf.Page]:
    if not 1 <= len(references) <= limit:
        raise ValueError("PDF page target batch is empty or exceeds its limit")
    pages = [verify_reference(package, ref) for ref in references]
    if len({p.obj.objgen for p in pages}) != len(pages):
        raise ValueError("PDF operation contains duplicate page targets")
    return pages


class NativePdf:
    render_region = staticmethod(render_region)

    def decompose(self, data: bytes) -> list[dict[str, Any]]:
        from src.domain.native_pdf import NativePdfPageLocator

        result, size = [], len(data)
        with NativePdfPackage(data) as package:
            for index in range(len(package.pdf.pages)):
                record = package.record(index)
                locator = NativePdfPageLocator.model_validate(record["locator"])
                png = self.render(data, locator, 768)
                size += len(canonical(record)) + len(png)
                if size > 96 * 1024 * 1024:
                    raise ValueError(
                        "Native PDF decomposition exceeds its output budget"
                    )
                result.append({"record": record, "png": png})
        return result

    def inspect(self, data: bytes) -> dict[str, Any]:
        with NativePdfPackage(data) as package:
            return {
                "page_count": len(package.pdf.pages),
                "pdf_version": package.pdf.pdf_version,
                "pages": [
                    {
                        "locator": {
                            "page_index": i,
                            "object_id": p.obj.objgen[0],
                            "generation": p.obj.objgen[1],
                        },
                        "label": p.label,
                        "media_box": [float(v) for v in p.mediabox],
                        "crop_box": [float(v) for v in p.cropbox],
                        "rotation": int(p.obj.get("/Rotate", 0)) % 360,
                    }
                    for i, p in enumerate(package.pdf.pages)
                ],
            }

    def read_page(self, data: bytes, locator: NativePdfPageLocator) -> dict[str, Any]:
        with NativePdfPackage(data) as package:
            package.locate(locator)
            return package.record(locator.page_index)

    def create(
        self, request: NativePdfCreate, sources: dict[str, bytes]
    ) -> tuple[bytes, NativeEditResult]:
        with pikepdf.Pdf.new() as pdf:
            plan = PdfMutation(pdf, adding=True)
            insert_pages(plan, request.pages, sources, 0)
            return plan.finish()

    def insert(
        self, data: bytes, request: NativePdfInsert, sources: dict[str, bytes]
    ) -> tuple[bytes, NativeEditResult]:
        with NativePdfPackage(data) as package:
            package.check_editable()
            plan = PdfMutation(package.pdf, data, adding=True)
            if len(package.pdf.pages) + len(request.pages) > MAX_PDF_PAGES:
                raise ValueError("PDF insertion exceeds the page limit")
            insert_pages(plan, request.pages, sources, request.position)
            return plan.finish()

    def delete(
        self, data: bytes, references: list[NativePdfReference]
    ) -> tuple[bytes, NativeEditResult]:
        with NativePdfPackage(data) as package:
            package.check_editable()
            targets = _targets(package, references)
            if len(targets) == len(package.pdf.pages):
                raise ValueError("PDF deletion must retain at least one page")
            plan = PdfMutation(package.pdf, data)
            for ref in sorted(
                references, key=lambda r: r.locator.page_index, reverse=True
            ):
                del package.pdf.pages[ref.locator.page_index]
                plan.changes.append(
                    {"operation": "delete_page", "reference": ref.model_dump()}
                )
            return plan.finish()

    def reorder(
        self, data: bytes, references: list[NativePdfReference]
    ) -> tuple[bytes, NativeEditResult]:
        with NativePdfPackage(data) as package:
            package.check_editable()
            targets = _targets(package, references, MAX_PDF_PAGES)
            if len(targets) != len(package.pdf.pages):
                raise ValueError("PDF reorder must name every page exactly once")
            plan = PdfMutation(package.pdf, data)
            for position, page in enumerate(targets):
                index = next(
                    i
                    for i, p in enumerate(package.pdf.pages)
                    if p.obj.objgen == page.obj.objgen
                )
                del package.pdf.pages[index]
                package.pdf.pages.insert(position, page)
            plan.changes = [
                {
                    "operation": "reorder_page",
                    "position": i,
                    "reference": ref.model_dump(),
                }
                for i, ref in enumerate(references)
            ]
            return plan.finish()

    def edit(
        self, data: bytes, edits: list[NativePdfPageEdit]
    ) -> tuple[bytes, NativeEditResult]:
        with NativePdfPackage(data) as package:
            package.check_editable()
            pages = _targets(package, [edit.reference for edit in edits])
            plan = PdfMutation(package.pdf, data)
            for page, edit in zip(pages, edits, strict=True):
                ignored = tuple(
                    key
                    for key, value in (
                        ("/Rotate", edit.rotation),
                        ("/CropBox", edit.crop_box),
                    )
                    if value is not None
                )
                expected = plan.expect_geometry(page, ignored)
                _geometry(page, edit)
                plan.check_geometry(page, ignored, expected)
                plan.changes.append(
                    {"operation": "update_page_geometry", **edit.model_dump()}
                )
            return plan.finish()

    def render(self, data: bytes, locator: NativePdfPageLocator, width: int) -> bytes:
        if not 64 <= width <= 2048:
            raise ValueError("PDF render dimension must be 64..2048 pixels")
        with NativePdfPackage(data) as package:
            package.locate(locator)
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            if pdf.is_repaired:
                raise ValueError("PDF rendering requires repair")
            page = pdf[locator.page_index]
            scale = width / max(page.rect.width, page.rect.height)
            png = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=True
            ).tobytes("png")
            if len(png) > 3 * 1024 * 1024:
                raise ValueError(
                    "PDF render exceeds image limit; request a smaller dimension"
                )
            return bytes(png)


def _geometry(page: pikepdf.Page, edit: NativePdfPageEdit) -> None:
    if edit.rotation is not None:
        page.obj.Rotate = edit.rotation
    if edit.crop_box is not None:
        media = [float(v) for v in page.mediabox]
        crop = edit.crop_box
        if (
            crop[0] < media[0]
            or crop[1] < media[1]
            or crop[2] > media[2]
            or crop[3] > media[3]
        ):
            raise ValueError("PDF crop box must be inside the media box")
        page.obj.CropBox = pikepdf.Array(crop)
