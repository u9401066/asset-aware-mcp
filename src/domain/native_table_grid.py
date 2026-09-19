"""Identity-based A2T grid plans and exact sequential correspondence checks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from src.domain.native_asset_models import cell_position, column_letters
from src.domain.native_grid import NativeGridEdit, NativeGridUpdate
from src.domain.native_table_workspace import NativeTableProjection

if TYPE_CHECKING:
    from src.domain.table_entities import TableContext


def grid_axes(context: TableContext) -> list[tuple[str, list[str], list[str], int]]:
    binding = context.native_binding
    if (
        binding is None
        or not binding.column_ids
        or (context.columns and not context.column_ids)
    ):
        raise ValueError("Structural application requires bound column identities")
    if any(column.type != "native" for column in context.columns):
        raise ValueError("Structural native workspaces require tagged native columns")
    first_row, first_column = cell_position(binding.projection.start_cell)
    return [
        ("row", binding.row_ids, context.row_ids, first_row),
        ("column", binding.column_ids, context.column_ids, first_column),
    ]


def _axis_plan(
    axis: Literal["row", "column"], before: list[str], after: list[str], start: int
) -> list[NativeGridEdit]:
    old, new = set(before), set(after)
    if len(old) != len(before) or len(new) != len(after):
        raise ValueError("Grid correspondence requires unique identities")
    if [value for value in before if value in new] != [
        value for value in after if value in old
    ]:
        raise ValueError("Reordered source identities require native move semantics")
    edits = []
    left = right = position = 0
    while left < len(before) or right < len(after):
        if left < len(before) and before[left] not in new:
            end = left
            while end < len(before) and before[end] not in new and end - left < 1024:
                end += 1
            edits.append(
                NativeGridEdit(
                    axis=axis,
                    operation="delete",
                    at=start + position,
                    count=end - left,
                    merged_anchor="delete",
                )
            )
            left = end
        elif right < len(after) and after[right] not in old:
            end = right
            while end < len(after) and after[end] not in old and end - right < 1024:
                end += 1
            edits.append(
                NativeGridEdit(
                    axis=axis,
                    operation="insert",
                    at=start + position,
                    count=end - right,
                )
            )
            position += end - right
            right = end
        else:
            left += 1
            right += 1
            position += 1
    return edits


def proposed_grid(context: TableContext) -> NativeGridUpdate | None:
    axes = grid_axes(context)
    edits = []
    for axis, before, after, start in axes:
        edits.extend(
            _axis_plan("row" if axis == "row" else "column", before, after, start)
        )
    if not edits:
        return None
    assert context.native_binding is not None
    return NativeGridUpdate(
        worksheet=context.native_binding.projection.worksheet, edits=edits
    )


def validate_grid(context: TableContext, grid: NativeGridUpdate) -> None:
    """Require each surviving identity and every new slot at the exact destination."""
    axes = grid_axes(context)
    assert context.native_binding is not None
    if grid.worksheet != context.native_binding.projection.worksheet:
        raise ValueError("Grid worksheet does not match the native source binding")
    for axis, before, after, start in axes:
        mapped: list[int | None] = list(range(len(before)))
        for edit in grid.edits:
            if edit.axis != axis:
                continue
            offset = edit.at - start
            if offset < 0 or offset > len(mapped):
                raise ValueError("Grid edit is outside the projected range")
            if edit.operation == "insert":
                mapped[offset:offset] = [None] * edit.count
            else:
                if offset + edit.count > len(mapped):
                    raise ValueError("Grid deletion exceeds the projected range")
                del mapped[offset : offset + edit.count]
        positions = {identity: index for index, identity in enumerate(before)}
        if mapped != [positions.get(identity) for identity in after]:
            raise ValueError(
                "Grid edits do not match the workspace row/column identities"
            )


def destination_projection(context: TableContext) -> NativeTableProjection | None:
    assert context.native_binding is not None
    if not context.rows or not context.columns:
        return None
    source = context.native_binding.projection
    first_row, first_col = cell_position(source.start_cell)
    return NativeTableProjection(
        worksheet=source.worksheet,
        start_cell=source.start_cell,
        end_cell=column_letters(first_col + len(context.columns) - 1)
        + str(first_row + len(context.rows) - 1),
        title=source.title,
    )


def grid_plan_record(context: TableContext) -> dict[str, Any]:
    try:
        grid = proposed_grid(context)
        destination = destination_projection(context)
    except ValueError as exc:
        return {"status": "unavailable", "reason": str(exc)}
    return {
        "status": "required" if grid else "unchanged",
        "worksheet_grid": grid.model_dump(exclude_none=True) if grid else None,
        "destination": destination.model_dump() if destination else None,
        "scope": "Whole worksheet rows/columns move, including content outside the projection. Deleted identities discard their merged anchors. Native table membership follows explicit grid coordinates; insertion beyond a table edge does not expand that table. Review references, table membership and geometry before applying.",
        "formula_policy": "Unchanged source cells follow native grid relocation. Edited/new formulas are expressed in destination coordinates. Missing new values are blank; historical references never migrate.",
    }
