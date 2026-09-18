"""Deterministic spreadsheet package maintenance after a cell edit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    TYPE_NS,
    relationships_path,
    xml_bytes,
)
from src.infrastructure.native_spreadsheet_reader import NS, _tag

if TYPE_CHECKING:
    from src.infrastructure.native_spreadsheet_reader import NativeSpreadsheetReader


def repair_shared_strings(
    book: NativeSpreadsheetReader,
    replacements: dict[str, bytes],
    repairs: list[str],
    roots: dict[str, etree._Element],
) -> None:
    if book.shared_string_path is not None:
        reference_count = 0
        for name, info in book.sheets.items():
            if info["kind"] == f"{DOC_REL_NS}/worksheet":
                root = roots[name] if name in roots else book._sheet(name)
                reference_count += len(
                    root.xpath("./s:sheetData/s:row/s:c[@t='s']", namespaces=NS)
                )
        strings = book.package.xml(book.shared_string_path)
        if strings.get("count") is not None and strings.get("count") != str(
            reference_count
        ):
            strings.set("count", str(reference_count))
            replacements[book.shared_string_path] = xml_bytes(strings)
            repairs.append("shared_string_reference_count_recomputed")


def request_recalculation(
    book: NativeSpreadsheetReader, replacements: dict[str, bytes], repairs: list[str]
) -> None:
    calc = book.workbook.find("s:calcPr", NS)
    if calc is None:
        calc = etree.Element(_tag("calcPr"))
        # calcPr precedes these optional workbook tail elements.
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
        index = next(
            (
                i
                for i, item in enumerate(book.workbook)
                if etree.QName(item).localname in tail
            ),
            len(book.workbook),
        )
        book.workbook.insert(index, calc)
    calc.set("fullCalcOnLoad", "1")
    calc.set("forceFullCalc", "1")
    calc.set("calcMode", "auto")
    replacements[book.workbook_path] = xml_bytes(book.workbook)
    repairs.extend(
        [
            "worksheet_dimension_recomputed",
            "row_span_cache_removed",
            "formula_recalculation_requested",
        ]
    )


def remove_calculation_chain(
    book: NativeSpreadsheetReader,
    replacements: dict[str, bytes],
    repairs: list[str],
    removed: set[str],
) -> None:
    chains = {
        rid: path
        for rid, (kind, path) in book.rels.items()
        if kind == f"{DOC_REL_NS}/calcChain"
    }
    if chains:
        rel_path = relationships_path(book.workbook_path)
        rels = book.package.xml(rel_path)
        for relationship in list(rels):
            if relationship.get("Id") in chains:
                rels.remove(relationship)
        types = book.package.xml("[Content_Types].xml")
        for override in list(types):
            if (
                override.tag == f"{{{TYPE_NS}}}Override"
                and override.get("PartName", "").lstrip("/") in chains.values()
            ):
                types.remove(override)
        replacements[rel_path] = xml_bytes(rels)
        replacements["[Content_Types].xml"] = xml_bytes(types)
        removed.update(chains.values())
        repairs.append("stale_calculation_chain_removed")
