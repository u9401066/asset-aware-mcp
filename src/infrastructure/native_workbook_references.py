"""Explicit workbook references across native formulas, names, charts and pivots."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_ooxml import DOC_REL_NS, SHEET_NS
from src.infrastructure.native_workbook_formulas import (
    rename_sheet_references,
    sheet_references,
    table_references,
)

if TYPE_CHECKING:
    from src.infrastructure.native_workbook_package import NativeWorkbookPackage

FORMULA_NAMES = {
    "f",
    "formula",
    "formula1",
    "formula2",
    "definedName",
    "calculatedColumnFormula",
    "totalsRowFormula",
    "FmlaLink",
    "FmlaRange",
    "FmlaTxbx",
}
FORMULA_NAMESPACES = {
    SHEET_NS,
    "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "urn:schemas-microsoft-com:office:excel",
    "http://schemas.microsoft.com/office/excel/2006/main",
    "http://schemas.microsoft.com/office/spreadsheetml/2009/9/main",
}
SHEET_SOURCE_KINDS = {"pivot_source", "consolidation_source"}
NAMED_SOURCE_KINDS = {"pivot_name", "consolidation_name"}


@dataclass
class WorkbookReferenceField:
    part: str
    node: etree._Element
    kind: str
    attribute: str | None = None

    @property
    def text(self) -> str:
        return (
            self.node.get(self.attribute, "")
            if self.attribute
            else self.node.text or ""
        )

    def set(self, value: str) -> None:
        if self.attribute:
            self.node.set(self.attribute, value)
        else:
            self.node.text = value

    def formula(self) -> str:
        return (
            self.text.removeprefix("#")
            if self.kind == "hyperlink_location"
            else self.text
        )

    def record(self) -> dict[str, Any]:
        return {
            "part": self.part,
            "xpath": self.node.getroottree().getpath(self.node),
            "kind": self.kind,
            "attribute": self.attribute,
            "text": self.text,
            "text_sha256": hashlib.sha256(self.text.encode("utf-8")).hexdigest(),
        }


class NativeWorkbookReferences:
    def __init__(
        self,
        book: NativeWorkbookPackage,
        active: set[str],
        excluded_local_indices: set[int] | None = None,
    ):
        self.roots = dict(book.xml_parts(active))
        self.fields: list[WorkbookReferenceField] = []
        total = 0
        excluded_local_indices = excluded_local_indices or set()
        for part, root in self.roots.items():
            for node in root.iter():
                if not isinstance(node.tag, str):
                    continue
                tag = etree.QName(node)
                if (
                    tag.localname == "definedName"
                    and tag.namespace == SHEET_NS
                    and node.get("localSheetId") is not None
                ):
                    try:
                        index = int(node.get("localSheetId", ""))
                    except ValueError as exc:
                        raise ValueError(
                            "Invalid defined-name worksheet scope"
                        ) from exc
                    if index in excluded_local_indices:
                        continue
                fields = []
                known_namespace = tag.namespace in FORMULA_NAMESPACES or bool(
                    tag.namespace
                    and tag.namespace.startswith(
                        "http://schemas.microsoft.com/office/drawing/"
                    )
                )
                if tag.localname in FORMULA_NAMES and known_namespace:
                    fields.append(WorkbookReferenceField(part, node, "formula"))
                elif (
                    tag.namespace == SHEET_NS
                    and tag.localname == "hyperlink"
                    and node.get("location") is not None
                ):
                    fields.append(
                        WorkbookReferenceField(
                            part, node, "hyperlink_location", "location"
                        )
                    )
                elif tag.namespace == SHEET_NS and tag.localname in {
                    "worksheetSource",
                    "dataRef",
                }:
                    rid = node.get(f"{{{DOC_REL_NS}}}id")
                    external = False
                    if rid:
                        relations = book.package.relationships(part)
                        if rid not in relations:
                            raise ValueError("Pivot source relationship is missing")
                        external = not relations[rid][1]
                    prefix = (
                        "pivot"
                        if tag.localname == "worksheetSource"
                        else "consolidation"
                    )
                    for attribute, kind in (
                        ("sheet", prefix + "_source"),
                        ("name", prefix + "_name"),
                    ):
                        if node.get(attribute) is not None:
                            fields.append(
                                WorkbookReferenceField(part, node, kind, attribute)
                            )
                            if external:
                                fields[-1].kind = "external_" + kind
                for field in fields:
                    total += len(field.text.encode("utf-8"))
                    self.fields.append(field)
                    if len(self.fields) > 20_000 or total > 8 * 1024 * 1024:
                        raise ValueError(
                            "Workbook references exceed the inspection budget"
                        )

    def rename(self, old: str, new: str) -> dict[str, int]:
        changed: dict[str, int] = {}
        for field in self.fields:
            if field.kind in NAMED_SOURCE_KINDS or field.kind.startswith("external_"):
                continue
            if field.kind in SHEET_SOURCE_KINDS:
                value = new if field.text.casefold() == old.casefold() else field.text
                count = int(value != field.text)
            else:
                value, count = rename_sheet_references(field.formula(), old, new)
                if field.kind == "hyperlink_location" and field.text.startswith("#"):
                    value = "#" + value
            if count:
                field.set(value)
                changed[field.part] = changed.get(field.part, 0) + count
        return changed

    def check_delete(
        self,
        before: list[dict[str, Any]],
        removed_ids: set[str],
        removed_tables: set[str],
    ) -> None:
        removed_names = {
            s["name"].casefold() for s in before if s["key"]["sheet_id"] in removed_ids
        }
        for field in self.fields:
            if field.kind.startswith("external_"):
                continue
            if field.kind in NAMED_SOURCE_KINDS:
                if field.text.casefold() in removed_tables:
                    raise ValueError(
                        "Deleted worksheet table is still used by a pivot cache or consolidated range"
                    )
                continue
            if field.kind in SHEET_SOURCE_KINDS:
                if field.text.casefold() in removed_names:
                    raise ValueError(
                        "Deleted worksheet is still used by a pivot cache or consolidated range"
                    )
                continue
            for ref in sheet_references(field.formula()):
                members = _members(before, ref.names)
                if members & removed_ids or any(
                    n.casefold() in removed_names for n in ref.names
                ):
                    raise ValueError(
                        "Deleted worksheet has a surviving explicit formula or hyperlink reference"
                    )
            if table_references(field.formula()) & removed_tables:
                raise ValueError(
                    "Deleted worksheet table has a surviving structured reference"
                )

    def check_membership(
        self, before: list[dict[str, Any]], after: list[dict[str, Any]], allow: bool
    ) -> int:
        changed = 0
        for field in self.fields:
            if field.kind.startswith(("pivot_", "consolidation_", "external_")):
                continue
            for ref in sheet_references(field.formula()):
                if len(ref.names) == 2 and _members(before, ref.names) != _members(
                    after, ref.names
                ):
                    if not allow:
                        raise ValueError(
                            "Sheet structure changes 3D-reference membership; inspect references and explicitly allow the change"
                        )
                    changed += 1
        return changed


def _members(sheets: list[dict[str, Any]], names: tuple[str, ...]) -> set[str]:
    matches = {item["name"].casefold(): index for index, item in enumerate(sheets)}
    if len(names) == 1:
        return (
            {sheets[matches[names[0].casefold()]]["key"]["sheet_id"]}
            if names[0].casefold() in matches
            else set()
        )
    if any(name.casefold() not in matches for name in names):
        raise ValueError("3D reference has an unknown worksheet boundary")
    start, end = sorted(matches[name.casefold()] for name in names)
    return {item["key"]["sheet_id"] for item in sheets[start : end + 1]}
