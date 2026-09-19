"""Explicit native Table creation over an exact existing worksheet range."""

from __future__ import annotations

import re
from typing import Literal, Protocol

from pydantic import Field, model_validator

from src.domain.native_asset_models import NativeEditResult, NativeModel
from src.domain.native_grid_address import parse_address
from src.domain.native_table_edit import (  # noqa: TC001 -- schema
    NativeCalculatedEdit,
    NativeTotalsEdit,
)
from src.domain.native_workbook import NativeWorksheetKey  # noqa: TC001 -- schema


class NativeTableColumnCreate(NativeModel):
    name: str = Field(min_length=1, max_length=255)
    calculated: NativeCalculatedEdit | None = None
    totals: NativeTotalsEdit | None = None


class NativeTableStyle(NativeModel):
    name: str | None = Field(default="TableStyleMedium2", min_length=1, max_length=255)
    show_first_column: bool = False
    show_last_column: bool = False
    show_row_stripes: bool = True
    show_column_stripes: bool = False


class NativeTableCreate(NativeModel):
    worksheet: NativeWorksheetKey
    ref: str = Field(min_length=2, max_length=21)
    name: str = Field(min_length=1, max_length=255)
    columns: list[NativeTableColumnCreate] = Field(min_length=1, max_length=256)
    header_row: bool = True
    totals_row: bool = False
    autofilter: bool = True
    header_policy: Literal["require_matching", "fill_blank"] = "require_matching"
    style: NativeTableStyle = Field(default_factory=NativeTableStyle)

    @model_validator(mode="after")
    def valid_table(self) -> NativeTableCreate:
        if (
            not (self.name[0].isalpha() or self.name[0] in "_\\")
            or any(not (c.isalnum() or c in "_.") for c in self.name[1:])
            or self.name.casefold() in {"r", "c"}
            or parse_address(self.name) is not None
            or re.fullmatch(r"R[0-9]+C[0-9]+", self.name, re.IGNORECASE)
        ):
            raise ValueError("Invalid Excel Table name or cell-reference ambiguity")
        if len({c.name.casefold() for c in self.columns}) != len(self.columns):
            raise ValueError("Duplicate Table column names ignoring case")
        if self.autofilter and not self.header_row:
            raise ValueError("A Table AutoFilter requires a header row")
        if any(c.totals is not None for c in self.columns) and not self.totals_row:
            raise ValueError("Column totals require an explicit totals row")
        if any(c.calculated and c.calculated.formula is None for c in self.columns):
            raise ValueError("New calculated columns require a formula")
        return self


class NativeTableCreateAdapter(Protocol):
    def create(
        self, data: bytes, request: NativeTableCreate
    ) -> tuple[bytes, NativeEditResult]: ...
