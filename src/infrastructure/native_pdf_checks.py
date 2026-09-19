"""Verify planned PDF page mutations without trusting writer success alone."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import pikepdf
import pymupdf

from src.infrastructure.native_pdf_graph import PdfObjectGraph, graph_digest
from src.infrastructure.native_pdf_package import NativePdfPackage, save_pdf

if TYPE_CHECKING:
    from src.domain.native_pdf import NativePdfReference


def verify_reference(
    package: NativePdfPackage, reference: NativePdfReference
) -> pikepdf.Page:
    page = package.locate(reference.locator)
    if (
        hashlib.sha256(package.data).hexdigest() != reference.revision
        or graph_digest(package.record(reference.locator.page_index))
        != reference.value_sha256
    ):
        raise ValueError("Stale native PDF page reference")
    return page


def page_graph(page: pikepdf.Page, mapping: dict, ignored: tuple[str, ...] = ()) -> str:
    graph = PdfObjectGraph(mapping).describe(
        page.obj, root_page=True, ignore_root_keys=ignored
    )
    return graph_digest(graph)


def document_graph(
    pdf: pikepdf.Pdf, mapping: dict, *, ignore_forms: bool = False
) -> str:
    excluded = {"/Pages", "/PageLabels"}
    if ignore_forms:
        excluded.add("/AcroForm")
    root = pikepdf.Dictionary({k: v for k, v in pdf.Root.items() if k not in excluded})
    trailer_implementation = {
        "/Root",
        "/Info",
        "/ID",
        "/Size",
        "/Prev",
        "/XRefStm",
        "/Type",
        "/W",
        "/Index",
        "/Length",
        "/Filter",
        "/DecodeParms",
    }
    extras = pikepdf.Dictionary(
        {k: v for k, v in pdf.trailer.items() if k not in trailer_implementation}
    )
    value = pikepdf.Dictionary(
        Catalog=root,
        Info=pdf.trailer.get("/Info", pikepdf.Dictionary()),
        Trailer=extras,
    )
    return graph_digest(PdfObjectGraph(mapping).describe(value))


def render_fingerprint(data: bytes, index: int) -> str:
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        if pdf.is_repaired:
            raise ValueError("Independent PDF reader required repair")
        page = pdf[index]
        scale = min(1.0, 512 / max(page.rect.width, page.rect.height))
        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=True
        )
        return graph_digest(
            {
                "width": pixmap.width,
                "height": pixmap.height,
                "samples_sha256": hashlib.sha256(pixmap.samples).hexdigest(),
            }
        )


def form_snapshot(pdf: pikepdf.Pdf, mapping: dict) -> dict[str, Any]:
    form = pdf.Root.get("/AcroForm", pikepdf.Dictionary())
    return {
        "fields": [
            graph_digest(PdfObjectGraph(mapping).describe(v))
            for v in form.get("/Fields", [])
        ],
        "properties": _form_properties(form, mapping),
    }


def _form_properties(
    value: pikepdf.Object, mapping: dict, depth: int = 0
) -> dict[str, Any]:
    if depth > 20:
        raise ValueError("PDF form properties exceed nesting limit")
    return {
        key: _form_properties(item, mapping, depth + 1)
        if isinstance(item, pikepdf.Dictionary)
        else graph_digest(PdfObjectGraph(mapping).describe(item))
        for key, item in value.items()
        if key != "/Fields" or depth != 0
    }


def check_form_subset(before: dict, after: dict) -> None:
    for key, value in before.items():
        if key not in after:
            raise ValueError("PDF composition removed an existing form property")
        if isinstance(value, dict):
            check_form_subset(value, after[key])
        elif isinstance(value, list):
            if after[key][: len(value)] != value:
                raise ValueError("PDF composition changed existing form fields")
        elif after[key] != value:
            raise ValueError("PDF composition changed an existing form property")


def rebuild_labels(pdf: pikepdf.Pdf, labels: list[str] | None) -> None:
    if labels is None:
        return
    entries = []
    for index, label in enumerate(labels):
        entries.extend([index, pikepdf.Dictionary(P=pikepdf.String(label))])
    pdf.Root.PageLabels = pikepdf.Dictionary(Nums=pikepdf.Array(entries))


def checked_serialization(
    pdf: pikepdf.Pdf, identities: list[str], min_version: str = ""
) -> bytes:
    mapping = {
        page.obj.objgen: identity
        for page, identity in zip(pdf.pages, identities, strict=True)
    }
    expected = [page_graph(p, mapping) for p in pdf.pages]
    document = document_graph(pdf, mapping)
    labels = [p.label for p in pdf.pages]
    data = save_pdf(pdf, min_version)
    with NativePdfPackage(data) as checked:
        if checked.parser_checks:
            raise ValueError(
                "Serialized PDF retains redundant stream length declarations"
            )
        if len(checked.pdf.pages) != len(identities):
            raise ValueError("PDF page count changed during serialization")
        actual_map = {
            p.obj.objgen: key
            for p, key in zip(checked.pdf.pages, identities, strict=True)
        }
        if [page_graph(p, actual_map) for p in checked.pdf.pages] != expected:
            raise ValueError("PDF page graph changed during serialization")
        if (
            document_graph(checked.pdf, actual_map) != document
            or [p.label for p in checked.pdf.pages] != labels
        ):
            raise ValueError("PDF document properties changed during serialization")
    return data
