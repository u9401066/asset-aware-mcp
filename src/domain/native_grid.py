"""Explicit native grid edits and coordinate transforms, independent of file IO."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import Field, model_validator

from src.domain.native_asset_models import NativeEditResult, NativeModel
from src.domain.native_workbook import NativeWorksheetKey  # noqa: TC001 -- schema

if TYPE_CHECKING:
    from src.domain.native_layout import NativeLayoutUpdate


class NativeTableExpansion(NativeModel):
    part: str = Field(min_length=1, max_length=1024)
    expected_ref: str = Field(min_length=2, max_length=21)


class NativeGridEdit(NativeModel):
    axis: Literal["row", "column"]
    operation: Literal["insert", "delete"]
    at: int = Field(ge=1, le=1_048_576)
    count: int = Field(default=1, ge=1, le=1024)
    inherit_format: Literal["before", "after", "none"] | None = None
    merged_anchor: Literal["preserve", "delete"] | None = None
    collapsed_objects: Literal["preserve_size", "reject"] | None = None
    expand_tables: list[NativeTableExpansion] | None = Field(
        default=None, min_length=1, max_length=32
    )

    @property
    def limit(self) -> int:
        return 1_048_576 if self.axis == "row" else 16_384

    @model_validator(mode="after")
    def valid_bounds(self) -> NativeGridEdit:
        if self.expand_tables is not None:
            if self.operation != "insert":
                raise ValueError("Table expansion is only used for insertion")
            if len({item.part for item in self.expand_tables}) != len(
                self.expand_tables
            ):
                raise ValueError("Duplicate table expansion identities")
        if self.at + self.count - 1 > self.limit:
            raise ValueError("Native grid operation exceeds worksheet bounds")
        if self.operation == "delete" and self.inherit_format is not None:
            raise ValueError("Format inheritance is only used for insertion")
        if self.operation == "insert" and self.merged_anchor is not None:
            raise ValueError("Merged anchor policy is only used for deletion")
        if self.operation == "insert" and self.collapsed_objects is not None:
            raise ValueError("Collapsed object policy is only used for deletion")
        return self


class NativeGridUpdate(NativeModel):
    worksheet: NativeWorksheetKey
    edits: list[NativeGridEdit] = Field(min_length=1, max_length=32)
    column_digit_width: int | None = Field(default=None, ge=1, le=100)
    default_column_pixels: int | None = Field(default=None, ge=1, le=10_000)
    default_row_height_points: float | None = Field(
        default=None, gt=0, le=409.5, allow_inf_nan=False
    )


@dataclass(frozen=True)
class GridTransform:
    edit: NativeGridEdit

    def point(self, value: int, *, clamp: bool = False) -> int | None:
        if not 1 <= value <= self.edit.limit:
            raise ValueError("Grid coordinate exceeds worksheet bounds")
        start, size = self.edit.at, self.edit.count
        if value < start:
            return value
        if self.edit.operation == "insert":
            if value + size > self.edit.limit:
                if clamp:
                    return self.edit.limit
                raise ValueError("Insertion would move content outside the worksheet")
            return value + size
        if value < start + size:
            return start if clamp else None
        return value - size

    def span(
        self, first: int, last: int, *, clip: bool = False
    ) -> tuple[int, int] | None:
        if not 1 <= first <= last <= self.edit.limit:
            raise ValueError("Invalid native grid interval")
        at, count = self.edit.at, self.edit.count
        if self.edit.operation == "insert":
            left = first + count if first >= at else first
            right = last + count if last >= at else last
            if right > self.edit.limit:
                if not clip:
                    raise ValueError(
                        "Insertion would move a range outside the worksheet"
                    )
                right = self.edit.limit
            return (left, right) if left <= right else None
        end = at + count - 1
        if first >= at and last <= end:
            return None
        left = first if first < at else max(first - count, at)
        right = last if last < at else max(last - count, at - 1)
        return (left, right) if left <= right else None


class NativeGridAdapter(Protocol):
    def update(
        self, data: bytes, request: NativeGridUpdate
    ) -> tuple[bytes, NativeEditResult]: ...

    def read_layout(self, data: bytes, key: NativeWorksheetKey) -> dict[str, Any]: ...

    def update_layout(
        self, data: bytes, request: NativeLayoutUpdate
    ) -> tuple[bytes, NativeEditResult]: ...
