"""Pinned native header/footer parts and explicit shared-content edits."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

from pydantic import Field, field_validator

from src.domain.native_asset_models import (
    ASSET_ID_PATTERN,
    SHA256_PATTERN,
    NativeModel,
)
from src.domain.native_docx_structure import (
    NativeDocxBlock,
    bounded_blocks,
    xml_text,
)

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult

STORY_REVIEW = [
    "semantic_accuracy",
    "rendered_layout",
    "all_shared_section_uses",
    "inherited_and_disabled_definitions",
    "fields_and_revisions",
]


class DocxStoryLocator(NativeModel):
    part: str = Field(min_length=1, max_length=1024)
    story_kind: Literal["header", "footer"]


class DocxStoryReference(NativeModel):
    schema_version: Literal["native-docx-story-ref-v1"] = "native-docx-story-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    locator: DocxStoryLocator
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


class StoryTextEdit(NativeModel):
    op: Literal["set_text"]
    path: list[Annotated[int, Field(ge=0, le=20_000)]] = Field(
        min_length=1, max_length=64
    )
    text: str = Field(max_length=8000)

    @field_validator("text")
    @classmethod
    def valid_text(cls, value: str) -> str:
        return xml_text(value)


class StoryInsert(NativeModel):
    op: Literal["insert_blocks"]
    index: int = Field(ge=0, le=20_000)
    blocks: list[NativeDocxBlock] = Field(min_length=1, max_length=100)

    @field_validator("blocks")
    @classmethod
    def bounded(cls, value: list[NativeDocxBlock]) -> list[NativeDocxBlock]:
        return bounded_blocks(value)


class StoryDelete(NativeModel):
    op: Literal["delete_blocks"]
    index: int = Field(ge=0, le=20_000)
    count: int = Field(ge=1, le=100)


StoryEdit = Annotated[
    StoryTextEdit | StoryInsert | StoryDelete, Field(discriminator="op")
]


class DocxStoryUpdate(NativeModel):
    part: str = Field(min_length=1, max_length=1024)
    shared_scope: Literal["all_sections_using_part"]
    edits: list[StoryEdit] = Field(min_length=1, max_length=32)


class NativeDocxStoryAdapter(Protocol):
    def inspect(self, data: bytes) -> dict[str, Any]: ...
    def read(self, data: bytes, part: str) -> dict[str, Any]: ...
    def edit(
        self, data: bytes, request: DocxStoryUpdate
    ) -> tuple[bytes, NativeEditResult]: ...
