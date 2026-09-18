"""A portable reference to complete immutable native file bytes."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NativeFileReference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["native-file-ref-v1"] = "native-file-ref-v1"
    asset_id: str = Field(pattern=r"^file_[a-f0-9]{32}$")
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    verification_scope: Literal["immutable_file_bytes"] = "immutable_file_bytes"
