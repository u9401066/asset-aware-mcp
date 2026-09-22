"""Source-scoped field evidence, including hidden fields and every widget occurrence."""

from __future__ import annotations

import hashlib
import math
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pikepdf

from src.domain.native_asset_models import MAX_NATIVE_RESULT_BYTES
from src.infrastructure.native_pdf_annotation_geometry import (
    display_geometry,
    display_transforms,
)
from src.infrastructure.native_pdf_field_tree import INHERITABLE, FieldTree, identity
from src.infrastructure.native_pdf_graph import PdfObjectGraph, canonical, graph_digest
from src.infrastructure.native_pdf_package import NativePdfPackage

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.domain.native_pdf_annotations import PdfAnnotationLocator
    from src.domain.native_pdf_fields import PdfFieldLocator, PdfFieldReference
    from src.infrastructure.native_pdf_field_tree import FieldNode, FieldWidget

MAX_FIELD_RECORD_BYTES = 16 * 1024 * 1024


def _bounded_records(values: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    size = 0
    for value in values:
        size += len(canonical(value))
        if size > MAX_FIELD_RECORD_BYTES:
            raise ValueError("Native PDF field representation exceeds 16 MiB")
        result.append(value)
    return result


def _text(value: Any) -> str | None:
    return str(value) if isinstance(value, pikepdf.String) else None


class FieldCatalog:
    def __init__(self, package: NativePdfPackage):
        self.package = package
        self.tree = FieldTree(package)
        self.mapping = package.page_map()
        self.field_paths = {
            node.obj.objgen: [list(path)]
            for path, node in self.tree.nodes.items()
            if node.obj.is_indirect
        }
        self.transforms = display_transforms(
            package.data, {loc.page.page_index for loc, _ in self.tree.page_widgets}
        )
        self.form_properties = PdfObjectGraph(self.mapping).describe(
            self.tree.form, ignore_root_keys=("/Fields",)
        )
        self.form_properties_sha256 = graph_digest(self.form_properties)

    def _graph(self, value: Any, skips: tuple[str, ...] = ()) -> dict[str, Any]:
        return PdfObjectGraph(self.mapping).describe(value, ignore_root_keys=skips)

    def _entries(self, node: FieldNode) -> dict[str, Any]:
        entries: dict[str, Any] = {}
        for key in INHERITABLE:
            value, owner = node.inherited(key)
            source: dict[str, Any] | None = (
                {"field": owner.locator.model_dump()} if owner else None
            )
            if owner is None and key in {"/DA", "/Q"} and key in self.tree.form:
                value, source = self.tree.form[key], {"acroform": True}
            if source is not None:
                entries[key] = {"source": source, "native_graph": self._graph(value)}
                if isinstance(value, (pikepdf.String, pikepdf.Name)):
                    entries[key]["text"] = str(value)
                elif isinstance(value, (int, bool)):
                    entries[key]["value"] = value
                if len(canonical(entries)) > MAX_FIELD_RECORD_BYTES:
                    raise ValueError("Native PDF field representation exceeds 16 MiB")
        return entries

    def _geometry(
        self, obj: pikepdf.Object, locator: PdfAnnotationLocator
    ) -> dict[str, Any]:
        rect = obj.get("/Rect")
        if not isinstance(rect, pikepdf.Array) or len(rect) != 4:
            return {"status": "invalid_native_rectangle"}
        try:
            if any(
                not isinstance(v, (Decimal, float, int)) or isinstance(v, bool)
                for v in rect
            ):
                return {"status": "invalid_native_rectangle"}
            values = [float(v) for v in rect]
            if (
                not all(math.isfinite(v) for v in values)
                or values[0] == values[2]
                or values[1] == values[3]
            ):
                return {"status": "invalid_native_rectangle"}
            geometry = display_geometry(obj, self.transforms[locator.page.page_index])
            if not all(math.isfinite(v) for v in geometry["rect"]):
                return {"status": "invalid_native_rectangle"}
            return {"status": "mapped", **geometry}
        except (TypeError, ValueError, OverflowError):
            return {"status": "invalid_native_rectangle"}

    def _widget(self, widget: FieldWidget) -> dict[str, Any]:
        obj = widget.obj
        appearances = obj.get("/AP")
        normal = (
            appearances.get("/N")
            if isinstance(appearances, pikepdf.Dictionary)
            else None
        )
        return {
            "tree_path": list(widget.path),
            **identity(obj),
            "issues": widget.issues,
            "parent_link": self._link(obj.get("/Parent")),
            "page_occurrences": [
                {
                    "locator": loc.model_dump(),
                    "display_geometry": self._geometry(obj, loc),
                }
                for loc in widget.occurrences
            ],
            "appearance_state": str(obj.AS)
            if isinstance(obj.get("/AS"), pikepdf.Name)
            else None,
            "normal_appearance_states": sorted(normal.keys())
            if isinstance(normal, pikepdf.Dictionary)
            else [],
            "normal_appearance_kind": "stream"
            if isinstance(normal, pikepdf.Stream)
            else "states"
            if isinstance(normal, pikepdf.Dictionary)
            else "missing_or_invalid",
            "native_graph": self._graph(obj, ("/Parent", "/Kids")),
        }

    def record(self, locator: PdfFieldLocator) -> dict[str, Any]:
        node = self.tree.locate(locator)
        names = [_text(n.obj.get("/T")) for n in (*node.ancestors, node)]
        entries = self._entries(node)
        value = {
            "schema_version": "native-pdf-field-v1",
            "locator": locator.model_dump(),
            "partial_name": names[-1],
            "qualified_name": ".".join(n for n in names if n is not None),
            "name_is_identity": False,
            "kind": "group" if node.children else "terminal",
            "field_type": entries.get("/FT", {}).get("text"),
            "issues": node.issues,
            "parent_link": self._link(node.obj.get("/Parent")),
            "ancestor_fields": _bounded_records(
                {
                    "locator": n.locator.model_dump(),
                    "issues": n.issues,
                    "parent_link": self._link(n.obj.get("/Parent")),
                    "native_graph": self._graph(n.obj, ("/Parent", "/Kids")),
                }
                for n in node.ancestors
            ),
            "child_fields": [n.locator.model_dump() for n in node.children],
            "kids_present": "/Kids" in node.obj,
            "kids_array_identity": identity(node.obj.Kids)
            if "/Kids" in node.obj
            else None,
            "inherited_entries": entries,
            "inheritance_basis": "physical_Fields_Kids_tree; inspect_parent_link_issues",
            "native_graph": self._graph(node.obj, ("/Parent", "/Kids")),
            "widgets": _bounded_records(
                self._widget(widget) for widget in node.widgets
            ),
            "form_properties_sha256": self.form_properties_sha256,
            "record_scope": "field_dictionary_ancestors_inherited_entries_and_owned_widgets; descendant_field_values_are_separate_records",
            "review_required": [
                "field_value_and_visual_appearance_consistency",
                "actual_page_images",
                "viewer_behavior_and_scripts",
                "XFA_if_present",
            ],
        }
        if len(canonical(value)) > MAX_FIELD_RECORD_BYTES:
            raise ValueError("Native PDF field representation exceeds 16 MiB")
        return value

    def _link(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, pikepdf.Dictionary):
            if value.is_indirect:
                return {
                    **identity(value),
                    "field_paths": self.field_paths.get(value.objgen, []),
                }
            return {"direct_dictionary": self._graph(value)}
        return {"invalid_parent_value": self._graph(value)}

    def inspect(self) -> dict[str, Any]:
        fields = []
        represented_bytes = len(canonical(self.form_properties))
        for node in self.tree.nodes.values():
            record = self.record(node.locator)
            represented_bytes += len(canonical(record))
            if represented_bytes > MAX_NATIVE_RESULT_BYTES:
                raise ValueError(
                    "PDF field catalog exceeds its aggregate representation limit"
                )
            fields.append(
                {
                    key: record[key]
                    for key in (
                        "locator",
                        "partial_name",
                        "qualified_name",
                        "kind",
                        "field_type",
                        "issues",
                        "child_fields",
                    )
                }
                | {
                    "record_sha256": graph_digest(record),
                    "widget_count": len(node.widgets),
                }
            )
        orphans = []
        for loc, obj in self.tree.page_widgets:
            if obj.is_indirect and obj.objgen in self.tree.widget_owners:
                continue
            orphan = {
                "locator": loc.model_dump(),
                "display_geometry": self._geometry(obj, loc),
                "native_graph": self._graph(obj),
                "reason": "unresolved_direct_widget_identity"
                if not obj.is_indirect
                else "widget_not_in_field_tree",
            }
            represented_bytes += len(canonical(orphan))
            if represented_bytes > MAX_NATIVE_RESULT_BYTES:
                raise ValueError(
                    "PDF field catalog exceeds its aggregate representation limit"
                )
            orphans.append(orphan)
        inventory = {
            "schema_version": "native-pdf-field-catalog-v1",
            "field_count": len(fields),
            "terminal_field_count": sum(
                not node.children for node in self.tree.nodes.values()
            ),
            "page_widget_occurrence_count": len(self.tree.page_widgets),
            "acroform_present": "/AcroForm" in self.package.pdf.Root,
            "root_fields_present": "/Fields" in self.tree.form,
            "root_fields_array_identity": identity(self.tree.form.Fields)
            if "/Fields" in self.tree.form
            else None,
            "fields": fields,
            "orphan_page_widgets": orphans,
            "xfa_present": "/XFA" in self.tree.form,
            "form_properties": self.form_properties,
            "form_properties_sha256": self.form_properties_sha256,
            "parser_checks": self.package.parser_checks,
            "verification_scope": "native_structure_and_source_identity; no_repair_or_semantic_or_visual_verdict",
        }
        if len(canonical(inventory)) > MAX_NATIVE_RESULT_BYTES:
            raise ValueError("PDF field catalog exceeds its representation limit")
        return {**inventory, "catalog_sha256": graph_digest(inventory)}

    def verify(self, reference: PdfFieldReference) -> FieldNode:
        if (
            hashlib.sha256(self.package.data).hexdigest() != reference.revision
            or graph_digest(self.record(reference.locator)) != reference.value_sha256
        ):
            raise ValueError("Stale native PDF field reference")
        return self.tree.locate(reference.locator)


def inspect_fields(data: bytes) -> dict[str, Any]:
    with NativePdfPackage(data) as package:
        return FieldCatalog(package).inspect()


def read_field(data: bytes, locator: PdfFieldLocator) -> dict[str, Any]:
    with NativePdfPackage(data) as package:
        return FieldCatalog(package).record(locator)


def decompose_fields(data: bytes) -> list[dict[str, Any]]:
    with NativePdfPackage(data) as package:
        catalog = FieldCatalog(package)
        records = []
        size = 0
        for node in catalog.tree.nodes.values():
            record = catalog.record(node.locator)
            size += len(canonical(record))
            if size > MAX_NATIVE_RESULT_BYTES:
                raise ValueError("PDF field records exceed the aggregate limit")
            records.append(record)
        return records
