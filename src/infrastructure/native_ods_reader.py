"""Native ODS ranges stay compressed; reads keep values, display and XML distinct."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_ods import (
    MAX_ODS_COLUMNS,
    MAX_ODS_RECORDS,
    MAX_ODS_ROWS,
    NativeODSCellLocator,
)
from src.infrastructure.native_odf_package import NS, NativeODFPackage, q
from src.infrastructure.native_ods_text import paragraph_text

if TYPE_CHECKING:
    from collections.abc import Iterator

ROW_CONTAINERS = {
    q("table", name) for name in ("table-row-group", "table-header-rows", "table-rows")
}
CELL_TAGS = {q("table", "table-cell"), q("table", "covered-table-cell")}
COL_CONTAINERS = {
    q("table", name)
    for name in ("table-column-group", "table-header-columns", "table-columns")
}


def columns(table: etree._Element) -> Iterator[tuple[int, int, etree._Element]]:
    def walk(parent: etree._Element) -> Iterator[etree._Element]:
        for child in parent:
            if child.tag == q("table", "table-column"):
                yield child
            elif child.tag in COL_CONTAINERS:
                yield from walk(child)

    offset = 0
    for node in walk(table):
        count = repeat(node, "columns")
        if offset + count > MAX_ODS_COLUMNS:
            raise ValueError("ODS declared column budget exceeded")
        yield offset, count, node
        offset += count


def repeat(node: etree._Element, axis: str) -> int:
    raw = node.get(q("table", f"number-{axis}-repeated"), "1")
    maximum = MAX_ODS_ROWS if axis == "rows" else MAX_ODS_COLUMNS
    if not re.fullmatch(r"[0-9]{1,10}", raw) or not 1 <= int(raw) <= maximum:
        raise ValueError("Invalid or excessive ODS repetition")
    return int(raw)


def rows(table: etree._Element) -> Iterator[tuple[int, int, etree._Element]]:
    def walk(parent: etree._Element) -> Iterator[etree._Element]:
        for child in parent:
            if child.tag == q("table", "table-row"):
                yield child
            elif child.tag in ROW_CONTAINERS:
                yield from walk(child)

    offset = 0
    for row in walk(table):
        count = repeat(row, "rows")
        if offset + count > MAX_ODS_ROWS:
            raise ValueError("ODS logical row budget exceeded")
        yield offset, count, row
        offset += count


def cells(row: etree._Element) -> Iterator[tuple[int, int, etree._Element]]:
    offset = 0
    for cell in row:
        if cell.tag not in CELL_TAGS:
            continue
        count = repeat(cell, "columns")
        if offset + count > MAX_ODS_COLUMNS:
            raise ValueError("ODS logical column budget exceeded")
        yield offset, count, cell
        offset += count


def cell_value(cell: etree._Element | None) -> dict[str, Any]:
    if cell is None:
        return {
            "present": False,
            "covered": False,
            "value_type": None,
            "value_attributes": {},
            "display_paragraphs": [],
            "formula": None,
            "cached_value_verified": False,
            "attributes": {},
            "native_xml": None,
        }
    formula = cell.get(q("table", "formula"))
    expression, namespace = formula, None
    if formula is not None:
        prefix, separator, remaining = formula.partition(":")
        try:
            name = etree.QName(prefix)
            prefixed = (
                bool(separator) and name.namespace is None and name.localname == prefix
            )
        except ValueError:
            prefixed = False
        expression = remaining if prefixed else formula
        namespace = cell.nsmap.get(prefix) if prefixed else NS["of"]
    result: dict[str, Any] = {
        "present": True,
        "covered": cell.tag == q("table", "covered-table-cell"),
        "value_type": cell.get(q("office", "value-type")),
        "value_attributes": {
            etree.QName(key).localname: value
            for key, value in cell.attrib.items()
            if key.startswith("{" + NS["office"] + "}")
        },
        "display_paragraphs": [
            paragraph_text(p) for p in cell if p.tag in {q("text", "p"), q("text", "h")}
        ],
        "formula": None
        if formula is None
        else {"lexical": formula, "expression": expression, "namespace": namespace},
        "cached_value_verified": False,
        "attributes": dict(cell.attrib),
        "native_xml": etree.tostring(cell, encoding="unicode", with_tail=False),
    }
    if len(json.dumps(result, ensure_ascii=False).encode()) > 256 * 1024:
        raise ValueError("ODS cell evidence exceeds record byte budget")
    return result


class NativeODSReader:
    def __init__(self, data: bytes):
        self.package = NativeODFPackage(data)
        self.root = self.package.xml("content.xml")
        if self.root.tag != q("office", "document-content"):
            raise ValueError("Expected ODF document-content")
        sheets = self.root.findall("office:body/office:spreadsheet", NS)
        if len(sheets) != 1:
            raise ValueError("Expected one ODS spreadsheet body")
        self.body = sheets[0]
        self.tables = self.body.findall(q("table", "table"))
        if not 1 <= len(self.tables) <= 256:
            raise ValueError("ODS table count exceeds operational bounds")
        names = [table.get(q("table", "name"), "") for table in self.tables]
        if any(not name or len(name) > 1024 for name in names) or len(
            set(names)
        ) != len(names):
            raise ValueError("Ambiguous ODS table identity")
        count = 0
        for table in self.tables:
            count += sum(1 for _ in columns(table))
            if count > MAX_ODS_RECORDS:
                raise ValueError("ODS physical row/cell budget exceeded")
            for _, _, row in rows(table):
                count += 1
                for _ in cells(row):
                    count += 1
                    if count > MAX_ODS_RECORDS:
                        raise ValueError("ODS physical row/cell budget exceeded")
                if count > MAX_ODS_RECORDS:
                    raise ValueError("ODS physical row/cell budget exceeded")

    def table(self, locator: NativeODSCellLocator) -> etree._Element:
        if locator.table_index >= len(self.tables):
            raise ValueError("ODS table locator index is absent")
        table = self.tables[locator.table_index]
        if table.get(q("table", "name")) != locator.table_name:
            raise ValueError("ODS table locator name does not match index")
        return table

    def locate(
        self, locator: NativeODSCellLocator
    ) -> tuple[etree._Element | None, etree._Element | None, dict[str, int] | None]:
        for row_start, row_count, row in rows(self.table(locator)):
            if row_start <= locator.row < row_start + row_count:
                for column_start, column_count, cell in cells(row):
                    if column_start <= locator.column < column_start + column_count:
                        return (
                            row,
                            cell,
                            {
                                "row_start": row_start,
                                "row_count": row_count,
                                "column_start": column_start,
                                "column_count": column_count,
                            },
                        )
                return row, None, None
        return None, None, None

    def read_cell(self, locator: NativeODSCellLocator) -> dict[str, Any]:
        _, cell, repetition = self.locate(locator)
        return {
            "locator": locator.model_dump(),
            "repetition": repetition,
            **cell_value(cell),
        }

    def inspect(self, *, offset: int = 0, limit: int = 200) -> dict[str, Any]:
        if offset < 0 or not 1 <= limit <= 1000:
            raise ValueError("Require offset >= 0 and limit between 1 and 1000")
        records, count = [], 0
        for index, table in enumerate(self.tables):
            for row_start, row_count, row in rows(table):
                for column_start, column_count, cell in cells(row):
                    if offset <= count < offset + limit:
                        records.append(
                            {
                                "locator": {
                                    "part": "content.xml",
                                    "table_index": index,
                                    "table_name": table.get(q("table", "name")),
                                    "row": row_start,
                                    "column": column_start,
                                },
                                "repetition": {
                                    "row_start": row_start,
                                    "row_count": row_count,
                                    "column_start": column_start,
                                    "column_count": column_count,
                                },
                                **cell_value(cell),
                            }
                        )
                    count += 1
        result = {
            "format": "ods",
            "odf_version": self.root.get(q("office", "version")),
            "tables": [
                {
                    "table_index": i,
                    "table_name": table.get(q("table", "name")),
                    "attributes": dict(table.attrib),
                }
                for i, table in enumerate(self.tables)
            ],
            "records": records,
            "total_physical_records": count,
            "next_offset": offset + len(records)
            if offset + len(records) < count
            else None,
            "formula_results_verified": False,
        }
        if len(json.dumps(result, ensure_ascii=False).encode()) > 16 * 1024 * 1024:
            raise ValueError("ODS listing byte budget exceeded; request a smaller page")
        return result
