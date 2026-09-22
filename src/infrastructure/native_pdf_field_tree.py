"""Walk raw Fields/Kids without name deduplication or implicit form repairs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pikepdf

from src.domain.native_pdf_annotations import PdfAnnotationLocator
from src.domain.native_pdf_fields import (
    MAX_FIELD_DEPTH,
    MAX_PDF_FIELDS,
    PdfFieldLocator,
)

if TYPE_CHECKING:
    from src.infrastructure.native_pdf_package import NativePdfPackage

# Common, variable-text, text and choice entries marked inheritable by PDF 1.7.
# AA, T, TU, TM, DS and RV are deliberately NOT inherited.
INHERITABLE = ("/FT", "/Ff", "/V", "/DV", "/DA", "/Q", "/MaxLen", "/Opt", "/TI", "/I")
WIDGET_FIELD_KEYS = {
    "/TU",
    "/TM",
    "/Ff",
    "/V",
    "/DV",
    "/MaxLen",
    "/Opt",
    "/TI",
    "/I",
    "/RV",
}


def identity(obj: pikepdf.Object) -> dict[str, int]:
    return {"object_id": obj.objgen[0], "generation": obj.objgen[1]}


@dataclass
class FieldWidget:
    path: tuple[int, ...]
    obj: pikepdf.Object
    occurrences: list[PdfAnnotationLocator]
    issues: list[str] = field(default_factory=list)


@dataclass
class FieldNode:
    locator: PdfFieldLocator
    obj: pikepdf.Object
    ancestors: tuple[FieldNode, ...]
    children: list[FieldNode] = field(default_factory=list)
    widgets: list[FieldWidget] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def inherited(self, key: str) -> tuple[Any, FieldNode | None]:
        for node in (self, *reversed(self.ancestors)):
            if key in node.obj:
                return node.obj[key], node
        return None, None


class FieldTree:
    def __init__(self, package: NativePdfPackage):
        self.package = package
        self.form = package.pdf.Root.get("/AcroForm", pikepdf.Dictionary())
        if not isinstance(self.form, pikepdf.Dictionary):
            raise ValueError("PDF AcroForm is not a dictionary")
        self.nodes: dict[tuple[int, ...], FieldNode] = {}
        self.seen: set[tuple[int, int]] = set()
        self.widget_owners: set[tuple[int, int]] = set()
        self.page_widgets: list[tuple[PdfAnnotationLocator, pikepdf.Object]] = []
        self.widget_pages: dict[tuple[int, int], list[PdfAnnotationLocator]] = {}
        self._scan_pages()
        self.visited = 0
        for index, obj in enumerate(self._array(self.form, "/Fields")):
            self._field(obj, (index,), ())

    @staticmethod
    def _array(obj: pikepdf.Object, key: str) -> pikepdf.Object:
        value = obj.get(key, pikepdf.Array())
        if not isinstance(value, pikepdf.Array):
            raise ValueError(f"PDF form {key} is not an array")
        return value

    def _scan_pages(self) -> None:
        count = 0
        for page_index, page in enumerate(self.package.pdf.pages):
            for index, obj in enumerate(self._array(page.obj, "/Annots")):
                count += 1
                if count > MAX_PDF_FIELDS:
                    raise ValueError("PDF exceeds the annotation catalog limit")
                if not isinstance(obj, pikepdf.Dictionary):
                    raise ValueError(
                        "PDF annotation inventory contains a non-dictionary"
                    )
                if obj.get("/Subtype") != pikepdf.Name.Widget:
                    continue
                locator = PdfAnnotationLocator.model_validate(
                    {
                        "page": {"page_index": page_index, **identity(page.obj)},
                        "annotation_index": index,
                        **identity(obj),
                    }
                )
                self.page_widgets.append((locator, obj))
                if obj.is_indirect:
                    self.widget_pages.setdefault(obj.objgen, []).append(locator)

    def _visit(self, obj: pikepdf.Object, path: tuple[int, ...]) -> None:
        self.visited += 1
        if self.visited > MAX_PDF_FIELDS or len(path) > MAX_FIELD_DEPTH:
            raise ValueError("PDF field tree exceeds its count or depth limit")
        if not isinstance(obj, pikepdf.Dictionary):
            raise ValueError("PDF field tree contains a non-dictionary")
        if obj.is_indirect:
            if obj.objgen in self.seen:
                raise ValueError(
                    "PDF field tree contains a cycle or shared object ownership"
                )
            self.seen.add(obj.objgen)

    @staticmethod
    def _parent_issues(obj: pikepdf.Object, parent: FieldNode | None) -> list[str]:
        linked = obj.get("/Parent")
        if parent is None:
            return ["root_field_has_parent"] if linked is not None else []
        if linked is None:
            return ["missing_parent_link"]
        if not isinstance(linked, pikepdf.Dictionary):
            return ["invalid_parent_link"]
        if not linked.is_indirect or not parent.obj.is_indirect:
            return ["unresolved_direct_parent_identity"]
        return (
            ["parent_link_disagrees_with_tree"]
            if linked.objgen != parent.obj.objgen
            else []
        )

    def _field(
        self,
        obj: pikepdf.Object,
        path: tuple[int, ...],
        ancestors: tuple[FieldNode, ...],
    ) -> FieldNode:
        self._visit(obj, path)
        node = FieldNode(
            PdfFieldLocator(field_path=list(path), **identity(obj)), obj, ancestors
        )
        self.nodes[path] = node
        node.issues.extend(
            self._parent_issues(obj, ancestors[-1] if ancestors else None)
        )
        if not obj.is_indirect:
            node.issues.append("direct_field_identity")
        if "/T" in obj and not isinstance(obj.T, pikepdf.String):
            node.issues.append("invalid_partial_name")
        if obj.get("/Subtype") == pikepdf.Name.Widget:
            node.widgets.append(self._widget(obj, path, None))
        for index, child in enumerate(self._array(obj, "/Kids")):
            child_path = (*path, index)
            if (
                isinstance(child, pikepdf.Dictionary)
                and child.get("/Subtype") == pikepdf.Name.Widget
                and not any(key in child for key in ("/T", "/FT", "/Kids"))
            ):
                self._visit(child, child_path)
                widget = self._widget(child, child_path, node)
                if WIDGET_FIELD_KEYS.intersection(child.keys()):
                    widget.issues.append("widget_has_ambiguous_field_attributes")
                node.widgets.append(widget)
            else:
                node.children.append(self._field(child, child_path, (*ancestors, node)))
        if node.widgets and node.children:
            node.issues.append("mixed_child_fields_and_widgets")
        if obj.get("/Subtype") == pikepdf.Name.Widget and "/Kids" in obj:
            node.issues.append("merged_widget_has_kids")
        return node

    def _widget(
        self, obj: pikepdf.Object, path: tuple[int, ...], parent: FieldNode | None
    ) -> FieldWidget:
        occurrences = self.widget_pages.get(obj.objgen, []) if obj.is_indirect else []
        widget = FieldWidget(path, obj, occurrences)
        if parent is not None:
            widget.issues.extend(self._parent_issues(obj, parent))
        if obj.is_indirect:
            self.widget_owners.add(obj.objgen)
        else:
            widget.issues.append("unresolved_direct_widget_identity")
        if not occurrences:
            widget.issues.append("widget_not_found_in_page_annots")
        if len(occurrences) > 1:
            widget.issues.append("widget_has_multiple_page_occurrences")
        if "/P" in obj:
            linked = obj.P
            if not isinstance(linked, pikepdf.Dictionary) or not linked.is_indirect:
                widget.issues.append("invalid_widget_page_link")
            elif any(
                (loc.page.object_id, loc.page.generation) != linked.objgen
                for loc in occurrences
            ):
                widget.issues.append("widget_page_link_disagrees_with_annots")
        return widget

    def locate(self, locator: PdfFieldLocator) -> FieldNode:
        node = self.nodes.get(tuple(locator.field_path))
        if node is None or node.locator != locator:
            raise ValueError("PDF field path/object locator does not match revision")
        return node
