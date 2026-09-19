"""Freeze a retained totals cell's own Table selectors before losing its role."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.native_grid_tables import GridTableChange
from src.infrastructure.native_grid_formulas import _names, _ranges
from src.infrastructure.native_grid_source_ranges import table_bounds
from src.infrastructure.native_grid_structured import _parse
from src.infrastructure.native_grid_xml import Rectangle
from src.infrastructure.native_workbook_formulas import (
    _qualifier_spans,
    _range_operands,
)

if TYPE_CHECKING:
    from src.infrastructure.native_grid_table_state import GridTableState


def freeze_totals_formula(text: str, state: GridTableState, sheet: str) -> str:
    lookup = {
        name.casefold(): GridTableChange(name, state.columns, state.columns)
        for name in {state.name, state.root.get("name", "")} - {""}
    }
    changes = []
    for start, end, value in _ranges(text):
        parsed = []
        external = False
        for operand in _range_operands(value):
            item = _parse(operand, lookup, state.name, external)
            external = item.external
            parsed.append(item)
        if not any(p.change is not None for p in parsed):
            continue
        if len(parsed) > 2 or any(p.change is None for p in parsed):
            raise ValueError(
                "Retained totals formulas need explicit resolution of mixed/chained ranges"
            )
        rectangles = []
        for index, item in enumerate(parsed):
            if (index and item.original.startswith("@")) or (
                index < len(parsed) - 1 and item.original.endswith("#")
            ):
                raise ValueError(
                    "Modified range endpoints need explicit formula resolution"
                )
            operand = item.original.removeprefix("@")
            for left, right in _qualifier_spans(operand):
                names = _names(operand[left:right])
                if (
                    names is None
                    or len(names) != 1
                    or names[0].casefold() != sheet.casefold()
                ):
                    raise ValueError(
                        "Retained Table formula has a conflicting worksheet qualifier"
                    )
            rectangles.append(
                table_bounds(
                    state,
                    item.spec or "",
                    source_name=False,
                    current_row=state.bounds.last_row,
                )
            )
        bounds = Rectangle(
            min(r.first_row for r in rectangles),
            min(r.first_column for r in rectangles),
            max(r.last_row for r in rectangles),
            max(r.last_column for r in rectangles),
        )
        qualifier = "'" + sheet.replace("'", "''") + "'!"

        def absolute(location: str) -> str:
            at = next(i for i, char in enumerate(location) if char.isdigit())
            return "$" + location[:at] + "$" + location[at:]

        reference = qualifier + ":".join(absolute(p) for p in bounds.text.split(":"))
        if value.startswith("@"):
            reference = "@" + reference
        if value.endswith("#"):
            reference += "#"
        changes.append((start, end, reference))
    for start, end, value in reversed(changes):
        text = text[:start] + value + text[end:]
    return text
