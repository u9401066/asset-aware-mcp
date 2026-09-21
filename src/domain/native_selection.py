"""Exact selections in immutable parsed representations, without semantic inference."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

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
from src.domain.native_pdf import NativePdfReference
from src.domain.native_pdf_annotations import PdfAnnotationReference
from src.domain.native_pdf_region import NativePdfRegionReference
from src.domain.native_pptx import NativePptxReference

NativeSelectionParent = (
    NativeCellReference
    | NativeDocxBlockReference
    | DocxStoryReference
    | DocxNoteReference
    | NativePptxReference
    | NativePdfReference
    | PdfAnnotationReference
    | NativePdfRegionReference
    | NativeDelimitedReference
)
MAX_SELECTION_BYTES = 16 * 1024 * 1024


class NativeCharacterRange(NativeModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def nonempty(self) -> NativeCharacterRange:
        if self.start >= self.end:
            raise ValueError("Character ranges must be nonempty and half-open")
        return self


class NativeSelectionSelector(NativeModel):
    pointer: str = Field(default="", max_length=2048)
    char_range: NativeCharacterRange | None = None

    @field_validator("pointer")
    @classmethod
    def valid_pointer(cls, value: str) -> str:
        if value and not value.startswith("/"):
            raise ValueError("Use a JSON Pointer, not a URI fragment or JSONPath")
        if re.search(r"~(?![01])|[\ud800-\udfff]", value) or value.count("/") > 64:
            raise ValueError("Invalid JSON Pointer escape, Unicode or depth")
        return value


class NativeSelectionReference(NativeModel):
    schema_version: Literal["native-selection-ref-v1"] = "native-selection-ref-v1"
    asset_id: str = Field(pattern=ASSET_ID_PATTERN)
    revision: str = Field(pattern=SHA256_PATTERN)
    parent: NativeSelectionParent
    selector: NativeSelectionSelector
    value_sha256: str = Field(pattern=SHA256_PATTERN)
    verification_scope: Literal["immutable_representation_selection"] = (
        "immutable_representation_selection"
    )

    @model_validator(mode="after")
    def bound_parent(self) -> NativeSelectionReference:
        if (
            self.asset_id != self.parent.asset_id
            or self.revision != self.parent.revision
        ):
            raise ValueError("Selection identity must match its full parent reference")
        return self


def canonical_selection(value: Any) -> bytes:
    data = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if len(data) > MAX_SELECTION_BYTES:
        raise ValueError("Native selection exceeds the 16 MiB output budget")
    return data


def resolve_pointer(value: Any, pointer: str) -> Any:
    for encoded in pointer.split("/")[1:] if pointer else []:
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if token not in value:
                raise ValueError("JSON Pointer names a missing member")
            value = value[token]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token) or int(token) >= len(value):
                raise ValueError("JSON Pointer array index is invalid or out of range")
            value = value[int(token)]
        else:
            raise ValueError("JSON Pointer cannot traverse a scalar value")
    return value


def selection_record(
    parent: NativeSelectionParent,
    selector: NativeSelectionSelector,
    representation: dict[str, Any],
) -> dict[str, Any]:
    value = resolve_pointer(representation, selector.pointer)
    context = None
    if selector.char_range is not None and not isinstance(value, str):
        raise ValueError("Character ranges require a selected JSON string")
    if isinstance(value, str):
        start, end = (
            (selector.char_range.start, selector.char_range.end)
            if selector.char_range
            else (0, len(value))
        )
        if end > len(value):
            raise ValueError("Selection character range exceeds the parsed string")
        context = {
            "char_range": [start, end],
            "utf8_byte_range": [
                len(value[:start].encode("utf-8")),
                len(value[:end].encode("utf-8")),
            ],
            "source_text_length": len(value),
            "source_text_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "prefix": value[max(0, start - 64) : start],
            "suffix": value[end : end + 64],
            "coordinate_scope": "Unicode codepoints and UTF-8 bytes of the selected parsed string; not source-file offsets",
        }
        value = value[start:end]
    record = {
        "schema_version": "native-selection-v1",
        "parent": parent.model_dump(mode="json"),
        "selector": selector.model_dump(mode="json"),
        "value": value,
        "text_context": context,
    }
    record["evidence"] = NativeSelectionReference(
        asset_id=parent.asset_id,
        revision=parent.revision,
        parent=parent,
        selector=selector,
        value_sha256=hashlib.sha256(canonical_selection(record)).hexdigest(),
    ).model_dump(mode="json")
    return record
