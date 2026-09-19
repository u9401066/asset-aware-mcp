"""Revision-scoped presentation structure with explicit layout and slide identities."""

from __future__ import annotations

from pydantic import Field, model_validator

from src.domain.native_pptx import (
    MAX_PPTX_COMPONENTS,
    NativePptxTextBoxCreate,
    PptxModel,
)

MAX_SLIDES = 2000


class NativePptxSlideKey(PptxModel):
    slide_id: str = Field(pattern=r"^[1-9][0-9]*$", max_length=10)
    part: str = Field(min_length=1, max_length=1024)


class NativePptxSlideAddition(PptxModel):
    layout_part: str = Field(min_length=1, max_length=1024)
    textboxes: list[NativePptxTextBoxCreate] = Field(
        default_factory=list, max_length=100
    )


class NativePptxSlideInsert(PptxModel):
    index: int = Field(ge=0, le=MAX_SLIDES)
    slides: list[NativePptxSlideAddition] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def bounded_content(self) -> NativePptxSlideInsert:
        runs = [
            r for s in self.slides for b in s.textboxes for p in b.paragraphs for r in p
        ]
        if (
            len(runs) > MAX_PPTX_COMPONENTS
            or sum(len(r.text.encode("utf-8")) for r in runs) > 4 * 1024 * 1024
        ):
            raise ValueError("Slide additions exceed 20,000 runs or 4 MiB UTF-8 text")
        return self
