"""Native PDF page identity, composition and geometry contracts without IO."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from src.domain.native_assets import NativeEditResult
    from src.domain.native_pdf_annotations import (
        PdfAnnotationLocator,
        PdfAnnotationsUpdate,
    )
    from src.domain.native_pdf_region import NativePdfRegionSelector

MAX_PDF_PAGES = 2000
MAX_PDF_BATCH = 100
PDF_MEDIA_TYPE = "application/pdf"


class PdfModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class NativePdfPageLocator(PdfModel):
    page_index: int = Field(ge=0, lt=MAX_PDF_PAGES)
    object_id: int = Field(ge=1)
    generation: int = Field(ge=0)


class NativePdfReference(PdfModel):
    schema_version: Literal["native-pdf-page-ref-v1"] = "native-pdf-page-ref-v1"
    asset_id: str = Field(pattern=r"^file_[a-f0-9]{32}$")
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    locator: NativePdfPageLocator
    value_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


class NativePdfBlankPage(PdfModel):
    width: float = Field(default=595.0, ge=3, le=14400, allow_inf_nan=False)
    height: float = Field(default=842.0, ge=3, le=14400, allow_inf_nan=False)


class NativePdfPageInput(PdfModel):
    model_config = ConfigDict(
        json_schema_extra={
            "oneOf": [
                {
                    "required": ["blank"],
                    "properties": {
                        "blank": {"not": {"type": "null"}},
                        "reference": {"type": "null"},
                    },
                },
                {
                    "required": ["reference"],
                    "properties": {
                        "reference": {"not": {"type": "null"}},
                        "blank": {"type": "null"},
                    },
                },
            ]
        }
    )
    blank: NativePdfBlankPage | None = None
    reference: NativePdfReference | None = None

    @model_validator(mode="after")
    def single_source(self) -> NativePdfPageInput:
        if (self.blank is None) == (self.reference is None):
            raise ValueError("PDF page input requires exactly one blank or reference")
        return self


class NativePdfCreate(PdfModel):
    name: str = Field(min_length=5, max_length=200)
    pages: list[NativePdfPageInput] = Field(min_length=1, max_length=MAX_PDF_BATCH)

    @field_validator("name")
    @classmethod
    def basename(cls, value: str) -> str:
        if not value.lower().endswith(".pdf") or any(c in value for c in "/\\:\x00"):
            raise ValueError("PDF name must be a basename ending in .pdf")
        return value


class NativePdfInsert(PdfModel):
    position: int = Field(ge=0, le=MAX_PDF_PAGES)
    pages: list[NativePdfPageInput] = Field(min_length=1, max_length=MAX_PDF_BATCH)


class NativePdfPageEdit(PdfModel):
    model_config = ConfigDict(
        json_schema_extra={
            "anyOf": [
                {"required": [name], "properties": {name: {"not": {"type": "null"}}}}
                for name in ("rotation", "crop_box")
            ]
        }
    )
    reference: NativePdfReference
    rotation: Literal[0, 90, 180, 270] | None = None
    crop_box: list[float] | None = Field(default=None, min_length=4, max_length=4)

    @field_validator("rotation", mode="before")
    @classmethod
    def integer_rotation(cls, value: Any) -> Any:
        if value is not None and type(value) is not int:
            raise ValueError("PDF rotation must be an integer degree value")
        return value

    @model_validator(mode="after")
    def geometry(self) -> NativePdfPageEdit:
        if self.rotation is None and self.crop_box is None:
            raise ValueError("PDF page edit requires rotation or crop_box")
        if self.crop_box is not None:
            x0, y0, x1, y1 = self.crop_box
            if not all(math.isfinite(v) for v in self.crop_box) or x0 >= x1 or y0 >= y1:
                raise ValueError("PDF crop_box must be a finite, positive rectangle")
        return self


class NativePdfAdapter(Protocol):
    def inspect_annotations(self, data: bytes) -> dict[str, Any]: ...
    def read_annotation(
        self, data: bytes, locator: PdfAnnotationLocator
    ) -> dict[str, Any]: ...
    def decompose_annotations(self, data: bytes) -> list[dict[str, Any]]: ...
    def edit_annotations(
        self, data: bytes, request: PdfAnnotationsUpdate
    ) -> tuple[bytes, NativeEditResult]: ...
    def decompose(self, data: bytes) -> list[dict[str, Any]]: ...
    def inspect(self, data: bytes) -> dict[str, Any]: ...
    def read_page(
        self, data: bytes, locator: NativePdfPageLocator
    ) -> dict[str, Any]: ...
    def create(
        self, request: NativePdfCreate, sources: dict[str, bytes]
    ) -> tuple[bytes, NativeEditResult]: ...
    def insert(
        self, data: bytes, request: NativePdfInsert, sources: dict[str, bytes]
    ) -> tuple[bytes, NativeEditResult]: ...
    def edit(
        self, data: bytes, edits: list[NativePdfPageEdit]
    ) -> tuple[bytes, NativeEditResult]: ...
    def delete(
        self, data: bytes, references: list[NativePdfReference]
    ) -> tuple[bytes, NativeEditResult]: ...
    def reorder(
        self, data: bytes, references: list[NativePdfReference]
    ) -> tuple[bytes, NativeEditResult]: ...
    def render(
        self, data: bytes, locator: NativePdfPageLocator, width: int
    ) -> bytes: ...
    def render_region(
        self,
        data: bytes,
        locator: NativePdfPageLocator,
        selector: NativePdfRegionSelector,
        width: int,
    ) -> dict[str, Any]: ...
