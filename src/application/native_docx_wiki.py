"""DOCX block notes and exact package attachments in a distinct immutable projection."""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_wiki_format import NativeWikiContent, canonical_json, digest
from src.domain.native_wiki import MAX_WIKI_CELLS, MAX_WIKI_PARTS

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata

PROJECTION = "docx-blocks-v1"
PART_SUFFIXES = {
    ".xml",
    ".rels",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
    ".svg",
    ".emf",
    ".wmf",
    ".xlsx",
    ".bin",
}


class NativeDocxWikiContent(NativeWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        *,
        projection: str = PROJECTION,
    ):
        super().__init__(identity, contract, metadata, projection=projection)
        self.docx_projection = projection
        self.source_name = self.prefix + ".docx"
        self.parts: dict[str, dict[str, Any]] = {}

    def add_parts(self, parts: dict[str, bytes]) -> None:
        if len(parts) > MAX_WIKI_PARTS:
            raise ValueError("DOCX wiki exceeds the package-part limit")
        for part, data in sorted(parts.items()):
            if part.endswith("/"):
                if data:
                    raise ValueError("DOCX directory entry unexpectedly contains bytes")
                continue
            suffix = posixpath.splitext(part)[1].lower()
            suffix = suffix if suffix in PART_SUFFIXES else ".bin"
            name = f"{self.prefix}-part-{digest(part.encode('utf-8'))}{suffix}"
            self.add_file(name, data)
            self.parts[part] = {
                "attachment": name,
                "sha256": digest(data),
                "size_bytes": len(data),
            }

    def add_block(self, record: dict[str, Any]) -> None:
        if len(self.records) >= MAX_WIKI_CELLS:
            raise ValueError("DOCX wiki exceeds the block-record limit")
        locator = record["locator"]
        if locator["part"] not in self.parts:
            raise ValueError("DOCX block references a missing package part")
        stem = f"{self.prefix}-block-{digest(canonical_json(locator))}"
        title = citation_markdown(f"{record['kind']} {record['block_id']}")
        presentation = render_citation(
            self.contract,
            self.metadata,
            source_id=self.identity["asset_id"],
            asset_id=self.identity["asset_id"],
            title=self.identity["name"],
            locator=locator,
        )
        record = {
            **record,
            "note": stem + ".md",
            "citation_presentation": presentation,
            "source_part_attachment": self.parts[locator["part"]]["attachment"],
        }
        line = canonical_json(record) + b"\n"
        self.reserve(len(line))
        self.records.append(line)
        self.links.append(f"- [[{stem}|{title}]]")
        self.add_file(stem + ".md", self._block_note(record, title, presentation))

    def _block_note(
        self, record: dict[str, Any], title: str, presentation: dict[str, str]
    ) -> bytes:
        reference = record["evidence"]
        content = citation_markdown(record["representation"]["text"])
        text = (
            f"# {title}\n\n{content}\n\n"
            f"Citation: {citation_markdown(presentation['inline'])}\n\n"
            f"Reference: {citation_markdown(presentation['reference'])}\n\n"
            f"Source asset: `{reference['asset_id']}`\n\nRevision: `{reference['revision']}`\n\n"
            f"Block representation SHA-256: `{reference['value_sha256']}`\n\n"
            f"[Source package part]({record['source_part_attachment']}) · "
            f"[Original DOCX]({self.source_name}) · [Full representation](records.jsonl)\n\n"
            "The complete native-docx-block-ref-v1 reference is in records.jsonl. "
            "It verifies the parsed representation, not extraction completeness or semantic support. "
            "Review Word layout, fields and revisions with the agent.\n\n"
            f"[[{self.index_name[:-3]}|Source index]]\n"
        )
        return text.encode("utf-8")

    def record_counts(self) -> dict[str, int]:
        return {
            "cell_count": 0,
            "block_count": len(self.records),
            "part_count": len(self.parts),
        }

    def manifest_details(self) -> dict[str, Any]:
        return {
            **self.record_counts(),
            "representation": "docx_blocks",
            "projection": self.docx_projection,
            "part_attachments": self.parts,
            "extraction_scope": "Existing DFM parser blocks; original/package parts retain unparsed features",
        }

    def review_required(self) -> list[str]:
        return ["semantic_accuracy", "rendered_layout", "fields_and_revisions"]

    def _index(self) -> bytes:
        title = citation_markdown(self.identity["name"])
        parts = [
            f"- [{citation_markdown(part)}]({info['attachment']})"
            for part, info in self.parts.items()
        ]
        text = (
            f"# {title}\n\nSource asset: `{self.identity['asset_id']}`\n\n"
            f"Revision: `{self.identity['revision']}`\n\n"
            f"[Original DOCX]({self.source_name}) · [Evidence records](records.jsonl)\n\n"
            f"{len(self.records)} parsed DFM blocks and {len(self.parts)} original package parts. "
            "Unparsed features remain in the source and part attachments. Temporary DFM paths "
            "are representation metadata; use the package-part mapping for actual attachments.\n\n"
            "Semantic accuracy, Word layout, fields and revisions require agent review. "
            "Keep synthesis in adjacent curated notes; this snapshot is immutable.\n\n"
            "## Blocks\n\n"
            + "\n".join(self.links)
            + "\n\n## Package parts\n\n"
            + "\n".join(parts)
            + "\n"
        )
        return text.encode("utf-8")
