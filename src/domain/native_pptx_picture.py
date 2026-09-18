"""Cross-asset picture insertion and explicitly preserved image mapping."""

from typing import Literal

from pydantic import Field, field_validator

from src.domain.native_file_reference import NativeFileReference
from src.domain.native_pptx import (
    NativePptxReference,
    NativePptxShapeContainer,
    PptxModel,
    xml_text,
)


class NativePptxPictureCreate(PptxModel):
    container: NativePptxShapeContainer
    image: NativeFileReference
    left: int = Field(ge=0, le=100_000_000)
    top: int = Field(ge=0, le=100_000_000)
    width: int = Field(ge=1, le=100_000_000)
    height: int = Field(ge=1, le=100_000_000)
    fit: Literal["contain", "cover", "stretch"] = "contain"
    name: str = Field(default="Picture", min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)

    @field_validator("name", "description")
    @classmethod
    def valid_xml(cls, value: str) -> str:
        return xml_text(value)


class NativePptxPictureReplace(PptxModel):
    reference: NativePptxReference
    image: NativeFileReference
    mapping: Literal["preserve_existing"] = "preserve_existing"
