"""Exact string-table CRUD, explicit dialects and revision-bound field identity."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Any, Literal, Protocol

from pydantic import Field, field_validator, model_validator

from src.domain.native_asset_models import (
    ASSET_ID_PATTERN,
    SHA256_PATTERN,
    NativeEditResult,
    NativeModel,
)

MAX_DELIMITED_BYTES = 16 * 1024 * 1024
MAX_DELIMITED_FIELDS = 20_000
Encoding = Literal["utf-8", "utf-16-le", "utf-16-be", "cp950", "cp1252", "latin-1"]
Separator = Literal["\n", "\r", "\r\n"]
DELIMITED_REVIEW = [
    "semantic_accuracy",
    "header_and_type_interpretation",
    "downstream_rendering_and_formula_interpretation",
]
FieldValue = Annotated[str, Field(max_length=MAX_DELIMITED_BYTES)]


def row_budget(value: Any) -> Any:
    if (
        isinstance(value, list)
        and sum(len(r) for r in value if isinstance(r, list)) > MAX_DELIMITED_FIELDS
    ):
        raise ValueError("Delimited rows exceed the total field budget")
    if (
        isinstance(value, list)
        and sum(
            len(cell)
            for row in value
            if isinstance(row, list)
            for cell in row
            if isinstance(cell, str)
        )
        > MAX_DELIMITED_BYTES
    ):
        raise ValueError("Delimited string values exceed the input budget")
    return value


class NativeDelimitedDialect(NativeModel):
    delimiter: str = Field(default=",", min_length=1, max_length=1)
    quotechar: str | None = Field(default='"', min_length=1, max_length=1)
    escapechar: str | None = Field(default=None, min_length=1, max_length=1)
    doublequote: bool = True
    encoding: Encoding | None = None

    @model_validator(mode="after")
    def valid_characters(self) -> NativeDelimitedDialect:
        chars = [
            c
            for c in (self.delimiter, self.quotechar, self.escapechar)
            if c is not None
        ]
        if len(set(chars)) != len(chars) or any(
            c in "\r\n\x00" or 0xD800 <= ord(c) <= 0xDFFF for c in chars
        ):
            raise ValueError(
                "Delimiter, quote and escape must be distinct non-newline scalar characters"
            )
        return self


class NativeDelimitedLocator(NativeModel):
    row: int = Field(ge=0, lt=MAX_DELIMITED_FIELDS)
    column: int = Field(ge=0, lt=MAX_DELIMITED_FIELDS)
    byte_start: int = Field(ge=0, le=MAX_DELIMITED_BYTES)
    byte_end: int = Field(ge=0, le=MAX_DELIMITED_BYTES)
    char_start: int = Field(ge=0, le=MAX_DELIMITED_BYTES)
    char_end: int = Field(ge=0, le=MAX_DELIMITED_BYTES)

    @model_validator(mode="after")
    def ordered(self) -> NativeDelimitedLocator:
        if self.byte_start > self.byte_end or self.char_start > self.char_end:
            raise ValueError("Delimited field spans must be ordered")
        return self


class NativeDelimitedReference(NativeModel):
    schema_version: Literal["native-delimited-cell-ref-v1"] = (
        "native-delimited-cell-ref-v1"
    )
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    dialect: NativeDelimitedDialect
    locator: NativeDelimitedLocator
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_delimited_field"] = (
        "immutable_delimited_field"
    )


def attach_delimited_evidence(
    record: dict[str, Any], asset_id: str, revision: str
) -> None:
    raw = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    record["evidence"] = NativeDelimitedReference(
        asset_id=asset_id,
        revision=revision,
        dialect=record["dialect"],
        locator=record["locator"],
        value_sha256=hashlib.sha256(raw).hexdigest(),
    ).model_dump(mode="json")


class NativeDelimitedCreate(NativeModel):
    name: str = Field(default="table.csv", min_length=5, max_length=200)
    rows: list[list[FieldValue]] = Field(
        default_factory=list, max_length=MAX_DELIMITED_FIELDS
    )
    dialect: NativeDelimitedDialect | None = None
    record_separator: Separator = "\r\n"
    bom: bool = False
    final_separator: bool = True

    _budget = field_validator("rows", mode="before")(row_budget)

    @field_validator("name")
    @classmethod
    def basename(cls, value: str) -> str:
        if not value.lower().endswith((".csv", ".tsv")) or any(
            c in value for c in "/\\:\x00"
        ):
            raise ValueError("Delimited name must be a CSV/TSV basename")
        return value


class NativeDelimitedCellEdit(NativeModel):
    reference: NativeDelimitedReference
    value: FieldValue


class NativeDelimitedSetCells(NativeModel):
    operation: Literal["set_cells"]
    cells: list[NativeDelimitedCellEdit] = Field(min_length=1, max_length=1000)

    @field_validator("cells", mode="before")
    @classmethod
    def input_budget(cls, value: Any) -> Any:
        if isinstance(value, list):
            row_budget(
                [
                    [v.get("value")]
                    if isinstance(v, dict)
                    else [v.value]
                    if isinstance(v, NativeDelimitedCellEdit)
                    else []
                    for v in value
                ]
            )
        return value


class NativeDelimitedInsertRows(NativeModel):
    operation: Literal["insert_rows"]
    index: int = Field(ge=0, le=MAX_DELIMITED_FIELDS)
    rows: list[list[FieldValue]] = Field(min_length=1, max_length=1024)
    record_separator: Separator

    _budget = field_validator("rows", mode="before")(row_budget)


class NativeDelimitedDeleteRows(NativeModel):
    operation: Literal["delete_rows"]
    index: int = Field(ge=0, lt=MAX_DELIMITED_FIELDS)
    count: int = Field(ge=1, le=1024)


class NativeDelimitedInsertColumn(NativeModel):
    operation: Literal["insert_column"]
    index: int = Field(ge=0, le=MAX_DELIMITED_FIELDS)
    values: list[FieldValue] = Field(min_length=1, max_length=MAX_DELIMITED_FIELDS)

    @field_validator("values", mode="before")
    @classmethod
    def input_budget(cls, value: Any) -> Any:
        if isinstance(value, list):
            row_budget([value])
        return value


class NativeDelimitedDeleteColumns(NativeModel):
    operation: Literal["delete_columns"]
    index: int = Field(ge=0, lt=MAX_DELIMITED_FIELDS)
    count: int = Field(ge=1, le=1024)
    record_separator: Separator = "\r\n"


NativeDelimitedUpdate = Annotated[
    NativeDelimitedSetCells
    | NativeDelimitedInsertRows
    | NativeDelimitedDeleteRows
    | NativeDelimitedInsertColumn
    | NativeDelimitedDeleteColumns,
    Field(discriminator="operation"),
]


class NativeDelimitedAdapter(Protocol):
    def inspect(
        self, data: bytes, dialect: NativeDelimitedDialect
    ) -> dict[str, Any]: ...
    def read_cell(
        self, data: bytes, dialect: NativeDelimitedDialect, row: int, column: int
    ) -> dict[str, Any]: ...
    def decompose(
        self, data: bytes, dialect: NativeDelimitedDialect
    ) -> list[dict[str, Any]]: ...
    def create(
        self, request: NativeDelimitedCreate
    ) -> tuple[bytes, NativeEditResult]: ...
    def update(
        self,
        data: bytes,
        dialect: NativeDelimitedDialect,
        request: NativeDelimitedUpdate,
    ) -> tuple[bytes, NativeEditResult]: ...
