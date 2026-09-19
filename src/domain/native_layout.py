"""Explicit worksheet dimensions; size selection belongs to the reviewing Agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import Field, model_validator

from src.domain.native_asset_models import NativeModel
from src.domain.native_workbook import NativeWorksheetKey  # noqa: TC001 -- schema


class NativeLayoutEdit(NativeModel):
    axis: Literal["row", "column"]
    at: int = Field(ge=1, le=1_048_576)
    count: int = Field(default=1, ge=1, le=1024)
    height_points: float | None = Field(
        default=None, gt=0, le=409.5, allow_inf_nan=False
    )
    width_ooxml: float | None = Field(
        default=None,
        gt=0,
        le=255,
        allow_inf_nan=False,
        description="Raw OOXML column width, including padding; not Excel UI characters.",
    )
    reset_size: bool = False
    hidden: bool | None = None
    collapsed_objects: Literal["reject", "preserve_size"] = "reject"

    @property
    def limit(self) -> int:
        return 1_048_576 if self.axis == "row" else 16_384

    @model_validator(mode="after")
    def valid_intent(self) -> NativeLayoutEdit:
        if self.at + self.count - 1 > self.limit:
            raise ValueError("Layout interval exceeds worksheet bounds")
        size = self.height_points if self.axis == "row" else self.width_ooxml
        other = self.width_ooxml if self.axis == "row" else self.height_points
        if other is not None:
            raise ValueError("Row height and column width use different units")
        if self.reset_size and size is not None:
            raise ValueError("Choose an explicit size or reset_size, not both")
        if size is None and not self.reset_size and self.hidden is None:
            raise ValueError("Layout edit needs an explicit size, reset or visibility")
        return self


class NativeLayoutUpdate(NativeModel):
    worksheet: NativeWorksheetKey
    edits: list[NativeLayoutEdit] = Field(min_length=1, max_length=32)
    column_digit_width: int | None = Field(default=None, ge=1, le=100)
    default_column_pixels: int | None = Field(default=None, ge=1, le=10_000)
    default_row_height_points: float | None = Field(
        default=None, gt=0, le=409.5, allow_inf_nan=False
    )


@dataclass(frozen=True)
class LayoutTransform:
    edit: NativeLayoutEdit

    def point(self, value: int, *, clamp: bool = False) -> int:
        if not 1 <= value <= self.edit.limit:
            raise ValueError("Layout coordinate exceeds worksheet bounds")
        return value
