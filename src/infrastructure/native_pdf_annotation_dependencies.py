"""Reject annotation deletion that leaves references outside the explicit plan."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pikepdf

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.infrastructure.native_pdf_annotations import AnnotationCatalog


def owned_popup(
    catalog: AnnotationCatalog, annotation: pikepdf.Object
) -> pikepdf.Object | None:
    popup = annotation.get("/Popup")
    if popup is None:
        return None
    if (
        not isinstance(popup, pikepdf.Dictionary)
        or not popup.is_indirect
        or popup.get("/Subtype") != pikepdf.Name.Popup
        or not isinstance(popup.get("/Parent"), pikepdf.Dictionary)
        or popup.Parent.objgen != annotation.objgen
        or not annotation.is_indirect
    ):
        raise ValueError("PDF annotation has an unsupported popup ownership graph")
    owners = [loc for loc, obj in catalog.entries if obj.objgen == annotation.objgen]
    locations = [loc for loc, obj in catalog.entries if obj.objgen == popup.objgen]
    if len(owners) != 1 or len(locations) != 1 or locations[0].page != owners[0].page:
        raise ValueError("PDF popup is shared, detached or located on a different page")
    return popup


def require_unreferenced_deletions(
    catalog: AnnotationCatalog,
    deleted: Iterable[pikepdf.Object],
    structural_pages: set[int],
) -> None:
    targets = {obj.objgen for obj in deleted if obj.is_indirect}
    page_ids = {p.obj.objgen for p in catalog.package.pdf.pages}
    arrays = {
        value.objgen
        for index, page in enumerate(catalog.package.pdf.pages)
        if index in structural_pages
        if isinstance(value := page.obj.get("/Annots"), pikepdf.Array)
        and value.is_indirect
    }
    if not targets and not arrays:
        return
    for identity in arrays:
        owners = [
            p
            for p in catalog.package.pdf.pages
            if isinstance(value := p.obj.get("/Annots"), pikepdf.Array)
            and value.objgen == identity
        ]
        if len(owners) != 1:
            raise ValueError("PDF annotation array has a shared page dependency")
    visited_nodes = 0

    def scan(
        value: Any, owner: tuple[int, int], path: tuple = (), depth: int = 0
    ) -> None:
        nonlocal visited_nodes
        visited_nodes += 1
        if depth > 100 or visited_nodes > 500_000:
            raise ValueError("PDF annotation dependency scan exceeds its limit")
        children: list[tuple[str | int, Any]]
        if isinstance(value, (pikepdf.Dictionary, pikepdf.Stream)):
            children = list(value.items())
        elif isinstance(value, pikepdf.Array):
            children = list(enumerate(value))
        else:
            return
        for key, child in children:
            location = (*path, key)
            if isinstance(child, pikepdf.Object) and child.is_indirect:
                if child.objgen in arrays and not (
                    owner in page_ids and location == ("/Annots",)
                ):
                    raise ValueError("PDF annotation array has an external dependency")
                if child.objgen in targets:
                    allowed_page = (
                        owner in page_ids
                        and len(location) == 2
                        and location[0] == "/Annots"
                    )
                    allowed_array = owner in arrays and len(location) == 1
                    if owner not in targets and not allowed_page and not allowed_array:
                        raise ValueError(
                            "PDF annotation deletion leaves an incoming dependency"
                        )
                # Indirect objects are each scanned once via the object inventory.
            else:
                scan(child, owner, location, depth + 1)

    for obj in catalog.package.pdf.objects:
        # Unreachable objects are conservative dependencies too; no silent cleanup.
        scan(obj, obj.objgen)
    scan(catalog.package.pdf.trailer, (-1, -1))
