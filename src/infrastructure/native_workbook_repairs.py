"""Deterministic workbook indices, caches and calculation metadata maintenance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_ooxml import DOC_REL_NS, SHEET_NS
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from src.infrastructure.native_workbook_package import NativeWorkbookPackage


def repair_indices(
    book: NativeWorkbookPackage,
    after: list[dict[str, Any]],
    roots: dict[str, etree._Element],
) -> list[str]:
    old_ids = [item["key"]["sheet_id"] for item in book.entries]
    new_ids = [item["key"]["sheet_id"] for item in after]
    if old_ids == new_ids:
        return []
    visible = next(item for item in after if item["state"] == "visible")
    fallback = new_ids.index(visible["key"]["sheet_id"])

    def remap(value: str) -> int | None:
        try:
            index = int(value)
        except ValueError as exc:
            raise ValueError("Invalid workbook sheet index") from exc
        if not 0 <= index < len(old_ids):
            raise ValueError("Workbook sheet index is outside the sheet registry")
        return new_ids.index(old_ids[index]) if old_ids[index] in new_ids else None

    names = book.workbook.find("s:definedNames", NS)
    if names is not None:
        for node in list(names):
            if node.get("localSheetId") is not None:
                index = remap(node.get("localSheetId", ""))
                if index is None:
                    names.remove(node)
                else:
                    node.set("localSheetId", str(index))
    for view_id, node in enumerate(
        book.workbook.findall("s:bookViews/s:workbookView", NS)
    ):
        # Absent activeTab/firstSheet mean zero, so insertion must remap defaults too.
        for key in ("activeTab", "firstSheet"):
            index = remap(node.get(key, "0"))
            node.set(key, str(fallback if index is None else index))
            if key == "activeTab" and index is None:
                part = visible["key"]["part"]
                if after[fallback]["kind"] != f"{DOC_REL_NS}/worksheet":
                    continue
                root = roots[part]
                views = root.find("s:sheetViews", NS)
                if views is None:
                    views = etree.Element(f"{{{SHEET_NS}}}sheetViews")
                    preceding = {
                        f"{{{SHEET_NS}}}{name}" for name in ("sheetPr", "dimension")
                    }
                    at = next(
                        (
                            i
                            for i, child in enumerate(root)
                            if isinstance(child.tag, str) and child.tag not in preceding
                        ),
                        len(root),
                    )
                    root.insert(at, views)
                view = next(
                    (v for v in views if v.get("workbookViewId") == str(view_id)), None
                )
                if view is None:
                    view = etree.SubElement(
                        views, f"{{{SHEET_NS}}}sheetView", workbookViewId=str(view_id)
                    )
                view.set("tabSelected", "1")
    for node in book.workbook.findall("s:customWorkbookViews/s:customWorkbookView", NS):
        value = node.get("activeSheetId")
        if value is not None:
            try:
                identity = str(int(value))
            except ValueError as exc:
                raise ValueError("Invalid custom workbook activeSheetId") from exc
            if identity not in old_ids:
                raise ValueError("Unknown custom workbook activeSheetId")
            if identity not in new_ids:
                node.set("activeSheetId", visible["key"]["sheet_id"])
    return ["worksheet_view_indices_remapped", "defined_name_scopes_remapped"]


def repair_calculation(
    book: NativeWorkbookPackage,
    rels: etree._Element,
) -> set[str]:
    calc = book.workbook.find("s:calcPr", NS)
    if calc is None:
        calc = etree.Element(f"{{{SHEET_NS}}}calcPr")
        tail = {
            "oleSize",
            "customWorkbookViews",
            "pivotCaches",
            "smartTagPr",
            "smartTagTypes",
            "webPublishing",
            "fileRecoveryPr",
            "webPublishObjects",
            "extLst",
        }
        at = next(
            (
                i
                for i, node in enumerate(book.workbook)
                if isinstance(node.tag, str) and etree.QName(node).localname in tail
            ),
            len(book.workbook),
        )
        book.workbook.insert(at, calc)
    calc.attrib.update(
        {"fullCalcOnLoad": "1", "forceFullCalc": "1", "calcMode": "auto"}
    )
    chains = {
        rid: part
        for rid, (kind, part) in book.rels.items()
        if kind == f"{DOC_REL_NS}/calcChain"
    }
    for node in list(rels):
        if node.get("Id") in chains:
            rels.remove(node)
    # Detach the invalid chain, preserving bytes and any other incoming links.
    return set(chains.values())


def repair_caches(
    book: NativeWorkbookPackage,
    after: list[dict[str, Any]],
    roots: dict[str, etree._Element],
) -> list[str]:
    repairs = []
    path = book.shared_string_path
    if path and path in roots and roots[path].get("count") is not None:
        count = sum(
            len(
                roots[item["key"]["part"]].xpath(
                    "./s:sheetData/s:row/s:c[@t='s']", namespaces=NS
                )
            )
            for item in after
            if item["kind"] == f"{DOC_REL_NS}/worksheet"
        )
        if roots[path].get("count") != str(count):
            roots[path].set("count", str(count))
            repairs.append("shared_string_reference_count_recomputed")
    namespace = (
        "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
    )
    for root in roots.values():
        if root.tag == f"{{{namespace}}}Properties":
            for name in ("HeadingPairs", "TitlesOfParts"):
                for node in root.findall(f"{{{namespace}}}{name}"):
                    root.remove(node)
                    if "stale_extended_property_titles_removed" not in repairs:
                        repairs.append("stale_extended_property_titles_removed")
    return repairs
