"""Native workbook structure requests; source revision preconditions live above IO."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from pydantic import Field, field_validator, model_validator

from src.domain.native_asset_models import NativeModel, validate_sheet_name

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult


class NativeWorksheetKey(NativeModel):
    sheet_id: str = Field(pattern=r"^[1-9][0-9]{0,9}$")
    part: str = Field(min_length=1, max_length=1024)

    @field_validator("sheet_id")
    @classmethod
    def sheet_id_range(cls, value: str) -> str:
        if int(value) > 4_294_967_295:
            raise ValueError("Worksheet sheetId exceeds unsigned 32-bit range")
        return value


class NativeWorksheetInsert(NativeModel):
    index: int = Field(ge=0, le=256)
    names: list[str] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def valid_names(self) -> NativeWorksheetInsert:
        for name in self.names:
            validate_sheet_name(name)
        if len({name.casefold() for name in self.names}) != len(self.names):
            raise ValueError("Inserted worksheet names must be unique ignoring case")
        return self


class NativeWorksheetRename(NativeModel):
    key: NativeWorksheetKey
    name: str = Field(min_length=1, max_length=31)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return validate_sheet_name(value)


class NativeWorkbookStructureAdapter(Protocol):
    def read(self, data: bytes, *, references: bool = False) -> dict[str, Any]: ...

    def add(
        self, data: bytes, request: NativeWorksheetInsert, allow_3d: bool
    ) -> tuple[bytes, NativeEditResult]: ...

    def rename(
        self, data: bytes, request: NativeWorksheetRename
    ) -> tuple[bytes, NativeEditResult]: ...

    def reorder(
        self, data: bytes, keys: list[NativeWorksheetKey], allow_3d: bool
    ) -> tuple[bytes, NativeEditResult]: ...

    def delete(
        self, data: bytes, keys: list[NativeWorksheetKey]
    ) -> tuple[bytes, NativeEditResult]: ...
