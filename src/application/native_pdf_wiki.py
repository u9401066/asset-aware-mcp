"""Portable PDF page evidence, native source bytes and reviewable page previews."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_pdf_operations import PDF_REVIEW
from src.application.native_wiki_format import NativeWikiContent, canonical_json, digest

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata


class NativePdfWikiContent(NativeWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        *,
        projection: str = "pdf-pages-v1",
    ):
        super().__init__(identity, contract, metadata, projection=projection)
        self.projection = projection
        self.source_name = self.prefix + ".pdf"

    def add_page(self, record: dict[str, Any], png: bytes) -> None:
        locator = record["locator"]
        stem = f"{self.prefix}-page-{digest(canonical_json(locator))}"
        preview = stem + ".png"
        self.add_file(preview, png)
        presentation = render_citation(
            self.contract,
            self.metadata,
            source_id=self.identity["asset_id"],
            asset_id=self.identity["asset_id"],
            title=self.identity["name"],
            locator={**locator, "page": locator["page_index"] + 1},
        )
        record = {
            **record,
            "note": stem + ".md",
            "preview_attachment": preview,
            "preview_sha256": digest(png),
            "citation_presentation": presentation,
        }
        line = canonical_json(record) + b"\n"
        self.reserve(len(line))
        self.records.append(line)
        title = citation_markdown(
            f"Page {locator['page_index'] + 1} — {record['label']}"
        )
        self.links.append(f"- [[{stem}|{title}]]")
        self.add_file(stem + ".md", self._page_note(record, title))

    def _page_note(self, record: dict[str, Any], title: str) -> bytes:
        text = "\n\n".join(block[4] for block in record["text_blocks"])
        evidence = record["evidence"]
        presentation = record["citation_presentation"]
        return (
            f"# {title}\n\n![Page preview]({record['preview_attachment']})\n\n"
            f"{citation_markdown(text)}\n\nCitation: {citation_markdown(presentation['inline'])}\n\n"
            f"Reference: {citation_markdown(presentation['reference'])}\n\n"
            f"Source asset: `{evidence['asset_id']}`\n\nRevision: `{evidence['revision']}`\n\n"
            f"Page representation SHA-256: `{evidence['value_sha256']}`\n\n"
            f"[Original PDF]({self.source_name}) · [Full evidence](records.jsonl)\n\n"
            "Native text extraction is not OCR. Original PDF bytes retain streams and unparsed features. "
            "Preview pixels and graph checks do not establish semantic accuracy, accessibility or viewer fidelity.\n\n"
            f"[[{self.index_name[:-3]}|Source index]]\n"
        ).encode()

    def record_counts(self) -> dict[str, int]:
        return {"cell_count": 0, "page_count": len(self.records)}

    def manifest_details(self) -> dict[str, Any]:
        return {
            **self.record_counts(),
            "representation": "pdf_pages",
            "projection": self.projection,
            "extraction_scope": "native text blocks, bounded PDF object graphs, previews and exact source bytes; no OCR",
        }

    def review_required(self) -> list[str]:
        return list(PDF_REVIEW)

    def _index(self) -> bytes:
        return (
            f"# {citation_markdown(self.identity['name'])}\n\n"
            f"Source asset: `{self.identity['asset_id']}`\n\nRevision: `{self.identity['revision']}`\n\n"
            f"[Original PDF]({self.source_name}) · [Evidence records](records.jsonl)\n\n"
            f"{len(self.records)} pages with native text, object graphs and rendered previews. "
            "The exact PDF retains unparsed content. Agents review meaning, full resolution layout, "
            "forms and accessibility. Keep synthesis in adjacent curated notes; this snapshot is immutable.\n\n"
            + "\n".join(self.links)
            + "\n"
        ).encode("utf-8")
