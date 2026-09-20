"""Complete native stories in a distinct snapshot, leaving legacy Wikis intact."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_docx_wiki import NativeDocxWikiContent
from src.application.native_wiki_format import canonical_json, digest
from src.domain.native_docx_stories import STORY_REVIEW

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata


class NativeDocxStoryWikiContent(NativeDocxWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        catalog: dict[str, Any],
        *,
        projection: str = "docx-stories-v1",
    ):
        super().__init__(identity, contract, metadata, projection=projection)
        self.catalog = catalog
        self.story_links: list[str] = []

    def add_stories(self, records: list[dict[str, Any]]) -> None:
        lines = []
        self.add_file("story-catalog.json", canonical_json(self.catalog) + b"\n")
        for record in records:
            locator = record["locator"]
            name = self.prefix + "-story-" + digest(canonical_json(locator))
            part = self.parts[locator["part"]]["attachment"]
            presentation = render_citation(
                self.contract,
                self.metadata,
                source_id=self.identity["asset_id"],
                asset_id=self.identity["asset_id"],
                title=self.identity["name"],
                locator=locator,
            )
            title = citation_markdown(f"{locator['story_kind']} {locator['part']}")
            result = {
                **record,
                "note": name + ".md",
                "citation_presentation": presentation,
                "source_part_attachment": part,
            }
            lines.append(canonical_json(result) + b"\n")
            self.story_links.append(f"- [[{name}|{title}]]")
            text = (
                f"# {title}\n\n{citation_markdown(record['text'])}\n\n"
                f"Citation: {citation_markdown(presentation['inline'])}\n\n"
                f"Reference: {citation_markdown(presentation['reference'])}\n\n"
                f"[Original DOCX]({self.source_name}) · [Source part]({part}) · "
                "[Full story records](stories.jsonl) · [Section bindings](story-catalog.json)\n\n"
                "Literal native XML text includes field caches and alternate/revision branches. "
                "Review every affected rendered page and shared/disabled definition with the Agent.\n\n"
                f"[[{self.index_name[:-3]}|Source index]]\n"
            )
            self.add_file(name + ".md", text.encode())
        self.add_file("stories.jsonl", b"".join(lines))

    def record_counts(self) -> dict[str, int]:
        return {**super().record_counts(), "story_count": len(self.story_links)}

    def manifest_details(self) -> dict[str, Any]:
        return {
            **super().manifest_details(),
            "story_records": "stories.jsonl",
            "story_catalog": "story-catalog.json",
            "extraction_scope": "Legacy DFM blocks plus complete native header/footer XML and literal text nodes; section definitions are not a rendered page map.",
        }

    def review_required(self) -> list[str]:
        return STORY_REVIEW

    def _index(self) -> bytes:
        return (
            super()._index()
            + (
                "\n## Header/footer stories\n\n" + "\n".join(self.story_links) + "\n"
            ).encode()
        )
