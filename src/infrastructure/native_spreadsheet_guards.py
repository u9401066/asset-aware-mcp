"""Conservative native spreadsheet edit constraints; never flatten unsupported features."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.native_assets import cell_position
from src.infrastructure.native_ooxml import DOC_REL_NS
from src.infrastructure.native_spreadsheet_reader import NS, _contains, _tag

if TYPE_CHECKING:
    from lxml import etree

    from src.infrastructure.native_spreadsheet_reader import NativeSpreadsheetReader


class NativeCellGuards:
    def __init__(self, book: NativeSpreadsheetReader):
        self.book = book
        self._guard_cache: dict[
            str, tuple[list[etree._Element], list[etree._Element]]
        ] = {}
        self._table_cache: dict[str, list[etree._Element]] = {}

    def check(
        self,
        root: etree._Element,
        address: str,
        cell: etree._Element | None,
        sheet_name: str,
    ) -> None:
        self.check_structure(root, address, sheet_name)
        self._load_tables(root, sheet_name)
        self._check_tables(sheet_name, address)
        self._check_cell_features(cell)

    def check_structure(
        self, root: etree._Element, address: str, sheet_name: str
    ) -> None:
        """Shared geometry/protection guards for dedicated Table-aware writers."""
        if root.find("s:sheetProtection", NS) is not None:
            raise ValueError("Protected worksheets require an explicit unlock workflow")
        if sheet_name not in self._guard_cache:
            merged_ranges = root.findall("s:mergeCells/s:mergeCell", NS)
            special_formulas = [
                item
                for item in root.findall("s:sheetData/s:row/s:c/s:f", NS)
                if item.get("t") in {"shared", "array", "dataTable"}
            ]
            self._guard_cache[sheet_name] = (merged_ranges, special_formulas)
        merged_ranges, special_formulas = self._guard_cache[sheet_name]
        for merged in merged_ranges:
            bounds = merged.get("ref", "")
            if _contains(bounds, address) and address != bounds.split(":")[0]:
                raise ValueError("Only the anchor of a merged range can hold a value")
        for formula in special_formulas:
            if formula.get("t") in {"shared", "array", "dataTable"}:
                owner = formula.getparent().get("r", "")
                if owner == address or _contains(formula.get("ref", owner), address):
                    raise ValueError(
                        "Shared/array/data-table formula ranges require a range-aware edit"
                    )

    def _load_tables(self, root: etree._Element, sheet_name: str) -> None:
        if sheet_name not in self._table_cache:
            self._table_cache[sheet_name] = []
            table_parts = root.findall("s:tableParts/s:tablePart", NS)
            if table_parts:
                relations = self.book.package.relationships(
                    self.book.sheets[sheet_name]["part"]
                )
                for part in table_parts:
                    kind, path = relations.get(
                        part.get(f"{{{DOC_REL_NS}}}id", ""), ("", "")
                    )
                    if kind != f"{DOC_REL_NS}/table" or not path:
                        raise ValueError("Invalid worksheet table relationship")
                    self._table_cache[sheet_name].append(self.book.package.xml(path))

    def _check_tables(self, sheet_name: str, address: str) -> None:
        if self._table_cache[sheet_name]:
            for table in self._table_cache[sheet_name]:
                bounds = table.get("ref", "")
                if not _contains(bounds, address):
                    continue
                first, last = bounds.split(":")[0], bounds.split(":")[-1]
                start_row, start_col = cell_position(first)
                end_row, _ = cell_position(last)
                row, col = cell_position(address)
                headers, totals = (
                    int(table.get("headerRowCount", "1")),
                    int(table.get("totalsRowCount", "0")),
                )
                if row < start_row + headers or row > end_row - totals:
                    raise ValueError("Table headers/totals require a table-aware edit")
                columns = table.findall("s:tableColumns/s:tableColumn", NS)
                index = col - start_col
                if (
                    index >= len(columns)
                    or columns[index].find("s:calculatedColumnFormula", NS) is not None
                ):
                    raise ValueError(
                        "Calculated table columns require a table-aware edit"
                    )

    def _check_cell_features(self, cell: etree._Element | None) -> None:
        if cell is not None:
            if cell.get("cm") is not None or cell.get("vm") is not None:
                raise ValueError("Cell metadata requires a metadata-aware edit")
            if self.book._value(cell).get("rich_text"):
                raise ValueError(
                    "Rich text requires a run-aware edit to preserve formatting"
                )
            if any(
                child.tag not in {_tag("f"), _tag("v"), _tag("is")} for child in cell
            ):
                raise ValueError(
                    "Unknown cell features require a dedicated edit operation"
                )
