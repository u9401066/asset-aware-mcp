"""Typed A2T projections and immutable native workbook correspondence."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import Field, field_validator, model_validator

from src.domain.native_asset_models import (
    MAX_NATIVE_CELLS,
    NativeCellEdit,
    NativeModel,
    cell_position,
    validate_sheet_name,
)
from src.domain.native_file_reference import (
    NativeFileReference,  # noqa: TC001 -- schema
)
from src.domain.native_workbook import NativeWorksheetKey  # noqa: TC001 -- schema

if TYPE_CHECKING:
    from src.domain.table_entities import TableContext


def column_letters(index: int) -> str:
    if not 1 <= index <= 16_384:
        raise ValueError("Native column index is outside worksheet bounds")
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


class NativeTableCellValue(NativeModel):
    kind: Literal["string", "number", "boolean", "formula", "blank", "source_only"]
    value: str | int | float | bool | None

    @model_validator(mode="after")
    def checked_value(self) -> NativeTableCellValue:
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("Native table numbers must be finite")
        if self.kind != "source_only":
            NativeCellEdit(
                sheet="Projection", cell="A1", kind=self.kind, value=self.value
            )
        return self

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> NativeTableCellValue:
        try:
            return cls.model_validate(
                {"kind": record["kind"], "value": record["value"]}
            )
        except ValueError:
            return cls(kind="source_only", value=record["value"])


class NativeTableProjection(NativeModel):
    worksheet: NativeWorksheetKey
    start_cell: str = Field(min_length=2, max_length=10)
    end_cell: str = Field(min_length=2, max_length=10)
    title: str = Field(default="Native workbook range", min_length=1, max_length=200)

    @model_validator(mode="after")
    def valid_range(self) -> NativeTableProjection:
        first_row, first_col = cell_position(self.start_cell)
        last_row, last_col = cell_position(self.end_cell)
        if first_row > last_row or first_col > last_col:
            raise ValueError(
                "Native table range must run from top-left to bottom-right"
            )
        if (last_row - first_row + 1) * (last_col - first_col + 1) > MAX_NATIVE_CELLS:
            raise ValueError("Native table projection exceeds the cell budget")
        return self


class NativeTableBinding(NativeModel):
    schema_version: Literal["native-a2t-binding-v1"] = "native-a2t-binding-v1"
    source: NativeFileReference
    projection: NativeTableProjection
    row_ids: list[str] = Field(min_length=1, max_length=MAX_NATIVE_CELLS)
    columns: list[str] = Field(min_length=1, max_length=16_384)

    @model_validator(mode="after")
    def valid_mapping(self) -> NativeTableBinding:
        first_row, first_col = cell_position(self.projection.start_cell)
        last_row, last_col = cell_position(self.projection.end_cell)
        if len(self.row_ids) != last_row - first_row + 1 or len(
            set(self.row_ids)
        ) != len(self.row_ids):
            raise ValueError("Native table row mapping does not match the source range")
        if self.columns != [
            column_letters(col) for col in range(first_col, last_col + 1)
        ]:
            raise ValueError(
                "Native table column mapping does not match the source range"
            )
        return self


class NativeTableWorkbookCreate(NativeModel):
    name: str = Field(default="table.xlsx", min_length=6, max_length=200)
    sheet: str = Field(default="Data", min_length=1, max_length=31)
    include_headers: bool = False

    @field_validator("sheet")
    @classmethod
    def valid_sheet(cls, value: str) -> str:
        return validate_sheet_name(value)

    @field_validator("name")
    @classmethod
    def valid_filename(cls, value: str) -> str:
        if (
            "/" in value
            or "\\" in value
            or "\x00" in value
            or not value.lower().endswith(".xlsx")
        ):
            raise ValueError("Table workbook name must be an XLSX filename")
        return value


class NativeTableRangeReader(Protocol):
    def read_range(
        self, data: bytes, projection: NativeTableProjection
    ) -> list[list[dict[str, Any]]]: ...


class NativeTableSnapshotReader(Protocol):
    def read_workspace(self, table_id: str) -> TableContext: ...


class NativeTableWorkspaces(NativeTableSnapshotReader, Protocol):
    def create_workspace(self, context: TableContext) -> None: ...
