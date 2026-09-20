"""Native note identities and explicit content/reference operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal, Protocol

from pydantic import Field, field_validator

from src.domain.native_asset_models import ASSET_ID_PATTERN, SHA256_PATTERN, NativeModel
from src.domain.native_docx_stories import StoryEdit  # noqa: TC001 -- schema
from src.domain.native_docx_structure import NativeDocxBlock, bounded_blocks

if TYPE_CHECKING:
    from collections.abc import Iterator

    from src.domain.native_asset_models import NativeEditResult

NoteKind = Literal["footnote", "endnote"]
NoteId = Annotated[int, Field(ge=-(2**31), le=2**31 - 1)]
Digest = Annotated[str, Field(pattern=SHA256_PATTERN)]
NativePath = Annotated[
    list[Annotated[int, Field(ge=0, le=100_000)]], Field(min_length=1, max_length=64)
]
NOTE_REVIEW = [
    "semantic_accuracy",
    "rendered_layout",
    "reference_marks_and_numbering",
    "footnote_endnote_placement",
    "fields_revisions_and_custom_marks",
]


class DocxNoteLocator(NativeModel):
    part: str = Field(min_length=1, max_length=1024)
    note_kind: NoteKind
    note_id: NoteId


class DocxNoteReference(NativeModel):
    schema_version: Literal["native-docx-note-ref-v1"] = "native-docx-note-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: Digest
    locator: DocxNoteLocator
    value_sha256: Digest
    verification_scope: Literal["immutable_native_representation"] = (
        "immutable_native_representation"
    )


class DocxNoteUpdate(NativeModel):
    locator: DocxNoteLocator
    shared_scope: Literal["all_native_references"]
    edits: list[StoryEdit] = Field(min_length=1, max_length=32)


class DocxNoteAnchor(NativeModel):
    text_path: NativePath
    character_offset: int = Field(ge=0, le=4 * 1024 * 1024)
    expected_text_sha256: Digest


class DocxNoteCreate(NativeModel):
    op: Literal["create"]
    note_kind: NoteKind
    part: str = Field(min_length=1, max_length=1024)
    note_id: int | None = Field(default=None, ge=1, le=2**31 - 1)
    anchor: DocxNoteAnchor
    blocks: list[NativeDocxBlock] = Field(min_length=1, max_length=100)

    @field_validator("blocks")
    @classmethod
    def bounded(cls, value: list[NativeDocxBlock]) -> list[NativeDocxBlock]:
        return bounded_blocks(value)


class DocxNoteDelete(NativeModel):
    op: Literal["delete"]
    locator: DocxNoteLocator
    expected_note_sha256: Digest
    literal_body_text: Literal["preserve"]


NoteStructureEdit = Annotated[
    DocxNoteCreate | DocxNoteDelete, Field(discriminator="op")
]


class DocxNotesUpdate(NativeModel):
    expected_catalog_sha256: Digest
    scope: Literal["definitions_and_native_body_references"]
    edits: list[NoteStructureEdit] = Field(min_length=1, max_length=32)


class NativeDocxNoteAdapter(Protocol):
    def decompose(self, data: bytes) -> Iterator[dict[str, Any]]: ...
    def inspect(self, data: bytes) -> dict[str, Any]: ...
    def read(self, data: bytes, locator: DocxNoteLocator) -> dict[str, Any]: ...
    def edit(
        self, data: bytes, request: DocxNoteUpdate
    ) -> tuple[bytes, NativeEditResult]: ...
    def change_structure(
        self, data: bytes, request: DocxNotesUpdate
    ) -> tuple[bytes, NativeEditResult]: ...
