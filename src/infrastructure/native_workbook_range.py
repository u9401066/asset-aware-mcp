"""Read a bounded dense rectangle once, preserving complete native cell records."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.native_asset_models import cell_position
from src.domain.native_table_workspace import column_letters
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_package import (
    WORKSHEET_REL,
    NativeWorkbookPackage,
)

if TYPE_CHECKING:
    from src.domain.native_table_workspace import NativeTableProjection


class NativeWorkbookRange:
    def read_range(
        self, data: bytes, projection: NativeTableProjection
    ) -> list[list[dict[str, Any]]]:
        book = NativeWorkbookPackage(data)
        sheet = book.match(projection.worksheet)
        if sheet["kind"] != WORKSHEET_REL:
            raise ValueError("Only native worksheets expose rectangular cell ranges")
        root = book._sheet(sheet["name"])
        nodes = {
            cell.get("r"): cell for cell in root.findall("s:sheetData/s:row/s:c", NS)
        }
        first_row, first_col = cell_position(projection.start_cell)
        last_row, last_col = cell_position(projection.end_cell)
        result = []
        for row in range(first_row, last_row + 1):
            cells = []
            for col in range(first_col, last_col + 1):
                address = f"{column_letters(col)}{row}"
                cells.append(
                    {
                        "sheet": sheet["name"],
                        "cell": address,
                        "locator": {**book.sheets[sheet["name"]], "cell": address},
                        **book._value(nodes.get(address)),
                    }
                )
            result.append(cells)
        return result
