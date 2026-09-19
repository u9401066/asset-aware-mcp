"""Explicit native Table metadata/cell edits, independent of package IO."""

from __future__ import annotations

from typing import Literal, Protocol

from pydantic import Field, model_validator

from src.domain.native_asset_models import NativeEditResult, NativeModel
from src.domain.native_workbook import NativeWorksheetKey  # noqa: TC001 -- schema

TOTAL_FUNCTIONS = {
    "average": 101,
    "countNums": 102,
    "count": 103,
    "max": 104,
    "min": 105,
    "stdDev": 107,
    "sum": 109,
    "var": 110,
}


class NativeCalculatedEdit(NativeModel):
    formula: str | None = Field(min_length=2, max_length=8192)
    policy: Literal["require_matching", "replace_all", "keep_cells"]

    @model_validator(mode="after")
    def valid_formula(self) -> NativeCalculatedEdit:
        if (self.formula is None) != (self.policy == "keep_cells"):
            raise ValueError(
                "Null formula requires keep_cells; setting a formula does not"
            )
        if self.formula is not None and not self.formula.startswith("="):
            raise ValueError("Calculated formula must start with =")
        return self


class NativeTotalsEdit(NativeModel):
    kind: Literal["blank", "label", "formula", "function"]
    value: str | None = Field(default=None, max_length=8192)

    @model_validator(mode="after")
    def valid_value(self) -> NativeTotalsEdit:
        if (self.kind == "blank") != (self.value is None):
            raise ValueError("Only blank totals use null value")
        if self.kind == "formula" and (
            not self.value or not self.value.startswith("=") or len(self.value) < 2
        ):
            raise ValueError("Totals formula must start with = and contain a formula")
        if self.kind == "function" and self.value not in TOTAL_FUNCTIONS:
            raise ValueError("Unknown native Table totals function")
        return self


class NativeTableColumnEdit(NativeModel):
    column_id: int = Field(ge=1, le=4_294_967_295, strict=True)
    expected_name: str = Field(min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    header_runs: list[str] | None = Field(default=None, min_length=1, max_length=128)
    calculated: NativeCalculatedEdit | None = None
    totals: NativeTotalsEdit | None = None

    @model_validator(mode="after")
    def meaningful_edit(self) -> NativeTableColumnEdit:
        if self.name is None and self.calculated is None and self.totals is None:
            raise ValueError("A Table column edit must supply a change")
        if self.header_runs is not None and (
            self.name is None or "".join(self.header_runs) != self.name
        ):
            raise ValueError("Header runs must concatenate exactly to the new name")
        return self


class NativeTableUpdate(NativeModel):
    worksheet: NativeWorksheetKey
    part: str = Field(min_length=1, max_length=1024)
    expected_ref: str = Field(min_length=2, max_length=21)
    columns: list[NativeTableColumnEdit] = Field(min_length=1, max_length=256)

    @model_validator(mode="after")
    def unique_columns(self) -> NativeTableUpdate:
        if len({column.column_id for column in self.columns}) != len(self.columns):
            raise ValueError("Duplicate Table column edit identity")
        return self


class NativeTableEditAdapter(Protocol):
    def update(
        self, data: bytes, request: NativeTableUpdate
    ) -> tuple[bytes, NativeEditResult]: ...
