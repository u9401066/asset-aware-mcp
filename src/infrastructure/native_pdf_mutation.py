"""Native PDF page transactions with retained content and document dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.native_assets import NativeEditResult
from src.infrastructure.native_pdf_checks import (
    check_form_subset,
    checked_serialization,
    document_graph,
    form_snapshot,
    page_graph,
    rebuild_labels,
    render_fingerprint,
)
from src.infrastructure.native_pdf_copy import copy_pages

if TYPE_CHECKING:
    import pikepdf


class PdfMutation:
    def __init__(
        self, pdf: pikepdf.Pdf, data: bytes | None = None, *, adding: bool = False
    ):
        self.pdf = pdf
        self.min_version = pdf.pdf_version
        self.data = data
        self.adding = adding
        self.identities = {
            p.obj.objgen: f"original:{i}" for i, p in enumerate(pdf.pages)
        }
        self.originals = {
            p.obj.objgen: (i, page_graph(p, self.identities))
            for i, p in enumerate(pdf.pages)
        }
        self.document = document_graph(pdf, self.identities, ignore_forms=adding)
        self.forms = form_snapshot(pdf, self.identities)
        self.labels = (
            {p.obj.objgen: str(p.label) for p in pdf.pages}
            if "/PageLabels" in pdf.Root
            else None
        )
        self.geometry: set[tuple[int, int]] = set()
        self.changes: list[dict[str, Any]] = []
        self.repairs: list[str] = []
        self.imports: dict[tuple[int, int], tuple[bytes, int, str]] = {}

    def expect_geometry(self, page: pikepdf.Page, ignored: tuple[str, ...]) -> str:
        self.geometry.add(page.obj.objgen)
        return page_graph(page, self.identities, ignored)

    def check_geometry(
        self, page: pikepdf.Page, ignored: tuple[str, ...], expected: str
    ) -> None:
        if page_graph(page, self.identities, ignored) != expected:
            raise ValueError("PDF page changed outside requested geometry")

    def finish(self) -> tuple[bytes, NativeEditResult]:
        mapping = {p.obj.objgen: self.identities[p.obj.objgen] for p in self.pdf.pages}
        if document_graph(self.pdf, mapping, ignore_forms=self.adding) != self.document:
            raise ValueError("PDF document properties changed outside the page plan")
        if self.adding:
            check_form_subset(self.forms, form_snapshot(self.pdf, mapping))
        for page in self.pdf.pages:
            if (
                page.obj.objgen in self.originals
                and page.obj.objgen not in self.geometry
                and page_graph(page, mapping) != self.originals[page.obj.objgen][1]
            ):
                raise ValueError("PDF mutation changed an existing page graph")
            if (
                page.obj.objgen in self.imports
                and page_graph(page, mapping) != self.imports[page.obj.objgen][2]
            ):
                raise ValueError(
                    "PDF page copy did not preserve its source object graph"
                )
        if self.labels is not None:
            rebuild_labels(
                self.pdf,
                [
                    self.labels.get(p.obj.objgen, str(i + 1))
                    for i, p in enumerate(self.pdf.pages)
                ],
            )
        data = checked_serialization(self.pdf, list(mapping.values()), self.min_version)
        self._check_rendering(data)
        return data, self._report()

    def _check_rendering(self, data: bytes) -> None:
        for index, page in enumerate(self.pdf.pages):
            if page.obj.objgen in self.geometry:
                continue
            if page.obj.objgen in self.originals and self.data is not None:
                source, old_index = self.data, self.originals[page.obj.objgen][0]
            elif page.obj.objgen in self.imports:
                source, old_index, _ = self.imports[page.obj.objgen]
            else:
                continue
            if render_fingerprint(source, old_index) != render_fingerprint(data, index):
                raise ValueError(
                    "PDF page pixels changed in independent 512-pixel readback"
                )

    def _report(self) -> NativeEditResult:
        return NativeEditResult(
            changed_parts=["pdf:page-tree-and-requested-page-properties"],
            preserved_parts=sum(
                p.obj.objgen in self.originals and p.obj.objgen not in self.geometry
                for p in self.pdf.pages
            ),
            changes=self.changes,
            checks=[
                "revision_page_and_representation",
                "remaining_page_dependencies",
                "existing_page_object_graphs",
                "document_properties",
                "serialized_graph_readback",
                "independent_512_pixel_readback_for_unchanged_pages",
            ],
            repairs=self.repairs
            + (["rebuilt_page_labels_for_mapping"] if self.labels is not None else []),
            review_required=[
                "semantic_accuracy",
                "full_resolution_rendering",
                "forms_and_viewer_behavior",
                "logical_reading_order",
                "script_page_indices",
                "accessibility",
            ],
        )


def insert_pages(
    plan: PdfMutation, inputs: list, sources: dict[str, bytes], position: int
) -> None:
    if position > len(plan.pdf.pages):
        raise ValueError("PDF insertion position is outside the page sequence")
    selected: dict[str, list[tuple[int, Any]]] = {}
    additions: dict[int, pikepdf.Page] = {}
    for slot, item in enumerate(inputs):
        if item.blank is not None:
            page = plan.pdf.add_blank_page(
                page_size=(item.blank.width, item.blank.height)
            )
            additions[slot] = page
            plan.identities[page.obj.objgen] = f"blank:{slot}"
            plan.changes.append(
                {"operation": "insert_blank_page", "position": position + slot}
            )
        else:
            ref = item.reference
            selected.setdefault(f"{ref.asset_id}:{ref.revision}", []).append(
                (slot, ref)
            )
    for key, items in selected.items():
        copy_pages(plan, key, items, sources[key], additions, position)
    for slot in sorted(additions):
        page = additions[slot]
        index = next(
            i for i, p in enumerate(plan.pdf.pages) if p.obj.objgen == page.obj.objgen
        )
        del plan.pdf.pages[index]
        plan.pdf.pages.insert(position + slot, page)
