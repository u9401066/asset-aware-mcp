"""Reference-preserving page and form copying with annotation cycle repair."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pikepdf

from src.infrastructure.native_pdf_checks import page_graph
from src.infrastructure.native_pdf_forms import (
    repair_annotation_links,
    selected_fields,
    verify_copied_fields,
)
from src.infrastructure.native_pdf_package import NativePdfPackage

if TYPE_CHECKING:
    from src.infrastructure.native_pdf_mutation import PdfMutation


def copy_pages(
    plan: PdfMutation,
    key: str,
    items: list,
    data: bytes,
    additions: dict,
    position: int,
) -> None:
    from src.infrastructure.native_pdf_checks import verify_reference

    with NativePdfPackage(data) as source:
        source.check_editable()
        if (
            source.parser_checks
            and "canonicalized_equal_duplicate_stream_lengths" not in plan.repairs
        ):
            plan.repairs.append("canonicalized_equal_duplicate_stream_lengths")
        plan.min_version = max(
            plan.min_version,
            source.pdf.pdf_version,
            key=lambda v: tuple(int(n) for n in v.split(".")),
        )
        pages = [verify_reference(source, ref) for _, ref in items]
        if len({p.obj.objgen for p in pages}) != len(pages):
            raise ValueError("PDF copy batch contains duplicate source pages")
        if "/StructTreeRoot" in source.pdf.Root or "/OCProperties" in source.pdf.Root:
            raise ValueError(
                "PDF copy needs unsupported document-level tagged/layer integration"
            )
        mapping = {
            p.obj.objgen: f"copy:{key}:{ref.locator.page_index}"
            for p, (_, ref) in zip(pages, items, strict=True)
        }
        expected = [page_graph(p, mapping) for p in pages]
        start, fields, field_start = _append_pages(plan, source, pages, items)
        _register_copies(
            plan,
            source,
            items,
            pages,
            expected,
            mapping,
            start,
            data,
            additions,
            position,
        )

        verify_copied_fields(
            source.pdf, plan.pdf, mapping, plan.identities, fields, field_start
        )


def _append_pages(
    plan: PdfMutation, source: NativePdfPackage, pages: list, items: list
) -> tuple[int, list, int]:
    start = len(plan.pdf.pages)
    fields = selected_fields(source.pdf, pages)
    field_start = len(
        plan.pdf.Root.get("/AcroForm", pikepdf.Dictionary()).get("/Fields", [])
    )
    copied = plan.pdf.add_pages_from(
        source.pdf, [ref.locator.page_index for _, ref in items]
    )
    if copied.renamed_fields or copied.partial_fields:
        raise ValueError(
            "PDF form copy would rename fields or include partial field trees"
        )
    if copied.renamed_dests or copied.dropped_dests or copied.named_dests_added:
        raise ValueError(
            "PDF named destination copying needs explicit document-level integration"
        )
    if repair_annotation_links(pages, list(plan.pdf.pages)[start:]):
        plan.repairs.append("relinked_copied_annotation_backreferences")
    return start, fields, field_start


def _register_copies(
    plan: PdfMutation,
    source: NativePdfPackage,
    items: list,
    pages: list,
    expected: list,
    mapping: dict,
    start: int,
    data: bytes,
    additions: dict,
    position: int,
) -> None:
    for offset, ((slot, ref), page) in enumerate(zip(items, pages, strict=True)):
        target = plan.pdf.pages[start + offset]
        additions[slot] = target
        plan.identities[target.obj.objgen] = mapping[page.obj.objgen]
        plan.imports[target.obj.objgen] = (
            data,
            ref.locator.page_index,
            expected[offset],
        )
        if "/PageLabels" in source.pdf.Root:
            if plan.labels is None:
                plan.labels = {
                    p.obj.objgen: str(p.label)
                    for p in plan.pdf.pages
                    if p.obj.objgen in plan.originals
                }
            plan.labels[target.obj.objgen] = str(page.label)
        plan.changes.append(
            {
                "operation": "copy_page",
                "position": position + slot,
                "source_reference": ref.model_dump(),
                "document_metadata_imported": False,
            }
        )
