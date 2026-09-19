"""Immutable captured extraction references and IO ports, independent of storage."""

from __future__ import annotations

from typing import Any, Final, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

MAX_ETL_SNAPSHOT_BYTES = 128 * 1024 * 1024
MAX_ETL_METADATA_BYTES = 20 * 1024 * 1024
MAX_ETL_RECORD_BYTES = 2 * 1024 * 1024
ETL_REFERENCE_VERSION: Final = "etl-citation-ref-v1"


class EtlSourceSelector(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    doc_id: str = Field(pattern=r"^doc_[a-z0-9_]+$", max_length=256)
    source_type: Literal["span", "table", "figure"]
    source_id: str = Field(min_length=1, max_length=256)


class EtlEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["etl-citation-ref-v1"] = ETL_REFERENCE_VERSION
    snapshot_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    record_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    doc_id: str = Field(pattern=r"^doc_[a-z0-9_]+$", max_length=256)
    source_type: Literal["span", "table", "figure"]
    source_id: str = Field(min_length=1, max_length=256)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    verification_scope: Literal["immutable_captured_extraction"] = (
        "immutable_captured_extraction"
    )


class EtlSourceReader(Protocol):
    def capture(self, doc_id: str, figure_id: str | None) -> dict[str, bytes]: ...

    def decode_text(self, data: bytes) -> str: ...


class EtlSnapshotRepository(Protocol):
    def save(self, snapshot_id: str, files: dict[str, bytes]) -> None: ...

    def read(self, snapshot_id: str) -> dict[str, bytes]: ...


class EtlCitationSources(Protocol):
    def resolve(
        self, reference: EtlEvidenceReference
    ) -> tuple[dict[str, Any], dict[str, bytes]]: ...
