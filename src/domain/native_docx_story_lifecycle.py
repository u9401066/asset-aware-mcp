"""Explicit whole-definition lifecycle and section inheritance edits."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from src.domain.native_asset_models import SHA256_PATTERN, NativeModel
from src.domain.native_docx_structure import NativeDocxBlock, bounded_blocks

NewPart = Annotated[
    str,
    Field(pattern=r"^word/(?:[A-Za-z0-9-]+/)*[A-Za-z0-9_-]+\.xml$", max_length=1024),
]
ExistingPart = Annotated[str, Field(min_length=1, max_length=1024)]
Digest = Annotated[str, Field(pattern=SHA256_PATTERN)]


class StoryCreate(NativeModel):
    op: Literal["create"]
    part: NewPart
    story_kind: Literal["header", "footer"]
    blocks: list[NativeDocxBlock] = Field(min_length=1, max_length=100)

    @field_validator("blocks")
    @classmethod
    def bounded(cls, value: list[NativeDocxBlock]) -> list[NativeDocxBlock]:
        return bounded_blocks(value)


class StoryClone(NativeModel):
    op: Literal["clone"]
    source_part: ExistingPart
    source_part_sha256: Digest
    part: NewPart


class StoryBind(NativeModel):
    op: Literal["bind"]
    section_index: int = Field(ge=0, lt=2000)
    story_kind: Literal["header", "footer"]
    variant: Literal["default", "first", "even"]
    part: ExistingPart | None


class StoryRemove(NativeModel):
    op: Literal["delete"]
    part: ExistingPart
    expected_part_sha256: Digest


class StoryFirstPage(NativeModel):
    op: Literal["first_page"]
    section_index: int = Field(ge=0, lt=2000)
    enabled: bool


class StoryEvenPages(NativeModel):
    op: Literal["even_pages"]
    enabled: bool


StoryStructureEdit = Annotated[
    StoryCreate
    | StoryClone
    | StoryBind
    | StoryRemove
    | StoryFirstPage
    | StoryEvenPages,
    Field(discriminator="op"),
]


class DocxStoryStructure(NativeModel):
    expected_catalog_sha256: Digest
    scope: Literal["sections_and_following_inheritors"]
    edits: list[StoryStructureEdit] = Field(min_length=1, max_length=32)
