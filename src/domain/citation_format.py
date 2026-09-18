"""Declarative citation display, independent of canonical evidence identity."""

from __future__ import annotations

import hashlib
import json
from string import Formatter
from typing import Any, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

FORMAT_VERSION: Final = "citation-format-v1"
FORMAT_FIELDS = frozenset(
    {
        "source_id",
        "asset_id",
        "span_id",
        "citation_key",
        "title",
        "authors",
        "year",
        "doi",
        "url",
        "reference_number",
        "page",
        "section",
        "locator",
    }
)
MAX_RENDERED_CHARS = 8192


class CitationMetadata(BaseModel):
    """Caller-supplied bibliographic data; never canonical locator overrides."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    title: str = Field("", max_length=1024)
    authors: str = Field("", max_length=1024)
    year: str = Field("", max_length=32)
    doi: str = Field("", max_length=512)
    url: str = Field("", max_length=2048)
    reference_number: int | None = Field(None, ge=1, strict=True)


class CitationFormatPreset(BaseModel):
    """A display-only preset selector, with no provenance or template overrides."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    preset: Literal["source", "author-year", "numeric"]


class CitationFormatContract(BaseModel):
    """A bounded named-field template, not a programming language or CSL engine."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["citation-format-v1"] = FORMAT_VERSION
    name: str = Field("custom", min_length=1, max_length=100)
    inline_template: str = Field(min_length=1, max_length=2048)
    reference_template: str = Field(min_length=1, max_length=2048)
    required_fields: tuple[str, ...] = Field(default=(), max_length=len(FORMAT_FIELDS))

    @model_validator(mode="after")
    def validate_templates(self) -> CitationFormatContract:
        for template in (self.inline_template, self.reference_template):
            for _literal, field, spec, conversion in Formatter().parse(template):
                if field is not None and (
                    field not in FORMAT_FIELDS or spec or conversion
                ):
                    raise ValueError(
                        "Citation templates allow named scalar fields only: "
                        + ", ".join(sorted(FORMAT_FIELDS))
                    )
        if set(self.required_fields) - FORMAT_FIELDS:
            raise ValueError("Unknown required citation fields")
        return self

    @property
    def contract_sha256(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def render(self, values: dict[str, str]) -> dict[str, str]:
        required = set(self.required_fields)
        for template in (self.inline_template, self.reference_template):
            required.update(
                field
                for _, field, _, _ in Formatter().parse(template)
                if field is not None
            )
        missing = sorted(
            field for field in required if not values.get(field, "").strip()
        )
        if missing:
            raise ValueError("Missing citation metadata: " + ", ".join(missing))
        # Preflight each substitution before constructing a potentially large string.
        rendered: dict[str, str] = {}
        for key, template in (
            ("inline", self.inline_template),
            ("reference", self.reference_template),
        ):
            parts: list[str] = []
            size = 0
            for literal, field, _, _ in Formatter().parse(template):
                value = values[field] if field is not None else ""
                size += len(literal) + len(value)
                if size > MAX_RENDERED_CHARS:
                    raise ValueError("Rendered citation exceeds character limit")
                parts.extend((literal, value))
            rendered[key] = "".join(parts)
        return {"contract_sha256": self.contract_sha256, **rendered}


def citation_format_presets() -> dict[str, dict[str, Any]]:
    """Fresh declarative presets; numeric numbering belongs to the caller."""
    return {
        "source": {
            "name": "source",
            "inline_template": "[{source_id}, {locator}]",
            "reference_template": "{title} ({source_id})",
        },
        "author-year": {
            "name": "author-year",
            "inline_template": "({authors}, {year}, {locator})",
            "reference_template": "{authors} ({year}). {title}.",
        },
        "numeric": {
            "name": "numeric",
            "inline_template": "[{reference_number}]",
            "reference_template": "[{reference_number}] {title}. {source_id}",
        },
    }


def resolve_citation_format(value: dict[str, Any]) -> CitationFormatContract:
    """Accept a full contract or a preset selector, never silently ignore fields."""
    if "preset" in value:
        if set(value) != {"preset"}:
            raise ValueError("A preset selector cannot contain contract overrides")
        preset = value["preset"]
        if not isinstance(preset, str) or preset not in citation_format_presets():
            raise ValueError("Unknown citation format preset")
        value = citation_format_presets()[preset]
    return CitationFormatContract.model_validate(value)
