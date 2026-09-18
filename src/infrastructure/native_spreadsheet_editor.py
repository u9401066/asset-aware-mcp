"""Transactional cell edits with scoped OOXML repairs and read-back verification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lxml import etree

from src.domain.native_assets import (
    MAX_NATIVE_CELLS,
    NativeCellEdit,
    NativeEditResult,
    cell_position,
)
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_spreadsheet_guards import NativeCellGuards
from src.infrastructure.native_spreadsheet_reader import (
    NS,
    XML_SPACE,
    _encode_text,
    _tag,
)
from src.infrastructure.native_spreadsheet_repairs import (
    remove_calculation_chain,
    repair_shared_strings,
    request_recalculation,
)

if TYPE_CHECKING:
    from src.infrastructure.native_spreadsheet_reader import NativeSpreadsheetReader


class NativeSpreadsheetEditor:
    def __init__(self, book: NativeSpreadsheetReader):
        self.book = book
        self.guards = NativeCellGuards(book)

    def edit(self, edits: list[NativeCellEdit]) -> tuple[bytes, NativeEditResult]:
        if not 1 <= len(edits) <= MAX_NATIVE_CELLS:
            raise ValueError("A cell transaction requires 1-20000 edits")
        if len({(edit.sheet, edit.cell) for edit in edits}) != len(edits):
            raise ValueError("A transaction cannot edit the same cell twice")
        roots, changes = self._apply_edits(edits)
        replacements = {}
        changed_sheets = {change["sheet"] for change in changes}
        for name in changed_sheets:
            self._dimension(roots[name])
            replacements[self.book.sheets[name]["part"]] = xml_bytes(roots[name])
        repairs: list[str] = []
        removed: set[str] = set()
        if changes:
            repair_shared_strings(self.book, replacements, repairs, roots)
            request_recalculation(self.book, replacements, repairs)
            remove_calculation_chain(self.book, replacements, repairs, removed)
        return self._finish(replacements, removed, changes, changed_sheets, repairs)

    def _apply_edits(
        self, edits: list[NativeCellEdit]
    ) -> tuple[dict[str, etree._Element], list[dict[str, Any]]]:
        roots: dict[str, etree._Element] = {}
        rows_by_sheet: dict[str, dict[int, etree._Element]] = {}
        cells_by_sheet: dict[str, dict[str, etree._Element]] = {}
        changes = []
        for edit in sorted(
            edits, key=lambda item: (item.sheet, cell_position(item.cell))
        ):
            if edit.sheet not in roots:
                root = self.book._sheet(edit.sheet)
                roots[edit.sheet] = root
                rows_by_sheet[edit.sheet] = {
                    int(row.get("r", "0")): row
                    for row in root.findall("s:sheetData/s:row", NS)
                }
                cells_by_sheet[edit.sheet] = {
                    cell.get("r", ""): cell
                    for cell in root.findall("s:sheetData/s:row/s:c", NS)
                }
                guard_count = (
                    len(root.findall("s:mergeCells/s:mergeCell", NS))
                    + len(root.xpath("./s:sheetData/s:row/s:c/s:f[@t]", namespaces=NS))
                    + len(root.findall("s:tableParts/s:tablePart", NS))
                )
                if guard_count * len(edits) > 1_000_000:
                    raise ValueError(
                        "Worksheet constraint budget exceeded; use a smaller edit batch"
                    )
            change = self._set_cell(
                roots[edit.sheet],
                edit,
                rows_by_sheet[edit.sheet],
                cells_by_sheet[edit.sheet],
            )
            if change:
                changes.append(change)
        return roots, changes

    def _set_cell(
        self,
        root: etree._Element,
        edit: NativeCellEdit,
        rows: dict[int, etree._Element],
        cells: dict[str, etree._Element],
    ) -> dict[str, Any] | None:
        cell = cells.get(edit.cell)
        before = self.book._value(cell)
        if before["kind"] == edit.kind and before["value"] == edit.value:
            return None
        self.guards.check(root, edit.cell, cell, edit.sheet)
        cell = self._ensure_cell(root, edit, rows, cells)
        original_attributes = dict(cell.attrib)
        for child in list(cell):
            cell.remove(child)
        cell.attrib.pop("t", None)
        if edit.kind == "string":
            cell.set("t", "inlineStr")
            string = etree.SubElement(cell, _tag("is"))
            text = etree.SubElement(string, _tag("t"))
            text.set(XML_SPACE, "preserve")
            text.text = _encode_text(str(edit.value))
        elif edit.kind == "boolean":
            cell.set("t", "b")
            etree.SubElement(cell, _tag("v")).text = "1" if edit.value else "0"
        elif edit.kind == "number":
            etree.SubElement(cell, _tag("v")).text = str(edit.value)
        elif edit.kind == "formula":
            etree.SubElement(cell, _tag("f")).text = str(edit.value)[1:]
        if {k: v for k, v in cell.attrib.items() if k != "t"} != {
            k: v for k, v in original_attributes.items() if k != "t"
        }:
            raise ValueError("Cell style/metadata preservation failed")
        return {
            "sheet": edit.sheet,
            "cell": edit.cell,
            "before": before,
            "after": self.book._value(cell),
        }

    @staticmethod
    def _ensure_cell(
        root: etree._Element,
        edit: NativeCellEdit,
        rows: dict[int, etree._Element],
        cells: dict[str, etree._Element],
    ) -> etree._Element:
        sheet_data = root.find("s:sheetData", NS)
        assert sheet_data is not None
        row_number, column = cell_position(edit.cell)
        row = rows.get(row_number)
        cell = cells.get(edit.cell)
        if row is None:
            row = etree.Element(_tag("row"), r=str(row_number))
            later = len(sheet_data)
            if len(sheet_data) and int(sheet_data[-1].get("r", "0")) > row_number:
                later = next(
                    i
                    for i, item in enumerate(sheet_data)
                    if int(item.get("r", "0")) > row_number
                )
            sheet_data.insert(later, row)
            rows[row_number] = row
        if cell is None:
            cell = etree.Element(_tag("c"), r=edit.cell)
            later = next(
                (
                    i
                    for i, item in enumerate(row)
                    if item.tag == _tag("c")
                    and cell_position(item.get("r", ""))[1] > column
                ),
                len(row),
            )
            row.insert(later, cell)
            cells[edit.cell] = cell
        return cell

    @staticmethod
    def _dimension(root: etree._Element) -> None:
        # spans is an optional optimization shared by groups of sixteen rows;
        # remove this cache after an edit rather than retain stale column bounds.
        for row in root.findall("s:sheetData/s:row", NS):
            row.attrib.pop("spans", None)
        addresses = [c.get("r", "") for c in root.findall("s:sheetData/s:row/s:c", NS)]
        dimension = root.find("s:dimension", NS)
        if dimension is not None and addresses:
            # Use a safe bounding rectangle; styles on otherwise blank cells count.
            positions = [cell_position(address) for address in addresses]

            def coordinate(row: int, column: int) -> str:
                letters = ""
                while column:
                    column, remainder = divmod(column - 1, 26)
                    letters = chr(65 + remainder) + letters
                return f"{letters}{row}"

            first = coordinate(
                min(p[0] for p in positions), min(p[1] for p in positions)
            )
            last = coordinate(
                max(p[0] for p in positions), max(p[1] for p in positions)
            )
            dimension.set("ref", first if first == last else f"{first}:{last}")

    def _finish(
        self,
        replacements: dict[str, bytes],
        removed: set[str],
        changes: list[dict[str, Any]],
        changed_sheets: set[str],
        repairs: list[str],
    ) -> tuple[bytes, NativeEditResult]:
        data = self.book.package.replace(replacements, removed)
        reloaded = type(self.book)(data)
        checked_cells = {
            name: {
                cell.get("r", ""): cell
                for cell in reloaded._sheet(name).findall("s:sheetData/s:row/s:c", NS)
            }
            for name in changed_sheets
        }
        for change in changes:
            cell = checked_cells[change["sheet"]][change["cell"]]
            if reloaded._value(cell) != change["after"]:
                raise ValueError("Saved cell does not match the requested result")
        changed_parts = sorted(set(replacements) | removed)
        return data, NativeEditResult(
            changed_parts=changed_parts,
            preserved_parts=len(self.book.package.parts) - len(changed_parts),
            changes=changes,
            checks=[
                "bounded_package_read",
                "unrelated_parts_byte_identical",
                "cell_styles_preserved",
                "saved_cell_values_match",
            ],
            repairs=repairs,
        )
