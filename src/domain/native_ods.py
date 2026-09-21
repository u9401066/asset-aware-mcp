"""ODS coordinates and authored values; no OOXML identity or inferred cell types."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import Field, field_validator, model_validator

from src.domain.native_asset_models import NativeModel

# Operational bounds, not limits imposed by the OpenDocument specification.
MAX_ODS_ROWS = 1_048_576
MAX_ODS_COLUMNS = 16_384
MAX_ODS_RECORDS = 20_000
MAX_ODS_TEXT = 32_767


def ods_text(value: str) -> str:
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value):
        raise ValueError("ODS text contains characters unavailable in XML 1.0")
    return value


class NativeODSCellLocator(NativeModel):
    part: Literal["content.xml"] = "content.xml"
    table_index: int = Field(ge=0, le=255)
    table_name: str = Field(min_length=1, max_length=1024)
    row: int = Field(ge=0, lt=MAX_ODS_ROWS)
    column: int = Field(ge=0, lt=MAX_ODS_COLUMNS)

    _name = field_validator("table_name")(ods_text)


class NativeODSValue(NativeModel):
    kind: Literal[
        "string",
        "float",
        "percentage",
        "currency",
        "boolean",
        "date",
        "time",
        "formula",
        "blank",
    ] = "string"
    # Numbers retain their decimal lexical representation, without float coercion.
    value: str | bool | None = Field(default=None)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def validate_value(self) -> NativeODSValue:
        if (self.kind == "currency") != (self.currency is not None):
            raise ValueError("Only currency values require an explicit currency code")
        if self.kind == "blank":
            if self.value is not None:
                raise ValueError("Blank ODS values require null")
            return self
        if self.kind == "boolean":
            if type(self.value) is not bool:
                raise ValueError("ODS boolean values require a JSON boolean")
            return self
        if not isinstance(self.value, str) or len(self.value) > MAX_ODS_TEXT:
            raise ValueError("ODS values require a bounded lexical string")
        ods_text(self.value)
        if self.kind in {"float", "percentage", "currency"}:
            if not re.fullmatch(
                r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", self.value
            ):
                raise ValueError("ODS numbers require a finite decimal lexical value")
            try:
                finite = Decimal(self.value).is_finite()
            except InvalidOperation:
                finite = False
            if not finite:
                raise ValueError("ODS numbers require a finite decimal lexical value")
        elif self.kind == "date":
            if not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})?)?",
                self.value,
            ):
                raise ValueError("Author an ISO calendar date or date-time")
            if "T" in self.value:
                datetime.fromisoformat(self.value.replace("Z", "+00:00"))
            else:
                date.fromisoformat(self.value)
        elif self.kind == "time":
            if not re.fullmatch(
                r"-?P(?=[0-9]|T[0-9])(?:[0-9]+D)?(?:T(?=[0-9])(?:[0-9]+H)?(?:[0-9]+M)?(?:[0-9]+(?:\.[0-9]+)?S)?)?",
                self.value,
            ):
                raise ValueError("Author an ISO day/time duration")
        elif self.kind == "formula":
            if not self.value.startswith("=") or not 2 <= len(self.value) <= 8192:
                raise ValueError(
                    "OpenFormula expressions require '=' and 2-8192 characters"
                )
        return self


class NativeODSCellEdit(NativeModel):
    locator: NativeODSCellLocator
    value: NativeODSValue
    # Explicit acknowledgement that authored display paragraphs replace rich runs.
    display_policy: Literal["replace_paragraphs_preserve_cell_style"]


class NativeODSCreate(NativeModel):
    name: str = Field(default="workbook.ods", min_length=5, max_length=200)
    tables: list[str] = Field(
        default_factory=lambda: ["Sheet1"], min_length=1, max_length=256
    )

    @model_validator(mode="after")
    def validate_names(self) -> NativeODSCreate:
        ods_text(self.name)
        if (
            "/" in self.name
            or "\\" in self.name
            or not self.name.lower().endswith(".ods")
        ):
            raise ValueError("ODS name must be a filename without directories")
        if len(set(self.tables)) != len(self.tables):
            raise ValueError("ODS table names must be distinct")
        for name in self.tables:
            ods_text(name)
            if not name or len(name) > 1024:
                raise ValueError("ODS table name must contain 1-1024 characters")
        return self
