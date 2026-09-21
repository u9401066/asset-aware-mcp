"""ODS coordinates and authored values; no OOXML identity or inferred cell types."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import Field, field_validator, model_validator

from src.domain.native_asset_models import (
    ASSET_ID_PATTERN,
    SHA256_PATTERN,
    NativeEditResult,
    NativeModel,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

# Operational bounds, not limits imposed by the OpenDocument specification.
MAX_ODS_ROWS = 1_048_576
MAX_ODS_COLUMNS = 16_384
MAX_ODS_RECORDS = 20_000
MAX_ODS_TEXT = 32_767
ODS_REVIEW = [
    "semantic_accuracy",
    "rendered_layout",
    "formula_results",
    "rich_text_replacement",
]


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


class NativeODSCellReference(NativeModel):
    schema_version: Literal["native-ods-cell-ref-v1"] = "native-ods-cell-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    locator: NativeODSCellLocator
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


def attach_ods_evidence(record: dict[str, Any], asset_id: str, revision: str) -> None:
    data = json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    record["evidence"] = NativeODSCellReference(
        asset_id=asset_id,
        revision=revision,
        locator=NativeODSCellLocator.model_validate(record["locator"]),
        value_sha256=hashlib.sha256(data).hexdigest(),
    ).model_dump(mode="json")


class NativeODSCellUpdate(NativeModel):
    reference: NativeODSCellReference
    value: NativeODSValue
    display_policy: Literal["replace_paragraphs_preserve_cell_style"]


class NativeODSUpdate(NativeModel):
    cells: list[NativeODSCellUpdate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def distinct_targets(self) -> NativeODSUpdate:
        keys = [
            tuple(item.reference.locator.model_dump().values()) for item in self.cells
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("Each ODS logical cell must be targeted once")
        return self


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


class NativeODSAdapter(Protocol):
    def create(self, request: NativeODSCreate) -> bytes: ...
    def inspect(self, data: bytes, *, offset: int, limit: int) -> dict[str, Any]: ...
    def read_cell(
        self, data: bytes, locator: NativeODSCellLocator
    ) -> dict[str, Any]: ...
    def edit(
        self, data: bytes, edits: list[NativeODSCellEdit]
    ) -> tuple[bytes, NativeEditResult]: ...
    def decompose(self, data: bytes) -> Iterator[dict[str, Any]]: ...
