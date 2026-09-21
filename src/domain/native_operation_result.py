"""Operation-result identity binds exact native history without semantic claims."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from src.domain.native_asset_models import (
    ASSET_ID_PATTERN,
    SHA256_PATTERN,
    NativeAssetRevision,
    NativeEditResult,
    NativeModel,
)


def result_binding(
    asset_id: str, index: int, entry: NativeAssetRevision
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "history_index": index,
        "revision": entry.sha256,
        "parent_revision": entry.parent_sha256,
        "operation": entry.operation,
    }


class NativeOperationResultBlob(NativeModel):
    schema_version: Literal["native-operation-result-v1"] = "native-operation-result-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    history_index: int = Field(ge=0, lt=10000)
    revision: str = Field(pattern=SHA256_PATTERN)
    parent_revision: str | None = Field(default=None, pattern=SHA256_PATTERN)
    operation: str
    result: NativeEditResult
