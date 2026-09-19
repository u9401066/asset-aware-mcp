"""Explicit table membership at insertion boundaries, separate from cell movement."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from src.infrastructure.native_grid_filters import shift_filters
from src.infrastructure.native_grid_xml import Rectangle
from src.infrastructure.native_spreadsheet_reader import NS

if TYPE_CHECKING:
    from src.domain.native_grid import GridTransform, NativeTableExpansion
    from src.infrastructure.native_grid_table_state import GridTableState


def table_destination(
    state: GridTableState,
    transform: GridTransform,
    expansion: NativeTableExpansion | None,
) -> Rectangle | None:
    before = state.bounds
    after = before.shift(transform)
    if expansion is None:
        return after
    if Rectangle.parse(expansion.expected_ref) != before:
        raise ValueError("Table expansion expected_ref is stale in this grid step")
    edit = transform.edit
    if edit.operation != "insert":
        raise ValueError("Table expansion requires insertion")
    if edit.axis == "row":
        boundaries = {
            before.first_row + state.headers,
            before.last_row - state.totals + 1,
        }
    else:
        boundaries = {before.first_column, before.last_column + 1}
    if edit.at not in boundaries:
        raise ValueError(
            "Table expansion must insert at a data/column boundary; insert before totals"
        )
    last = getattr(before, "last_" + edit.axis) + edit.count
    if last > edit.limit:
        raise ValueError("Table expansion exceeds worksheet bounds")
    return replace(before, **{"last_" + edit.axis: last})


def shift_table_filters(
    state: GridTableState,
    transform: GridTransform,
    before_table: Rectangle,
) -> None:
    axis = transform.edit.axis
    after_table = state.bounds
    grew = getattr(after_table, "last_" + axis) - getattr(
        after_table, "first_" + axis
    ) > getattr(before_table, "last_" + axis) - getattr(before_table, "first_" + axis)
    if transform.edit.operation != "insert" or not grew:
        shift_filters(state.root, transform)
        return
    # A table-owned filter/sort range includes inserted cells at its selected
    # edge; ordinary worksheet ranges retain ordinary coordinate semantics.
    nodes = list(
        state.root.xpath(
            ".//s:autoFilter | .//s:sortState | .//s:sortCondition", namespaces=NS
        )
    )
    overrides = []
    for node in nodes:
        if node.tag.endswith("}sortCondition") and axis == "column":
            continue  # A sort key stays attached to its original column.
        before = Rectangle.parse(node.get("ref", ""))
        first, last = (
            getattr(before, "first_" + transform.edit.axis),
            getattr(before, "last_" + transform.edit.axis),
        )
        if first <= transform.edit.at <= last + 1:
            after = replace(
                before, **{"last_" + transform.edit.axis: last + transform.edit.count}
            )
            overrides.append((node, before, after))
    shift_filters(state.root, transform)
    for node, before, after in overrides:
        if transform.edit.axis == "column":
            shifted = before.shift(transform)
            assert shifted is not None
            for column in node.findall("s:filterColumn", NS):
                column.set(
                    "colId",
                    str(
                        int(column.get("colId", "-1"))
                        + shifted.first_column
                        - after.first_column
                    ),
                )
        node.set("ref", after.text)
