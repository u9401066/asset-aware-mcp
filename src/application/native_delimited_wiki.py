"""Dialect-bound delimited evidence with exact native source attachments."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_wiki_format import NativeWikiContent, canonical_json, digest
from src.domain.native_delimited import DELIMITED_REVIEW, NativeDelimitedDialect

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata


class NativeDelimitedWikiContent(NativeWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        structure: dict[str, Any],
    ):
        self.dialect = NativeDelimitedDialect.model_validate(structure["dialect"])
        self.projection = "delimited-fields-v1:" + digest(
            canonical_json(structure["dialect"])
        )
        super().__init__(identity, contract, metadata, projection=self.projection)
        self.source_name = self.prefix + "." + identity["format"]
        self.row_count = structure["row_count"]
        self.add_file("structure.json", canonical_json(structure) + b"\n")

    def add_field(self, field: dict[str, Any]) -> None:
        locator = field["locator"]
        stem = f"{self.prefix}-field-{digest(canonical_json(locator))}"
        title = f"Row {locator['row'] + 1}, column {locator['column'] + 1}"
        presentation = render_citation(
            self.contract,
            self.metadata,
            source_id=self.identity["asset_id"],
            asset_id=self.identity["asset_id"],
            title=self.identity["name"],
            locator={**locator, "line_range": field["line_range"]},
        )
        record = {**field, "note": stem + ".md", "citation_presentation": presentation}
        line = canonical_json(record) + b"\n"
        self.reserve(len(line))
        self.records.append(line)
        self.links.append(f"- [[{stem}|{title}]]")
        # JSON spelling keeps empty strings and embedded control characters visible.
        displayed = citation_markdown(json.dumps(field["value"], ensure_ascii=False))
        self.add_file(
            stem + ".md",
            (
                f"# {title}\n\nStored string (JSON spelling): {displayed}\n\n"
                f"Citation: {citation_markdown(presentation['inline'])}\n\n"
                f"Reference: {citation_markdown(presentation['reference'])}\n\n"
                f"Source asset: `{self.identity['asset_id']}`\n\nRevision: `{self.identity['revision']}`\n\n"
                f"Field representation SHA-256: `{field['evidence']['value_sha256']}`\n\n"
                "Logical row/column labels above are one-based; canonical locators are zero-based. "
                "Byte spans address the original file; character spans exclude its BOM. "
                "Headers, types, formulas and meaning are not inferred.\n\n"
                f"[Original file]({self.source_name}) · [Complete records](records.jsonl) · "
                f"[Dialect and rows](structure.json) · [[{self.index_name[:-3]}|Source index]]\n"
            ).encode(),
        )

    def manifest_details(self) -> dict[str, Any]:
        return {
            **self.record_counts(),
            "row_count": self.row_count,
            "representation": "delimited_fields",
            "projection": self.projection,
            "dialect": self.dialect.model_dump(mode="json"),
            "structure_file": "structure.json",
            "extraction_scope": "exact string values, raw field spelling, original byte/char/line spans; no header/type inference",
        }

    def review_required(self) -> list[str]:
        return list(DELIMITED_REVIEW)

    def _index(self) -> bytes:
        return (
            f"# {citation_markdown(self.identity['name'])}\n\n"
            f"Source asset: `{self.identity['asset_id']}`\n\nRevision: `{self.identity['revision']}`\n\n"
            f"[Original file]({self.source_name}) · [Evidence records](records.jsonl) · [Dialect and rows](structure.json)\n\n"
            f"{self.row_count} logical rows and {len(self.records)} string fields. Blank rows have zero fields. "
            "Physical lines may occur inside fields. Agent reviews meaning and downstream interpretation. "
            "Keep synthesis in adjacent curated notes; this snapshot is immutable.\n\n"
            + "\n".join(self.links)
            + "\n"
        ).encode()
