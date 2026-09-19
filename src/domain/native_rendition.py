"""Explicit workbook rendering intent and its optional conversion port."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import Field, field_validator

from src.domain.native_asset_models import NativeModel


class NativeWorkbookRendition(NativeModel):
    name: str = Field(default="workbook-preview.pdf", min_length=5, max_length=200)
    mode: Literal["print", "whole_sheet"]
    calculation: Literal["recalculate", "prefer_cache"]

    @field_validator("name")
    @classmethod
    def basename(cls, value: str) -> str:
        if not value.lower().endswith(".pdf") or any(c in value for c in "/\\:\x00"):
            raise ValueError("Rendition name must be a basename ending in .pdf")
        return value


class NativeWorkbookRenderer(Protocol):
    def convert(
        self, data: bytes, request: NativeWorkbookRendition
    ) -> tuple[bytes, dict[str, Any]]: ...
