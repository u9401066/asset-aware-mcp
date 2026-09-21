"""Revision-pinned derivation assertions, distinct from machine evidence checks."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator

from src.domain.native_asset_models import (
    ASSET_ID_PATTERN,
    SHA256_PATTERN,
    NativeCellReference,
    NativeDocxBlockReference,
    NativeModel,
)
from src.domain.native_delimited import NativeDelimitedReference
from src.domain.native_docx_notes import DocxNoteReference
from src.domain.native_docx_stories import DocxStoryReference
from src.domain.native_file_reference import NativeFileReference
from src.domain.native_pdf import NativePdfReference
from src.domain.native_pdf_annotations import PdfAnnotationReference
from src.domain.native_pdf_region import NativePdfRegionReference
from src.domain.native_pptx import NativePptxReference
from src.domain.native_selection import NativeSelectionReference

NativeReference = (
    NativeCellReference
    | NativeDocxBlockReference
    | DocxStoryReference
    | DocxNoteReference
    | NativePptxReference
    | NativePdfReference
    | PdfAnnotationReference
    | NativePdfRegionReference
    | NativeDelimitedReference
    | NativeFileReference
    | NativeSelectionReference
)
ReviewResult = Literal["not_checked", "passed", "failed", "not_applicable"]
MAX_DERIVATION_BYTES = 16 * 1024 * 1024


def canonical(value: BaseModel) -> bytes:
    return json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def fingerprint(value: BaseModel) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


class NativeAgentReview(NativeModel):
    """Caller assertions only; the server does not authenticate or endorse them."""

    semantic_accuracy: ReviewResult = "not_checked"
    rendered_layout: ReviewResult = "not_checked"
    formula_results: ReviewResult = "not_checked"
    notes: str = Field(default="", max_length=4096)


class NativeDerivation(NativeModel):
    target: NativeReference
    sources: list[NativeReference] = Field(min_length=1, max_length=64)
    activity: str = Field(min_length=1, max_length=2000)
    agent: str = Field(min_length=1, max_length=256)
    review: NativeAgentReview = Field(default_factory=NativeAgentReview)
    supersedes: str | None = Field(default=None, pattern=SHA256_PATTERN)

    @field_validator("activity", "agent")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Derivation activity and agent must be nonblank")
        return value

    @model_validator(mode="after")
    def distinct_sources(self) -> NativeDerivation:
        sources = [fingerprint(ref) for ref in self.sources]
        if len(set(sources)) != len(sources):
            raise ValueError("Derivation source references must be unique")
        if fingerprint(self.target) in sources:
            raise ValueError("A derivation cannot cite its exact target as a source")
        return self


class NativeDerivationRecord(NativeModel):
    kind: Literal["record"] = "record"
    derivation_id: str = Field(pattern=SHA256_PATTERN)
    derivation: NativeDerivation

    @model_validator(mode="after")
    def check_identity(self) -> NativeDerivationRecord:
        if fingerprint(self.derivation) != self.derivation_id:
            raise ValueError("Derivation record hash mismatch")
        return self


class NativeDerivationRetraction(NativeModel):
    kind: Literal["retract"] = "retract"
    derivation_id: str = Field(pattern=SHA256_PATTERN)
    agent: str = Field(min_length=1, max_length=256)
    reason: str = Field(min_length=1, max_length=2000)

    @field_validator("agent", "reason")
    @classmethod
    def nonblank(cls, value: str) -> str:
        return NativeDerivation.nonblank(value)


NativeDerivationEvent = Annotated[
    NativeDerivationRecord | NativeDerivationRetraction, Field(discriminator="kind")
]


class NativeDerivationLedger(NativeModel):
    schema_version: Literal["native-derivations-v1"] = "native-derivations-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    events: list[NativeDerivationEvent] = Field(default_factory=list, max_length=1000)

    def active_records(self) -> dict[str, NativeDerivationRecord]:
        active: dict[str, NativeDerivationRecord] = {}
        seen = set()
        for event in self.events:
            if isinstance(event, NativeDerivationRecord):
                if event.derivation.target.asset_id != self.asset_id:
                    raise ValueError("Derivation target belongs to a different asset")
                if event.derivation_id in seen:
                    raise ValueError("Derivation record already exists in this ledger")
                if event.derivation.supersedes:
                    self._remove(active, event.derivation.supersedes)
                active[event.derivation_id] = event
                seen.add(event.derivation_id)
            else:
                self._remove(active, event.derivation_id)
        return active

    @staticmethod
    def _remove(active: dict[str, NativeDerivationRecord], identity: str) -> None:
        if identity not in active:
            raise ValueError("Cannot retract/supersede an unknown or inactive record")
        del active[identity]

    @model_validator(mode="after")
    def validate_history(self) -> NativeDerivationLedger:
        self.active_records()
        return self


class NativeDerivationRepository(Protocol):
    def load(self, asset_id: str) -> NativeDerivationLedger: ...
    def append(
        self, asset_id: str, expected_sha256: str, event: NativeDerivationEvent
    ) -> NativeDerivationLedger: ...
