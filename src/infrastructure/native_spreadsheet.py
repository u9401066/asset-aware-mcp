"""Native spreadsheet format adapter; parsing and editing have separate responsibilities."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

import xlsxwriter

from src.infrastructure.native_spreadsheet_editor import NativeSpreadsheetEditor
from src.infrastructure.native_spreadsheet_reader import NativeSpreadsheetReader

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeCellEdit,
        NativeCellLocator,
        NativeEditResult,
        NativeWorkbookCreate,
    )


class NativeSpreadsheet(NativeSpreadsheetReader):
    def edit(self, edits: list[NativeCellEdit]) -> tuple[bytes, NativeEditResult]:
        return NativeSpreadsheetEditor(self).edit(edits)


def create_native_workbook(request: NativeWorkbookCreate) -> bytes:
    output = io.BytesIO()
    with xlsxwriter.Workbook(
        output,
        {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False},
    ) as workbook:
        for name in request.sheets:
            workbook.add_worksheet(name)
    data = output.getvalue()
    # Apply typed values through the same checked path as later edits. This
    # avoids distinct formula/string escaping behavior during initial creation.
    spreadsheet = NativeSpreadsheet(data)
    if request.edits:
        data, _ = spreadsheet.edit(request.edits)
    return data


class SpreadsheetFileAdapter:
    """Format port used by the application layer; parsing remains infrastructure."""

    def read_cell_by_locator(
        self, data: bytes, locator: NativeCellLocator
    ) -> dict[str, Any]:
        book = NativeSpreadsheet(data)
        expected_sheet = locator.model_dump(exclude={"cell"})
        matching = [
            name for name, info in book.sheets.items() if info == expected_sheet
        ]
        if len(matching) != 1:
            raise ValueError(
                "Native cell locator does not match one worksheet in this revision"
            )
        return book.read_cell(matching[0], locator.cell)

    def read_cell(self, data: bytes, sheet: str, cell: str) -> dict[str, Any]:
        return NativeSpreadsheet(data).read_cell(sheet, cell)

    def inspect(
        self, data: bytes, *, sheet: str | None, offset: int, limit: int
    ) -> dict[str, Any]:
        return NativeSpreadsheet(data).inspect(sheet=sheet, offset=offset, limit=limit)

    def create(self, request: NativeWorkbookCreate) -> bytes:
        return create_native_workbook(request)

    def edit(
        self, data: bytes, edits: list[NativeCellEdit]
    ) -> tuple[bytes, NativeEditResult]:
        return NativeSpreadsheet(data).edit(edits)
