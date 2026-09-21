"""ODS repetition splitting, coordinate guards and scoped grid growth."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from lxml import etree

from src.infrastructure.native_odf_package import NS, q
from src.infrastructure.native_ods_reader import (
    NativeODSReader,
    cells,
    columns,
    repeat,
    rows,
)

if TYPE_CHECKING:
    from src.domain.native_ods import NativeODSCellEdit


def _dependency(node: etree._Element) -> bool:
    return any(
        isinstance(child.tag, str)
        and (
            child.tag.startswith("{" + NS["draw"] + "}")
            or child.tag == q("office", "annotation")
            or q("table", "formula") in child.attrib
            or any(
                etree.QName(key).localname
                in {
                    "id",
                    "number-rows-spanned",
                    "number-columns-spanned",
                    "number-matrix-rows-spanned",
                    "number-matrix-columns-spanned",
                }
                for key in child.attrib
            )
        )
        for child in node.iter()
    )


def _split(node: etree._Element, axis: str, index: int) -> etree._Element:
    count = repeat(node, axis)
    if count == 1:
        return node
    if _dependency(node):
        raise ValueError(
            "ODS repeated objects/formulas/merges require a mapping-aware edit"
        )
    parent = node.getparent()
    assert parent is not None
    position = parent.index(node)
    pieces: list[etree._Element] = []
    selected: etree._Element | None = None
    for length, target in ((index, False), (1, True), (count - index - 1, False)):
        if length:
            item = copy.deepcopy(node)
            item.tail = None
            item.attrib.pop(q("table", f"number-{axis}-repeated"), None)
            if length > 1:
                item.set(q("table", f"number-{axis}-repeated"), str(length))
            pieces.append(item)
            if target:
                selected = item
    pieces[-1].tail = node.tail
    parent.remove(node)
    for offset, item in enumerate(pieces):
        parent.insert(position + offset, item)
        for old, new in zip(node.iter(), item.iter(), strict=True):
            if any(new.nsmap.get(key) != value for key, value in old.nsmap.items()):
                raise ValueError("ODS repetition split would lose a namespace binding")
    assert selected is not None
    return selected


def guard_edit(book: NativeODSReader, edit: NativeODSCellEdit) -> None:
    table = book.table(edit.locator)
    if table.get(q("table", "protected")) in {"true", "1"} or book.body.get(
        q("table", "structure-protected")
    ) in {"true", "1"}:
        raise ValueError(
            "Protected ODS content requires an explicit protection workflow"
        )
    if table.find(q("table", "table-source")) is not None:
        raise ValueError("Linked ODS tables require a source-aware edit")
    if book.body.find(".//table:tracked-changes", NS) is not None:
        raise ValueError("Tracked ODS changes require a revision-aware edit")
    for start, count, row in rows(table):
        for column, width, cell in cells(row):
            merged_rows = cell.get(q("table", "number-rows-spanned"))
            merged_columns = cell.get(q("table", "number-columns-spanned"))
            if merged_rows is not None or merged_columns is not None:
                try:
                    height, span = int(merged_rows or "1"), int(merged_columns or "1")
                except ValueError as exc:
                    raise ValueError("Invalid ODS merge extent") from exc
                if min(height, span) < 1 or width > 1 or (height > 1 and count > 1):
                    raise ValueError("Ambiguous ODS merge extent")
                in_merge = (
                    start <= edit.locator.row < start + count + height - 1
                    and column <= edit.locator.column < column + span
                )
                if in_merge and (
                    edit.locator.row >= start + count or edit.locator.column != column
                ):
                    raise ValueError(
                        "Covered ODS coordinates require editing the merge anchor"
                    )
            nr = cell.get(q("table", "number-matrix-rows-spanned"))
            nc = cell.get(q("table", "number-matrix-columns-spanned"))
            if nr is not None or nc is not None:
                try:
                    height, span = int(nr or "1"), int(nc or "1")
                except ValueError as exc:
                    raise ValueError("Invalid ODS matrix extent") from exc
                if min(height, span) < 1 or count > 1 or width > 1:
                    raise ValueError("Ambiguous ODS matrix extent")
                if (
                    start <= edit.locator.row < start + height
                    and column <= edit.locator.column < column + span
                ):
                    raise ValueError("ODS matrix cells require a range-aware edit")
    _, cell, _ = book.locate(edit.locator)
    if cell is None:
        return
    if cell.tag == q("table", "covered-table-cell"):
        raise ValueError("Covered ODS cells require editing the merge anchor")
    if cell.get(q("table", "protected")) in {"true", "1"}:
        raise ValueError("Protected ODS cell requires a protection workflow")
    for paragraph in cell:
        if paragraph.tag not in {q("text", "p"), q("text", "h")}:
            continue
        for item in paragraph.iter():
            if not isinstance(item.tag, str):
                continue
            allowed = {
                q("text", name)
                for name in ("p", "h", "span", "a", "s", "tab", "line-break")
            }
            if item.tag not in allowed or any(
                etree.QName(key).localname == "id" for key in item.attrib
            ):
                raise ValueError("ODS display dependencies require a text-aware edit")


def ensure_cell(book: NativeODSReader, edit: NativeODSCellEdit) -> etree._Element:
    locator = edit.locator
    table = book.table(locator)
    row, _, _ = book.locate(locator)
    if row is None:
        row_ranges = list(rows(table))
        end = row_ranges[-1][0] + row_ranges[-1][1] if row_ranges else 0
        if row_ranges:
            last = row_ranges[-1][2]
            while last.getparent() is not table:
                parent = last.getparent()
                assert parent is not None
                last = parent
            position = table.index(last) + 1
        else:
            position = len(table)
        if locator.row > end:
            gap = etree.Element(q("table", "table-row"))
            gap.set(q("table", "number-rows-repeated"), str(locator.row - end))
            etree.SubElement(gap, q("table", "table-cell"))
            table.insert(position, gap)
            position += 1
        row = etree.Element(q("table", "table-row"))
        table.insert(position, row)
    else:
        start = next(start for start, _, item in rows(table) if item is row)
        row = _split(row, "rows", locator.row - start)
    end = 0
    for start, width, cell in cells(row):
        if start <= locator.column < start + width:
            return _split(cell, "columns", locator.column - start)
        end = start + width
    if locator.column > end:
        gap = etree.SubElement(row, q("table", "table-cell"))
        gap.set(q("table", "number-columns-repeated"), str(locator.column - end))
    return etree.SubElement(row, q("table", "table-cell"))


def ensure_columns(table: etree._Element) -> tuple[int, int] | None:
    declared = list(columns(table))
    count = declared[-1][0] + declared[-1][1] if declared else 0
    required = max(
        (start + width for _, _, row in rows(table) for start, width, _ in cells(row)),
        default=0,
    )
    if required <= count:
        return None
    if declared:
        last = declared[-1][2]
        while last.getparent() is not table:
            parent = last.getparent()
            assert parent is not None
            last = parent
        position = table.index(last) + 1
    else:
        first = next(rows(table), None)
        if first:
            node = first[2]
            while node.getparent() is not table:
                parent = node.getparent()
                assert parent is not None
                node = parent
            position = table.index(node)
        else:
            position = len(table)
    added = etree.Element(q("table", "table-column"))
    if required - count > 1:
        added.set(q("table", "number-columns-repeated"), str(required - count))
    table.insert(position, added)
    return count, required
