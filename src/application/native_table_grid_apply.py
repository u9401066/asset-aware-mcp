"""Apply one frozen A2T structure/value intent before a single native CAS commit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_table_projection import native_value
from src.domain.native_asset_models import NativeCellEdit, NativeEditResult
from src.domain.native_table_grid import destination_projection, validate_grid
from src.domain.native_table_workspace import NativeTableCellValue

if TYPE_CHECKING:
    from src.domain.native_assets import NativeSpreadsheetAdapter
    from src.domain.native_grid import NativeGridAdapter, NativeGridUpdate
    from src.domain.native_table_workspace import NativeTableRangeReader
    from src.domain.table_entities import TableContext


def _intent(
    context: TableContext,
    source: list[list[dict[str, Any]]],
    relocated: list[list[dict[str, Any]]],
) -> tuple[list[NativeCellEdit], list[list[NativeTableCellValue]]]:
    binding = context.native_binding
    assert binding is not None
    rows = {identity: index for index, identity in enumerate(binding.row_ids)}
    columns = {identity: index for index, identity in enumerate(binding.column_ids)}
    edits, expected = [], []
    for row_index, (identity, row) in enumerate(
        zip(context.row_ids, context.rows, strict=True)
    ):
        values = []
        for column_index, (column_id, column) in enumerate(
            zip(context.column_ids, context.columns, strict=True)
        ):
            requested = native_value(row.get(column.name))
            actual = NativeTableCellValue.from_record(
                relocated[row_index][column_index]
            )
            old_row, old_column = rows.get(identity), columns.get(column_id)
            inherited = (
                old_row is not None
                and old_column is not None
                and requested
                == NativeTableCellValue.from_record(source[old_row][old_column])
            )
            value = actual if inherited else requested
            values.append(value)
            if value != actual:
                record = relocated[row_index][column_index]
                edits.append(
                    NativeCellEdit.model_validate(
                        {
                            "sheet": record["sheet"],
                            "cell": record["cell"],
                            **value.model_dump(),
                        }
                    )
                )
            elif not inherited and value.kind == "source_only":
                raise ValueError(
                    "New source-only values cannot manufacture native payloads"
                )
        expected.append(values)
    return edits, expected


class NativeTableGridApply:
    def __init__(
        self,
        grid: NativeGridAdapter,
        cells: NativeSpreadsheetAdapter,
        ranges: NativeTableRangeReader,
    ):
        self.grid, self.cells, self.ranges = grid, cells, ranges

    def apply(
        self,
        data: bytes,
        context: TableContext,
        request: NativeGridUpdate,
    ) -> tuple[bytes, NativeEditResult, int]:
        validate_grid(context, request)
        destination = destination_projection(context)
        assert context.native_binding is not None
        source = self.ranges.read_range(data, context.native_binding.projection)
        updated, result = self.grid.update(data, request)
        if destination is None:
            return updated, result, 0
        relocated = self.ranges.read_range(updated, destination)
        edits, expected = _intent(context, source, relocated)
        if edits:
            updated, values = self.cells.edit(updated, edits)
            result = _combined(result, values)
        final = self.ranges.read_range(updated, destination)
        actual = [
            [NativeTableCellValue.from_record(record) for record in row]
            for row in final
        ]
        if actual != expected:
            raise ValueError(
                "Structural A2T destination readback disagrees with the frozen intent"
            )
        edited = {edit.cell for edit in edits}
        for old_row, new_row in zip(relocated, final, strict=True):
            for old, new in zip(old_row, new_row, strict=True):
                if old["cell"] not in edited and old != new:
                    raise ValueError("Unedited structural cell representation changed")
                if old.get("style_index") != new.get("style_index"):
                    raise ValueError(
                        "Structural cell formatting changed during value editing"
                    )
        result.checks.append("complete_structural_workspace_values_read_back")
        result.review_required.append("projected_range_and_native_table_membership")
        return updated, result, len(edits)


def _combined(grid: NativeEditResult, values: NativeEditResult) -> NativeEditResult:
    additional = set(values.changed_parts) - set(grid.changed_parts)
    return NativeEditResult(
        changed_parts=sorted(set(grid.changed_parts) | set(values.changed_parts)),
        preserved_parts=max(0, grid.preserved_parts - len(additional)),
        changes=[*grid.changes, *values.changes],
        checks=list(dict.fromkeys([*grid.checks, *values.checks])),
        repairs=list(dict.fromkeys([*grid.repairs, *values.repairs])),
        review_required=list(
            dict.fromkeys([*grid.review_required, *values.review_required])
        ),
    )
