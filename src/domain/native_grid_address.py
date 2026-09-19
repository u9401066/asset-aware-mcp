"""Parse and transform A1 references without losing absolute flags or row ranges."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.native_asset_models import cell_position, column_letters

if TYPE_CHECKING:
    from src.domain.native_grid import GridTransform

CELL = re.compile(r"(\$?)([A-Za-z]{1,3})(\$?)([1-9][0-9]{0,6})\Z")
COLUMN = re.compile(r"(\$?)([A-Za-z]{1,3})\Z")
ROW = re.compile(r"(\$?)([1-9][0-9]{0,6})\Z")


@dataclass(frozen=True)
class GridAddress:
    row: int | None
    column: int | None
    row_absolute: str = ""
    column_absolute: str = ""
    column_spelling: str = ""

    def text(self, row: int | None = None, column: int | None = None) -> str:
        value = ""
        if self.column is not None:
            letters = column_letters(self.column if column is None else column)
            if column is None or column == self.column:
                letters = self.column_spelling or letters
            elif self.column_spelling.islower():
                letters = letters.lower()
            value = self.column_absolute + letters
        if self.row is not None:
            value += self.row_absolute + str(self.row if row is None else row)
        return value


def parse_address(text: str, *, whole: bool = False) -> GridAddress | None:
    matched = CELL.fullmatch(text)
    if matched:
        col_abs, letters, row_abs, number = matched.groups()
        try:
            row, column = cell_position(letters.upper() + number)
        except ValueError:
            return None  # Out-of-grid identifiers can be defined names.
        return GridAddress(row, column, row_abs, col_abs, letters)
    if whole and (matched := COLUMN.fullmatch(text)):
        absolute, letters = matched.groups()
        try:
            _, column = cell_position(letters.upper() + "1")
        except ValueError:
            return None
        return GridAddress(
            None, column, column_absolute=absolute, column_spelling=letters
        )
    if whole and (matched := ROW.fullmatch(text)):
        absolute, number = matched.groups()
        if int(number) <= 1_048_576:
            return GridAddress(int(number), None, row_absolute=absolute)
    return None


def transform_reference(text: str, transform: GridTransform) -> str | None:
    """Return a shifted reference, #REF! for deletion, or None for a named operand."""
    parts = re.split(r"\s*:\s*", text)
    if len(parts) not in {1, 2}:
        if any(parse_address(part, whole=True) is not None for part in parts):
            raise ValueError(
                "Chained coordinate range requires an explicit range resolver"
            )
        return None
    endpoints = [parse_address(part, whole=len(parts) == 2) for part in parts]
    if any(point is None for point in endpoints):
        if any(point is not None for point in endpoints):
            raise ValueError(
                "Mixed named/coordinate range requires an explicit range resolver"
            )
        return None
    first, last = endpoints[0], endpoints[-1]
    assert first is not None and last is not None
    if (first.row is None) != (last.row is None) or (first.column is None) != (
        last.column is None
    ):
        raise ValueError("Mixed cell/row/column range endpoints")
    axis = transform.edit.axis
    left, right = getattr(first, axis), getattr(last, axis)
    if left is None:
        return text  # E.g. whole-column A:A is unaffected by row insertion.
    reverse = left > right
    span = transform.span(min(left, right), max(left, right), clip=True)
    if span is None:
        return "#REF!"
    left, right = reversed(span) if reverse else span
    result = [first.text(**{axis: left})]
    if len(parts) == 2:
        result.append(last.text(**{axis: right}))
    separator = re.search(r"\s*:\s*", text)
    return (separator[0] if separator else ":").join(result)


def translate_reference(text: str, rows: int, columns: int) -> str | None:
    """Translate relative A1 coordinates when materializing a shared formula."""
    parts = re.split(r"\s*:\s*", text)
    if len(parts) not in {1, 2}:
        if any(parse_address(part, whole=True) is not None for part in parts):
            raise ValueError(
                "Chained coordinate range requires an explicit range resolver"
            )
        return None
    endpoints = [parse_address(part, whole=len(parts) == 2) for part in parts]
    if any(point is None for point in endpoints):
        if any(point is not None for point in endpoints):
            raise ValueError(
                "Mixed named/coordinate range requires an explicit range resolver"
            )
        return None
    result = []
    for point in endpoints:
        assert point is not None
        row = point.row
        col = point.column
        if row is not None and not point.row_absolute:
            row += rows
        if col is not None and not point.column_absolute:
            col += columns
        if (row is not None and not 1 <= row <= 1_048_576) or (
            col is not None and not 1 <= col <= 16_384
        ):
            return "#REF!"
        result.append(point.text(row, col))
    separator = re.search(r"\s*:\s*", text)
    return (separator[0] if separator else ":").join(result)
