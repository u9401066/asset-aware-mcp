"""Presentation shape evidence with exact package attachments in immutable wikis."""

from __future__ import annotations

import posixpath
from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_pptx_operations import REVIEW_REQUIRED
from src.application.native_wiki_format import NativeWikiContent, canonical_json, digest
from src.domain.native_wiki import MAX_WIKI_CELLS, MAX_WIKI_PARTS

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata

PROJECTION = "pptx-shapes-v1"
PART_SUFFIXES = {
    ".xml",
    ".rels",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".emf",
    ".wmf",
    ".xlsx",
    ".bin",
}


class NativePptxWikiContent(NativeWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
    ):
        super().__init__(identity, contract, metadata, projection=PROJECTION)
        self.source_name = self.prefix + ".pptx"
        self.parts: dict[str, dict[str, Any]] = {}

    def add_parts(self, parts: dict[str, bytes]) -> None:
        if len(parts) > MAX_WIKI_PARTS:
            raise ValueError("PPTX wiki exceeds the package-part limit")
        for part, data in sorted(parts.items()):
            if part.endswith("/"):
                if data:
                    raise ValueError("PPTX directory entry unexpectedly contains bytes")
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

    def add_shape(self, record: dict[str, Any]) -> None:
        if len(self.records) >= MAX_WIKI_CELLS:
            raise ValueError("PPTX wiki exceeds the shape-record limit")
        locator = record["locator"]
        if locator["part"] not in self.parts:
            raise ValueError("PPTX shape references a missing package part")
        stem = f"{self.prefix}-shape-{digest(canonical_json(locator))}"
        title = citation_markdown(
            f"Slide ID {locator['slide_id']} / {locator['region']} / {record['name']} ({locator['shape_id']})"
        )
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
        self.add_file(stem + ".md", self._shape_note(record, title))

    def _shape_note(self, record: dict[str, Any], title: str) -> bytes:
        paragraphs = list(record["paragraphs"])
        for row in record.get("table", {}).get("rows", []):
            for cell in row["cells"]:
                paragraphs.extend(cell["paragraphs"])
        content = "\n\n".join(
            "".join(item["text"] for item in paragraph["items"])
            for paragraph in paragraphs
        )
        evidence = record["evidence"]
        presentation = record["citation_presentation"]
        return (
            f"# {title}\n\n{citation_markdown(content)}\n\n"
            f"Citation: {citation_markdown(presentation['inline'])}\n\n"
            f"Reference: {citation_markdown(presentation['reference'])}\n\n"
            f"Source asset: `{evidence['asset_id']}`\n\nRevision: `{evidence['revision']}`\n\n"
            f"Shape representation SHA-256: `{evidence['value_sha256']}`\n\n"
            f"[Source package part]({record['source_part_attachment']}) · [Original PPTX]({self.source_name}) · "
            "[Full representation and native reference](records.jsonl)\n\n"
            "Shape XML, explicit runs and local transforms are preserved. Inherited formatting, "
            "visual bounds, overflow and semantic accuracy require agent review.\n\n"
            f"[[{self.index_name[:-3]}|Source index]]\n"
        ).encode()

    def record_counts(self) -> dict[str, int]:
        return {
            "cell_count": 0,
            "shape_count": len(self.records),
            "part_count": len(self.parts),
        }

    def manifest_details(self) -> dict[str, Any]:
        return {
            **self.record_counts(),
            "representation": "pptx_shapes",
            "projection": PROJECTION,
            "part_attachments": self.parts,
            "extraction_scope": "Direct slide/notes shape trees; original/package parts retain unparsed and inherited features",
        }

    def review_required(self) -> list[str]:
        return list(REVIEW_REQUIRED)

    def _index(self) -> bytes:
        parts = [
            f"- [{citation_markdown(part)}]({info['attachment']})"
            for part, info in self.parts.items()
        ]
        return (
            f"# {citation_markdown(self.identity['name'])}\n\nSource asset: `{self.identity['asset_id']}`\n\n"
            f"Revision: `{self.identity['revision']}`\n\n"
            f"[Original PPTX]({self.source_name}) · [Evidence records](records.jsonl)\n\n"
            f"{len(self.records)} parsed shapes and {len(self.parts)} original package parts. "
            "Relationships, media, layouts, masters, themes and unparsed features remain in the attachments. "
            "The agent reviews semantic accuracy, inherited formatting, overflow and rendered layout. "
            "Keep synthesis in adjacent curated notes; this snapshot is immutable.\n\n## Shapes\n\n"
            + "\n".join(self.links)
            + "\n\n## Package parts\n\n"
            + "\n".join(parts)
            + "\n"
        ).encode("utf-8")
