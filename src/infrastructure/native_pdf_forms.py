"""Preserve copied form registration and repair known annotation backreferences."""

from __future__ import annotations

import pikepdf

from src.infrastructure.native_pdf_checks import _form_properties, check_form_subset
from src.infrastructure.native_pdf_graph import PdfObjectGraph, graph_digest


def selected_fields(pdf: pikepdf.Pdf, pages: list) -> list:
    widgets = {
        a.objgen
        for p in pages
        for a in p.obj.get("/Annots", [])
        if a.get("/Subtype") == pikepdf.Name.Widget
    }
    return [
        field
        for field in pdf.Root.get("/AcroForm", pikepdf.Dictionary()).get("/Fields", [])
        if _contains_widget(field, widgets)
    ]


def _contains_widget(field: pikepdf.Object, widgets: set) -> bool:
    pending, seen = [field], set()
    while pending:
        item = pending.pop()
        if item.objgen in seen:
            continue
        seen.add(item.objgen)
        if len(seen) > 50_000:
            raise ValueError("PDF form tree exceeds its object limit")
        if item.objgen in widgets:
            return True
        pending.extend(item.get("/Kids", []))
    return False


def verify_copied_fields(
    source: pikepdf.Pdf,
    target: pikepdf.Pdf,
    source_map: dict,
    target_map: dict,
    fields: list,
    start: int,
) -> None:
    actual: list[pikepdf.Object] = list(
        target.Root.get("/AcroForm", pikepdf.Dictionary()).get("/Fields", [])
    )[start:]
    expected = [graph_digest(PdfObjectGraph(source_map).describe(f)) for f in fields]
    if [
        graph_digest(PdfObjectGraph(target_map).describe(f)) for f in actual
    ] != expected:
        raise ValueError("PDF copied form fields are missing, detached or changed")
    if fields:
        check_form_subset(
            _form_properties(source.Root.AcroForm, source_map),
            _form_properties(target.Root.AcroForm, target_map),
        )


def repair_annotation_links(source_pages: list, target_pages: list) -> bool:
    pairs, targets = [], {}
    repaired = False
    for source, target in zip(source_pages, target_pages, strict=True):
        old = source.obj.get("/Annots", [])
        new = target.obj.get("/Annots", [])
        if len(old) != len(new):
            raise ValueError("PDF copying changed the annotation inventory")
        for original, copied in zip(old, new, strict=True):
            if original.objgen in targets:
                raise ValueError("PDF copying cannot duplicate a shared annotation")
            pairs.append((original, copied))
            targets[original.objgen] = copied
    for original, copied in pairs:
        for key in ("/Popup", "/Parent", "/IRT"):
            reference = original.get(key)
            if reference is not None and reference.objgen in targets:
                target = targets[reference.objgen]
                if copied.get(key) is None or copied[key].objgen != target.objgen:
                    copied[key] = target
                    repaired = True
    return repaired
