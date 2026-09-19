"""Lossless typed values and checked source correspondence for table workspaces."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import TYPE_CHECKING, Any

from src.domain.native_asset_models import (
    MAX_NATIVE_CELLS,
    NativeCellEdit,
    NativeWorkbookCreate,
    cell_position,
)
from src.domain.native_file_reference import NativeFileReference
from src.domain.native_table_workspace import (
    NativeTableBinding,
    NativeTableCellValue,
    column_letters,
)
from src.domain.table_entities import ColumnDef, TableContext
from src.domain.table_state import table_state

if TYPE_CHECKING:
    from src.domain.native_table_workspace import (
        NativeTableProjection,
        NativeTableWorkbookCreate,
    )


def canonical_table(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Table workspace requires finite UTF-8 JSON values") from exc
    if len(encoded) > 16 * 1024 * 1024:
        raise ValueError("Table workspace exceeds the 16 MiB budget")
    return encoded


def workspace_bytes(context: TableContext) -> bytes:
    return canonical_table(table_state(context))


def workspace_hash(context: TableContext) -> str:
    return hashlib.sha256(workspace_bytes(context)).hexdigest()


def projected_context(
    asset_id: str,
    revision: str,
    projection: NativeTableProjection,
    records: list[list[dict[str, Any]]],
) -> TableContext:
    _row, first_col = cell_position(projection.start_cell)
    _row, last_col = cell_position(projection.end_cell)
    columns = [column_letters(col) for col in range(first_col, last_col + 1)]
    context = TableContext(
        id="tbl_" + uuid.uuid4().hex,
        title=projection.title,
        intent="summary",
        columns=[
            ColumnDef(name=name, type="native", required=False) for name in columns
        ],
        rows=[
            {
                name: NativeTableCellValue.from_record(cell).model_dump()
                for name, cell in zip(columns, row, strict=True)
            }
            for row in records
        ],
        source_description=f"Native range {asset_id}@{revision}: {projection.start_cell}:{projection.end_cell}",
    )
    context.native_binding = NativeTableBinding(
        source=NativeFileReference(asset_id=asset_id, revision=revision),
        projection=projection,
        row_ids=list(context.row_ids),
        columns=columns,
        column_ids=list(context.column_ids),
    )
    return context


def native_value(value: Any) -> NativeTableCellValue:
    return (
        NativeTableCellValue(kind="blank", value=None)
        if value is None
        else NativeTableCellValue.model_validate(value)
    )


def matching_grid(context: TableContext) -> bool:
    binding = context.native_binding
    return bool(
        binding
        and context.row_ids == binding.row_ids
        and (
            context.column_ids == binding.column_ids
            if binding.column_ids
            else context.column_names == binding.columns
            and not (
                context.change_log
                and any(
                    entry.operation in {"add_column", "remove_column", "rename_column"}
                    for entry in context.change_log.entries
                )
            )
        )
        and all(column.type == "native" for column in context.columns)
    )


def projection_edits(
    context: TableContext, records: list[list[dict[str, Any]]]
) -> list[NativeCellEdit]:
    if not matching_grid(context):
        raise ValueError(
            "Native table row/column correspondence changed; source grid restructuring requires a dedicated workflow. Independent workbook creation remains available"
        )
    edits = []
    for row, original in zip(context.rows, records, strict=True):
        for column, source in zip(context.columns, original, strict=True):
            value = native_value(row.get(column.name))
            if value.kind == "native_generated":
                raise ValueError(
                    "native_generated requires structural native table generation"
                )
            if value == NativeTableCellValue.from_record(source):
                continue
            edits.append(
                NativeCellEdit.model_validate(
                    {
                        "sheet": source["sheet"],
                        "cell": source["cell"],
                        **value.model_dump(),
                    }
                )
            )
    return edits


def workbook_from_context(
    context: TableContext, destination: NativeTableWorkbookCreate
) -> tuple[NativeWorkbookCreate, dict[str, Any]]:
    if not context.columns or not context.rows:
        raise ValueError("Native table workbook creation requires columns and rows")
    if (len(context.rows) + int(destination.include_headers)) * len(
        context.columns
    ) > MAX_NATIVE_CELLS:
        raise ValueError("Table workbook exceeds the native cell budget")
    edits = []
    if destination.include_headers:
        for index, column in enumerate(context.columns, 1):
            edits.append(
                NativeCellEdit(
                    sheet=destination.sheet,
                    cell=column_letters(index) + "1",
                    kind="string",
                    value=column.name,
                )
            )
    first = 2 if destination.include_headers else 1
    for row_index, row in enumerate(context.rows, first):
        for index, column in enumerate(context.columns, 1):
            raw = row.get(column.name)
            if column.type == "native":
                value = native_value(raw)
            elif raw is None:
                value = NativeTableCellValue(kind="blank", value=None)
            elif type(raw) is bool:
                value = NativeTableCellValue(kind="boolean", value=raw)
            elif isinstance(raw, int | float):
                value = NativeTableCellValue(kind="number", value=raw)
            elif isinstance(raw, str):
                value = NativeTableCellValue(kind="string", value=raw)
            else:
                raise ValueError(
                    "Native workbook export requires scalar or explicitly tagged cell values"
                )
            if value.kind == "native_generated":
                raise ValueError(
                    "Resolve native_generated against a structural native table before export"
                )
            edits.append(
                NativeCellEdit.model_validate(
                    {
                        "sheet": destination.sheet,
                        "cell": column_letters(index) + str(row_index),
                        **value.model_dump(),
                    }
                )
            )
    request = NativeWorkbookCreate(
        name=destination.name, sheets=[destination.sheet], edits=edits
    )
    mapping = {
        "sheet": destination.sheet,
        "first_data_row": first,
        "row_ids": context.row_ids,
        "columns": [
            {"name": column.name, "native_column": column_letters(index)}
            for index, column in enumerate(context.columns, 1)
        ],
    }
    return request, mapping
