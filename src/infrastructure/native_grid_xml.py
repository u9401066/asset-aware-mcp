"""Strict stored worksheet coordinates shared by native grid patch stages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.native_asset_models import cell_position, column_letters
from src.domain.native_grid_address import parse_address
from src.infrastructure.native_ooxml import SHEET_NS
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from lxml import etree

    from src.domain.native_grid import GridTransform
    from src.domain.native_grid_geometry import GeometryTransform

MAX_GRID_CELLS = 200_000


def tag(name: str) -> str:
    return f"{{{SHEET_NS}}}{name}"


def address(row: int, column: int) -> str:
    if not 1 <= row <= 1_048_576:
        raise ValueError("Invalid worksheet row coordinate")
    return column_letters(column) + str(row)


@dataclass(frozen=True)
class Rectangle:
    first_row: int
    first_column: int
    last_row: int
    last_column: int

    @classmethod
    def parse(cls, value: str) -> Rectangle:
        parts = value.split(":")
        if len(parts) not in {1, 2}:
            raise ValueError("Invalid stored worksheet range")
        points = [parse_address(part) for part in parts]
        if any(point is None for point in points):
            raise ValueError("Invalid stored worksheet range")
        first_point, last_point = points[0], points[-1]
        assert first_point is not None and last_point is not None
        assert first_point.row is not None and first_point.column is not None
        assert last_point.row is not None and last_point.column is not None
        first = first_point.row, first_point.column
        last = last_point.row, last_point.column
        if first[0] > last[0] or first[1] > last[1]:
            raise ValueError("Reversed stored worksheet range")
        return cls(*first, *last)

    @property
    def anchor(self) -> str:
        return address(self.first_row, self.first_column)

    @property
    def text(self) -> str:
        last = address(self.last_row, self.last_column)
        return self.anchor if last == self.anchor else self.anchor + ":" + last

    def contains(self, cell: str) -> bool:
        row, column = cell_position(cell)
        return (
            self.first_row <= row <= self.last_row
            and self.first_column <= column <= self.last_column
        )

    def overlaps(self, other: Rectangle) -> bool:
        return (
            self.first_row <= other.last_row
            and other.first_row <= self.last_row
            and self.first_column <= other.last_column
            and other.first_column <= self.last_column
        )

    def shift(
        self, transform: GridTransform, *, clip: bool = False
    ) -> Rectangle | None:
        axis = transform.edit.axis
        result = transform.span(
            getattr(self, "first_" + axis), getattr(self, "last_" + axis), clip=clip
        )
        if result is None:
            return None
        if axis == "row":
            return Rectangle(result[0], self.first_column, result[1], self.last_column)
        return Rectangle(self.first_row, result[0], self.last_row, result[1])


def cell_map(root: etree._Element) -> dict[str, etree._Element]:
    rows = root.findall("s:sheetData/s:row", NS)
    if len(root.findall("s:sheetData", NS)) != 1 or len(rows) > MAX_GRID_CELLS:
        raise ValueError("Missing/ambiguous sheetData or worksheet row budget exceeded")
    result: dict[str, etree._Element] = {}
    seen: set[int] = set()
    for row in rows:
        number = int(row.get("r", "0"))
        if not 1 <= number <= 1_048_576 or number in seen:
            raise ValueError("Invalid or duplicate worksheet row coordinate")
        seen.add(number)
        for cell in row.findall("s:c", NS):
            locator = cell.get("r", "")
            if cell_position(locator)[0] != number or locator in result:
                raise ValueError("Invalid or duplicate worksheet cell coordinate")
            result[locator] = cell
            if len(result) > MAX_GRID_CELLS:
                raise ValueError("Native grid exceeds the stored-cell budget")
    return result


def shift_cell(
    value: str, transform: GeometryTransform, *, clamp: bool = False
) -> str | None:
    row, column = cell_position(value)
    point = transform.point(
        row if transform.edit.axis == "row" else column, clamp=clamp
    )
    if point is None:
        return None
    return (
        address(point, column) if transform.edit.axis == "row" else address(row, point)
    )
