"""Native file identity, typed edits and preservation results, without file IO."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.domain.citation_format import (
    CitationMetadata,  # noqa: TC001 -- Pydantic runtime schema
)

if TYPE_CHECKING:
    from collections.abc import Iterator

SHA256_PATTERN = r"^[a-f0-9]{64}$"
ASSET_ID_PATTERN = r"^file_[a-f0-9]{32}$"
MAX_NATIVE_BYTES = 64 * 1024 * 1024
MAX_NATIVE_CELLS = 20_000


def cell_position(address: str) -> tuple[int, int]:
    """Return one-based row/column, rejecting addresses outside Excel's grid."""
    match = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]{0,6})", address)
    if not match:
        raise ValueError("Cell address must be an uppercase A1 coordinate")
    column = 0
    for char in match[1]:
        column = column * 26 + ord(char) - ord("A") + 1
    row = int(match[2])
    if row > 1_048_576 or column > 16_384:
        raise ValueError("Cell address exceeds the worksheet grid")
    return row, column


def validate_sheet_name(name: str) -> str:
    if (
        not name.strip()
        or len(name) > 31
        or re.search(r"[\[\]:*?/\\\x00-\x1f]", name)
        or name.startswith("'")
        or name.endswith("'")
    ):
        raise ValueError("Invalid worksheet name")
    return name


class NativeModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class NativeCellEdit(NativeModel):
    sheet: str = Field(min_length=1, max_length=31)
    cell: str = Field(min_length=2, max_length=10)
    kind: Literal["string", "number", "boolean", "formula", "blank"] = "string"
    value: str | int | float | bool | None = None

    @field_validator("cell")
    @classmethod
    def validate_cell(cls, value: str) -> str:
        cell_position(value)
        return value

    @model_validator(mode="after")
    def validate_value(self) -> NativeCellEdit:
        value = self.value
        if self.kind == "blank":
            if value is not None:
                raise ValueError("blank edits require value=null")
        elif self.kind == "boolean":
            if type(value) is not bool:
                raise ValueError("boolean edits require a JSON boolean")
        elif self.kind == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError("number edits require a finite JSON number")
            try:
                finite = math.isfinite(value)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("number edits require a finite JSON number")
        elif not isinstance(value, str) or len(value) > 32_767:
            raise ValueError("string/formula edits require at most 32767 characters")
        elif re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value):
            raise ValueError("Cell text contains characters unavailable in XML 1.0")
        elif self.kind == "formula" and (
            not value.startswith("=") or len(value) < 2 or len(value) > 8192
        ):
            raise ValueError(
                "Formulas must start with '=' and contain 2-8192 characters"
            )
        return self


class NativeWorkbookCreate(NativeModel):
    name: str = Field(default="workbook.xlsx", min_length=6, max_length=200)
    sheets: list[str] = Field(
        default_factory=lambda: ["Sheet1"], min_length=1, max_length=256
    )
    edits: list[NativeCellEdit] = Field(
        default_factory=list, max_length=MAX_NATIVE_CELLS
    )

    @model_validator(mode="after")
    def validate_workbook(self) -> NativeWorkbookCreate:
        if (
            "/" in self.name
            or "\\" in self.name
            or not self.name.lower().endswith(".xlsx")
        ):
            raise ValueError(
                "Workbook name must be an XLSX filename without directories"
            )
        for name in self.sheets:
            validate_sheet_name(name)
        if len({name.casefold() for name in self.sheets}) != len(self.sheets):
            raise ValueError("Worksheet names must be unique ignoring case")
        if any(edit.sheet not in self.sheets for edit in self.edits):
            raise ValueError("An edit names an unknown worksheet")
        if len({(edit.sheet, edit.cell) for edit in self.edits}) != len(self.edits):
            raise ValueError("A transaction cannot edit the same cell twice")
        return self


class NativeEditResult(NativeModel):
    changed_parts: list[str]
    preserved_parts: int
    changes: list[dict[str, Any]]
    checks: list[str]
    repairs: list[str] = Field(default_factory=list)
    review_required: list[str] = Field(
        default_factory=lambda: [
            "semantic_accuracy",
            "rendered_layout",
            "formula_results",
        ]
    )


class NativeAssetRevision(NativeModel):
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=0, le=MAX_NATIVE_BYTES)
    operation: str
    parent_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    result: NativeEditResult | None = None


class NativeSource(NativeModel):
    path: str
    sha256: str = Field(pattern=SHA256_PATTERN)
    size_bytes: int = Field(ge=0)
    mtime_ns: int = Field(ge=0)
    device: int
    inode: int


class NativeFileAsset(NativeModel):
    schema_version: Literal["native-file-asset-v1"] = "native-file-asset-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    name: str
    format: str
    media_type: str
    revision: str = Field(pattern=SHA256_PATTERN)
    source: NativeSource | None = None
    archived: bool = False
    history: list[NativeAssetRevision] = Field(min_length=1, max_length=10000)


class NativeAssetRepository(Protocol):
    """Storage port. Immutable blobs and compare-and-swap metadata are atomic."""

    def register(self, source_path: str) -> NativeFileAsset: ...
    def create(
        self, name: str, data: bytes, format_name: str, media_type: str
    ) -> NativeFileAsset: ...
    def load(self, asset_id: str) -> NativeFileAsset: ...
    def read(self, asset_id: str, revision: str | None = None) -> bytes: ...
    def commit(
        self,
        asset_id: str,
        expected_revision: str,
        data: bytes,
        result: NativeEditResult,
    ) -> NativeFileAsset: ...
    def archive(self, asset_id: str, expected_revision: str) -> NativeFileAsset: ...
    def refresh(
        self, asset_id: str, expected_revision: str, expected_source_sha256: str
    ) -> NativeFileAsset: ...
    def writeback(
        self, asset_id: str, expected_revision: str, expected_source_sha256: str
    ) -> dict[str, Any]: ...
    def publish(
        self, asset_id: str, expected_revision: str, output_path: str
    ) -> dict[str, Any]: ...
    def list_assets(self, offset: int, limit: int) -> list[NativeFileAsset]: ...


class NativeCellLocator(NativeModel):
    sheet_id: str = Field(min_length=1, max_length=128)
    part: str = Field(min_length=1, max_length=1024)
    kind: str = Field(min_length=1, max_length=1024)
    cell: str = Field(min_length=2, max_length=10)

    @field_validator("cell")
    @classmethod
    def validate_cell(cls, value: str) -> str:
        cell_position(value)
        return value


class NativeCellReference(NativeModel):
    schema_version: Literal["native-cell-ref-v1"] = "native-cell-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    locator: NativeCellLocator
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


class NativeSpreadsheetAdapter(Protocol):
    def iter_cells(self, data: bytes) -> Iterator[dict[str, Any]]: ...

    def read_cell_by_locator(
        self, data: bytes, locator: NativeCellLocator
    ) -> dict[str, Any]: ...
    def read_cell(self, data: bytes, sheet: str, cell: str) -> dict[str, Any]: ...

    def inspect(
        self, data: bytes, *, sheet: str | None, offset: int, limit: int
    ) -> dict[str, Any]: ...
    def create(self, request: NativeWorkbookCreate) -> bytes: ...
    def edit(
        self, data: bytes, edits: list[NativeCellEdit]
    ) -> tuple[bytes, NativeEditResult]: ...


class NativeDocumentRequest(NativeModel):
    op: Literal[
        "contract",
        "register",
        "create",
        "list",
        "inspect",
        "read_cell",
        "verify",
        "export_wiki",
        "update",
        "history",
        "publish",
        "writeback",
        "refresh",
        "archive",
    ] = "contract"
    source_path: str | None = Field(default=None, min_length=1, max_length=4096)
    asset_id: str | None = Field(default=None, pattern=ASSET_ID_PATTERN)
    revision: str | None = Field(default=None, pattern=SHA256_PATTERN)
    expected_revision: str | None = Field(default=None, pattern=SHA256_PATTERN)
    expected_source_sha256: str | None = Field(default=None, pattern=SHA256_PATTERN)
    output_path: str | None = Field(default=None, min_length=1, max_length=4096)
    output_dir: str | None = Field(default=None, min_length=1, max_length=4096)
    citation_contract: dict[str, Any] | None = None
    citation_metadata: CitationMetadata | None = None
    workbook: NativeWorkbookCreate | None = None
    reference: NativeCellReference | None = None
    edits: list[NativeCellEdit] = Field(
        default_factory=list, max_length=MAX_NATIVE_CELLS
    )
    sheet: str | None = Field(default=None, min_length=1, max_length=31)
    cell: str | None = Field(default=None, min_length=2, max_length=10)
    text_offset: int = Field(default=0, ge=0)
    text_limit: int = Field(default=2000, ge=1, le=4000)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=1000)

    @field_validator("cell")
    @classmethod
    def validate_optional_cell(cls, value: str | None) -> str | None:
        if value is not None:
            cell_position(value)
        return value

    @model_validator(mode="after")
    def validate_operation(self) -> NativeDocumentRequest:
        required = {
            "register": {"source_path"},
            "create": {"workbook"},
            "inspect": {"asset_id"},
            "read_cell": {"asset_id", "sheet", "cell"},
            "verify": {"reference"},
            "export_wiki": {"asset_id", "output_dir"},
            "history": {"asset_id"},
            "update": {"asset_id", "expected_revision", "edits"},
            "publish": {"asset_id", "expected_revision", "output_path"},
            "writeback": {"asset_id", "expected_revision", "expected_source_sha256"},
            "refresh": {"asset_id", "expected_revision", "expected_source_sha256"},
            "archive": {"asset_id", "expected_revision"},
        }.get(self.op, set())
        missing = [name for name in required if not getattr(self, name)]
        if missing:
            raise ValueError(
                "Missing native operation fields: " + ", ".join(sorted(missing))
            )
        optional = {
            "list": {"offset", "limit"},
            "history": {"offset", "limit"},
            "inspect": {"sheet", "offset", "limit", "revision"},
            "read_cell": {"revision", "text_offset", "text_limit"},
            "export_wiki": {"revision", "citation_contract", "citation_metadata"},
        }.get(self.op, set())
        unused = self.model_fields_set - required - optional - {"op"}
        if unused:
            raise ValueError(
                "Fields not used by this native operation: " + ", ".join(sorted(unused))
            )
        return self
