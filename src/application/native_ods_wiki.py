"""Compressed ODS ranges with anchor-only references and complete operation receipts."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_wiki_format import NativeWikiContent, canonical_json, digest
from src.domain.native_ods import ODS_REVIEW

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata


class NativeODSWikiContent(NativeWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        structure: dict[str, Any],
        receipt: dict[str, Any] | None,
    ):
        self.projection = "ods-physical-ranges-v1:" + digest(canonical_json(receipt))
        super().__init__(identity, contract, metadata, projection=self.projection)
        self.source_name = self.prefix + ".ods"
        self.add_file("structure.json", canonical_json(structure) + b"\n")
        self.add_file("operation-result.json", canonical_json(receipt) + b"\n")

    def add_range(self, record: dict[str, Any]) -> None:
        locator = record["locator"]
        stem = f"{self.prefix}-range-{digest(canonical_json(locator))}"
        title = citation_markdown(
            f"{locator['table_name']}: row {locator['row'] + 1}, column {locator['column'] + 1}"
        )
        presentation = render_citation(
            self.contract,
            self.metadata,
            source_id=self.identity["asset_id"],
            asset_id=self.identity["asset_id"],
            title=self.identity["name"],
            locator=locator,
        )
        line = (
            canonical_json(
                {
                    **record,
                    "reference_scope": "logical_anchor_only",
                    "note": stem + ".md",
                    "citation_presentation": presentation,
                }
            )
            + b"\n"
        )
        self.reserve(len(line))
        self.records.append(line)
        self.links.append(f"- [[{stem}|{title}]]")
        display = citation_markdown(
            json.dumps(record["display_paragraphs"], ensure_ascii=False)
        )
        repetition = record["repetition"]
        self.add_file(
            stem + ".md",
            (
                f"# {title}\n\nStored display paragraphs: {display}\n\n"
                f"Physical range: {repetition['row_count']} rows × {repetition['column_count']} columns. "
                "The reference identifies the logical anchor only. Other coordinates require their own cell reads.\n\n"
                f"Citation: {citation_markdown(presentation['inline'])}\n\nReference: {citation_markdown(presentation['reference'])}\n\n"
                f"Cell representation SHA-256: `{record['evidence']['value_sha256']}`\n\n"
                "Covered cells, typed lexical values, formulas, unverified cached display and native XML are distinct in the complete record. "
                "Agent reviews meaning, rich text, calculated results and actual Calc appearance.\n\n"
                f"[Original ODS]({self.source_name}) · [Complete records](records.jsonl) · [Complete receipt](operation-result.json) · [[{self.index_name[:-3]}|Source index]]\n"
            ).encode(),
        )

    def record_counts(self) -> dict[str, int]:
        return {
            "physical_range_count": len(self.records),
            "logical_anchor_reference_count": len(self.records),
        }

    def manifest_details(self) -> dict[str, Any]:
        return {
            **self.record_counts(),
            "projection": self.projection,
            "representation": "ods_physical_ranges",
            "structure_file": "structure.json",
            "operation_result_file": "operation-result.json",
            "extraction_scope": "compressed physical cell ranges; references identify logical anchors only; implicit cells require explicit cell reads",
        }

    def review_required(self) -> list[str]:
        return list(ODS_REVIEW)

    def _index(self) -> bytes:
        return (
            f"# {citation_markdown(self.identity['name'])}\n\n"
            f"Source asset: `{self.identity['asset_id']}`\n\nRevision: `{self.identity['revision']}`\n\n"
            f"[Original ODS]({self.source_name}) · [Complete records](records.jsonl) · [Tables](structure.json) · [Operation receipt](operation-result.json)\n\n"
            f"{len(self.records)} physical ranges with logical anchor references. Repeated ranges stay compressed; "
            "implicit cells are not enumerated. Formula results and cached display are unverified. "
            "Agent reviews meaning and actual rendering; preserve this immutable snapshot and keep synthesis in adjacent notes.\n\n"
            + "\n".join(self.links)
            + "\n"
        ).encode("utf-8")
