"""Ports for version-bound DOCX editing through the existing DFM workflow."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from src.domain.native_assets import NativeEditResult
    from src.domain.repositories import DocumentRepository

MAX_DFM_BYTES = 4 * 1024 * 1024


class NativeDocxEdit(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    dfm_text: str = Field(min_length=1, max_length=MAX_DFM_BYTES)
    track_changes: bool = False
    revision_author: str = Field(
        default="Asset-Aware MCP", min_length=1, max_length=200
    )

    @field_validator("dfm_text", "revision_author")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", value):
            raise ValueError(
                "DOCX edit text contains characters unavailable in XML 1.0"
            )
        if len(value.encode("utf-8")) > MAX_DFM_BYTES:
            raise ValueError("DFM exceeds the 4 MiB UTF-8 limit")
        return value


@dataclass
class NativeDocxRead:
    dfm_text: str
    blocks: list[dict[str, Any]]


class NativeDocxWorkspace(Protocol):
    repository: DocumentRepository
    source_path: str

    def read_result(
        self, path: str, changed_blocks: list[str], track_changes: bool
    ) -> tuple[bytes, NativeEditResult]: ...


class NativeDocxWorkspaces(Protocol):
    def open(
        self, data: bytes, *, for_edit: bool = False
    ) -> AbstractContextManager[NativeDocxWorkspace]: ...


class NativeDocxAdapter(Protocol):
    def read(self, data: bytes, asset_id: str, revision: str) -> NativeDocxRead: ...

    def edit(
        self, data: bytes, asset_id: str, revision: str, edit: NativeDocxEdit
    ) -> tuple[bytes, NativeEditResult, list[str]]: ...
