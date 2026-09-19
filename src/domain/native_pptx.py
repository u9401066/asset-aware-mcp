"""Native presentation components and precise, revision-scoped text edits."""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING, Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_assets import NativeEditResult
    from src.domain.native_pptx_grid import NativePptxTableGridEdit
    from src.domain.native_pptx_picture import (
        NativePptxPictureCreate,
        NativePptxPictureReplace,
    )
    from src.domain.native_pptx_table import NativePptxTableAddition

PPTX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)
MAX_PPTX_COMPONENTS = 20_000


def xml_text(value: str) -> str:
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value):
        raise ValueError("Presentation text contains characters unavailable in XML 1.0")
    return value


class PptxModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class NativePptxPartLocator(PptxModel):
    slide_id: str = Field(pattern=r"^[1-9][0-9]*$", max_length=10)
    part: str = Field(min_length=1, max_length=1024)
    region: Literal["slide", "notes"] = "slide"


class NativePptxShapeLocator(NativePptxPartLocator):
    shape_id: str = Field(pattern=r"^(0|[1-9][0-9]*)$", max_length=10)


class NativePptxShapeContainer(NativePptxPartLocator):
    group_shape_id: str | None = Field(
        default=None, pattern=r"^(0|[1-9][0-9]*)$", max_length=10
    )


class NativePptxRunLocator(NativePptxShapeLocator):
    row: int | None = Field(default=None, ge=0, le=20_000)
    column: int | None = Field(default=None, ge=0, le=20_000)
    paragraph: int = Field(ge=0, le=20_000)
    run: int = Field(ge=0, le=20_000)

    @model_validator(mode="after")
    def paired_coordinates(self) -> NativePptxRunLocator:
        if (self.row is None) != (self.column is None):
            raise ValueError(
                "Presentation table row and column must be supplied together"
            )
        return self


class NativePptxTextEdit(PptxModel):
    locator: NativePptxRunLocator
    expected_text_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    text: str = Field(max_length=32_767)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        xml_text(value)
        if any(char in value for char in "\n\r\t"):
            raise ValueError(
                "Run edits cannot introduce paragraph, line-break or tab structure"
            )
        return value


class NativePptxRunCreate(PptxModel):
    text: str = Field(max_length=8000)
    bold: bool = False
    italic: bool = False
    font_size_pt: int = Field(default=18, ge=1, le=400)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return NativePptxTextEdit.validate_text(value)


class NativePptxTextBoxCreate(PptxModel):
    left: int = Field(default=914400, ge=0, le=100_000_000)
    top: int = Field(default=914400, ge=0, le=100_000_000)
    width: int = Field(default=7315200, ge=1, le=100_000_000)
    height: int = Field(default=914400, ge=1, le=100_000_000)
    paragraphs: list[list[NativePptxRunCreate]] = Field(min_length=1, max_length=100)

    @field_validator("paragraphs")
    @classmethod
    def bounded_runs(
        cls, value: list[list[NativePptxRunCreate]]
    ) -> list[list[NativePptxRunCreate]]:
        if any(not runs or len(runs) > 100 for runs in value):
            raise ValueError("Each paragraph requires 1 to 100 runs")
        return value


class NativePptxShapeCreate(PptxModel):
    container: NativePptxShapeContainer
    textbox: NativePptxTextBoxCreate


def validate_shape_additions(
    items: list[NativePptxShapeCreate],
) -> list[NativePptxShapeCreate]:
    count, size = 0, 0
    for item in items:
        for paragraph in item.textbox.paragraphs:
            count += len(paragraph)
            size += sum(len(run.text.encode("utf-8")) for run in paragraph)
    if count > MAX_PPTX_COMPONENTS or size > 4 * 1024 * 1024:
        raise ValueError(
            "Presentation additions exceed 20,000 runs or 4 MiB UTF-8 text"
        )
    return items


def shape_representation_sha256(record: dict[str, Any]) -> str:
    """Keep the released shape-v1 digest stable for reads, edits and deletion."""
    value = {key: item for key, item in record.items() if key != "evidence"}
    value["schema_version"] = "native-pptx-shape-v1"
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class NativePptxSlideCreate(PptxModel):
    textboxes: list[NativePptxTextBoxCreate] = Field(
        default_factory=list, max_length=100
    )
    notes: str = Field(default="", max_length=32_767)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str) -> str:
        return xml_text(value)


class NativePresentationCreate(PptxModel):
    name: str = Field(min_length=6, max_length=200)
    width: int = Field(default=12192000, ge=1, le=100_000_000)
    height: int = Field(default=6858000, ge=1, le=100_000_000)
    slides: list[NativePptxSlideCreate] = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.lower().endswith(".pptx") or any(c in value for c in "/\\:\x00"):
            raise ValueError("Presentation name must be a basename ending in .pptx")
        return value

    @model_validator(mode="after")
    def bounded_presentation(self) -> NativePresentationCreate:
        count = 0
        size = 0
        for slide in self.slides:
            size += len(slide.notes.encode("utf-8"))
            for textbox in slide.textboxes:
                for paragraph in textbox.paragraphs:
                    count += len(paragraph)
                    size += sum(len(run.text.encode("utf-8")) for run in paragraph)
        if count > MAX_PPTX_COMPONENTS or size > 4 * 1024 * 1024:
            raise ValueError("Presentation exceeds 20,000 runs or 4 MiB of UTF-8 text")
        return self


class NativePptxReference(PptxModel):
    schema_version: Literal["native-pptx-shape-ref-v1"] = "native-pptx-shape-ref-v1"
    asset_id: str = Field(pattern=r"^file_[a-f0-9]{32}$")
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    locator: NativePptxShapeLocator
    value_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


class NativePresentationAdapter(Protocol):
    def edit_table_grid(
        self, data: bytes, request: NativePptxTableGridEdit
    ) -> tuple[bytes, NativeEditResult]: ...

    def add_tables(
        self, data: bytes, items: list[NativePptxTableAddition]
    ) -> tuple[bytes, NativeEditResult]: ...

    def add_pictures(
        self,
        data: bytes,
        items: list[NativePptxPictureCreate],
        sources: dict[str, bytes],
    ) -> tuple[bytes, NativeEditResult]: ...
    def replace_pictures(
        self,
        data: bytes,
        items: list[NativePptxPictureReplace],
        sources: dict[str, bytes],
    ) -> tuple[bytes, NativeEditResult]: ...
    def read_picture(
        self,
        data: bytes,
        locator: NativePptxShapeLocator,
        render_size: int | None = None,
    ) -> dict[str, Any]: ...
    def package_parts(self, data: bytes) -> dict[str, bytes]: ...
    def create(self, request: NativePresentationCreate) -> bytes: ...
    def inspect(self, data: bytes) -> dict[str, Any]: ...
    def iter_shapes(
        self, data: bytes, *, offset: int = 0, limit: int | None = None
    ) -> Iterator[dict[str, Any]]: ...
    def read_shape(
        self, data: bytes, locator: NativePptxShapeLocator
    ) -> dict[str, Any]: ...
    def edit(
        self, data: bytes, edits: list[NativePptxTextEdit]
    ) -> tuple[bytes, NativeEditResult]: ...
    def add_shapes(
        self, data: bytes, additions: list[NativePptxShapeCreate]
    ) -> tuple[bytes, NativeEditResult]: ...
    def delete_shapes(
        self, data: bytes, references: list[NativePptxReference]
    ) -> tuple[bytes, NativeEditResult]: ...
