"""Portable note definitions and exact references in an immutable Wiki projection."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_docx_story_wiki import NativeDocxStoryWikiContent
from src.application.native_wiki_format import canonical_json, digest
from src.domain.native_docx_notes import NOTE_REVIEW

if TYPE_CHECKING:
    from collections.abc import Iterable

    from src.domain.citation_format import CitationFormatContract, CitationMetadata


class NativeDocxNoteWikiContent(NativeDocxStoryWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        notes: dict[str, Any],
        stories: dict[str, Any] | None,
    ):
        super().__init__(
            identity,
            contract,
            metadata,
            stories or {"stories": []},
            projection="docx-notes-v1"
            if stories is not None
            else "docx-notes-content-v1",
        )
        self.notes_catalog = notes
        self.has_stories = stories is not None
        self.note_links: list[str] = []

    def add_notes(self, records: Iterable[dict[str, Any]]) -> None:
        lines = []
        self.add_file("note-catalog.json", canonical_json(self.notes_catalog) + b"\n")
        for record in records:
            loc = record["locator"]
            name = self.prefix + "-note-" + digest(canonical_json(loc))
            part = self.parts[loc["part"]]["attachment"]
            presentation = render_citation(
                self.contract,
                self.metadata,
                source_id=self.identity["asset_id"],
                asset_id=self.identity["asset_id"],
                title=self.identity["name"],
                locator=loc,
            )
            title = citation_markdown(
                f"{loc['note_kind']} native ID {loc['note_id']} ({record['note_type']})"
            )
            line = (
                canonical_json(
                    {
                        **record,
                        "note": name + ".md",
                        "citation_presentation": presentation,
                        "source_part_attachment": part,
                    }
                )
                + b"\n"
            )
            self.reserve(len(line))
            lines.append(line)
            self.note_links.append(f"- [[{name}|{title}]]")
            text = (
                f"# {title}\n\n{citation_markdown(record['text'])}\n\n"
                f"Citation: {citation_markdown(presentation['inline'])}\n\n"
                f"Reference: {citation_markdown(presentation['reference'])}\n\n"
                f"[Original DOCX]({self.source_name}) · [Source part]({part}) · "
                "[Complete note records](notes.jsonl) · [Native references](note-catalog.json)\n\n"
                "Native IDs are distinct from displayed numbering. Literal XML includes fields and revision branches; special definitions are layout content. "
                "The Agent reviews meaning, actual note placement, numbering and custom marks.\n\n"
                f"[[{self.index_name[:-3]}|Source index]]\n"
            )
            self.add_file(name + ".md", text.encode())
        self.files["notes.jsonl"] = b"".join(lines)

    def record_counts(self) -> dict[str, int]:
        return {**super().record_counts(), "note_count": len(self.note_links)}

    def manifest_details(self) -> dict[str, Any]:
        return {
            **super().manifest_details(),
            "note_records": "notes.jsonl",
            "note_catalog": "note-catalog.json",
            "extraction_scope": "Legacy DFM blocks and complete native header/footer/footnote/endnote records with literal references and special note roles. Native IDs and body paths are not rendered numbers or page locations."
            if self.has_stories
            else "Legacy DFM blocks and complete native footnote/endnote records with literal references and special roles. The header/footer story adapter is absent. Native IDs and body paths are not rendered numbers or page locations.",
        }

    def review_required(self) -> list[str]:
        return list(dict.fromkeys([*super().review_required(), *NOTE_REVIEW]))

    def _index(self) -> bytes:
        return (
            super()._index()
            + (
                "\n## Footnotes and endnotes\n\n" + "\n".join(self.note_links) + "\n"
            ).encode()
        )
