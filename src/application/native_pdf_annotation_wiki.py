"""Portable annotation notes alongside exact source PDF and actual page previews."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_pdf_wiki import NativePdfWikiContent
from src.application.native_wiki_format import canonical_json, digest
from src.domain.native_pdf_annotations import ANNOTATION_REVIEW

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.domain.citation_format import CitationFormatContract, CitationMetadata


class NativePdfAnnotationWikiContent(NativePdfWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        catalog: dict[str, Any],
        *,
        projection: str = "pdf-annotations-v1",
    ):
        super().__init__(identity, contract, metadata, projection=projection)
        self.annotations_catalog = catalog
        self.annotation_links: list[str] = []
        self.page_notes: dict[int, str] = {}

    def add_page(self, record: dict[str, Any], png: bytes) -> None:
        super().add_page(record, png)
        self.page_notes[record["locator"]["page_index"]] = (
            self.prefix + "-page-" + digest(canonical_json(record["locator"]))
        )

    def add_annotations(self, records: Iterable[dict[str, Any]]) -> None:
        self.add_file(
            "annotation-catalog.json", canonical_json(self.annotations_catalog) + b"\n"
        )
        lines = []
        for record in records:
            locator = record["locator"]
            page_index = locator["page"]["page_index"]
            name = self.prefix + "-annotation-" + digest(canonical_json(locator))
            page_name = self.page_notes[page_index]
            presentation = render_citation(
                self.contract,
                self.metadata,
                source_id=self.identity["asset_id"],
                asset_id=self.identity["asset_id"],
                title=self.identity["name"],
                locator={
                    "page": page_index + 1,
                    "annotation_index": locator["annotation_index"],
                    "annotation_object": locator["object_id"],
                    "generation": locator["generation"],
                },
            )
            title = citation_markdown(
                f"Page {page_index + 1} annotation {locator['annotation_index']} — {record['subtype']}"
            )
            line = (
                canonical_json(
                    {
                        **record,
                        "note": name + ".md",
                        "preview_attachment": page_name + ".png",
                        "citation_presentation": presentation,
                    }
                )
                + b"\n"
            )
            self.reserve(len(line))
            lines.append(line)
            self.annotation_links.append(f"- [[{name}|{title}]]")
            evidence = record["evidence"]
            text = (
                f"# {title}\n\n{citation_markdown(record['contents'] or '')}\n\n"
                f"Annotation author: {citation_markdown(record['author'] or 'unspecified')}\n\n"
                f"Citation: {citation_markdown(presentation['inline'])}\n\n"
                f"Reference: {citation_markdown(presentation['reference'])}\n\n"
                f"Source asset: `{evidence['asset_id']}`\n\nRevision: `{evidence['revision']}`\n\n"
                f"Annotation representation SHA-256: `{evidence['value_sha256']}`\n\n"
                f"![Actual page preview]({page_name}.png)\n\n"
                f"[[{page_name}|Source page]] · [Original PDF]({self.source_name}) · "
                "[Complete annotation records](annotations.jsonl) · [Native annotation catalog](annotation-catalog.json)\n\n"
                "Annotation text is an authored comment or FreeText appearance, not a transcription of the underlying highlighted document. "
                "Native verification does not establish semantic support. Popup, reply and viewer behavior require Agent review.\n\n"
                f"[[{self.index_name[:-3]}|Source index]]\n"
            )
            self.add_file(name + ".md", text.encode())
        self.files["annotations.jsonl"] = b"".join(lines)

    def record_counts(self) -> dict[str, int]:
        return {
            **super().record_counts(),
            "annotation_count": len(self.annotation_links),
        }

    def manifest_details(self) -> dict[str, Any]:
        return {
            **super().manifest_details(),
            "annotation_records": "annotations.jsonl",
            "annotation_catalog": "annotation-catalog.json",
            "extraction_scope": "Native page records/previews and complete annotation records, raw native object graphs, comment text and exact PDF bytes. Annotation text is distinct from underlying page text; no OCR.",
        }

    def review_required(self) -> list[str]:
        return list(dict.fromkeys([*super().review_required(), *ANNOTATION_REVIEW]))

    def _index(self) -> bytes:
        return (
            super()._index()
            + (
                "\n## Annotations\n\n" + "\n".join(self.annotation_links) + "\n"
            ).encode()
        )
