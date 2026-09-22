"""Field evidence notes retain native identities, every widget page and full receipts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_pdf_annotation_wiki import NativePdfAnnotationWikiContent
from src.application.native_wiki_format import canonical_json, digest
from src.domain.native_pdf_fields import FIELD_REVIEW

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata


class NativePdfFieldWikiContent(NativePdfAnnotationWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        annotations: dict[str, Any],
        fields: dict[str, Any],
        receipt: dict[str, Any] | None,
    ):
        super().__init__(
            identity,
            contract,
            metadata,
            annotations,
            projection="pdf-fields-v1:" + digest(canonical_json(receipt)),
        )
        self.field_catalog = fields
        self.field_links: list[str] = []
        self.add_file("field-catalog.json", canonical_json(fields) + b"\n")
        self.add_file("operation-result.json", canonical_json(receipt) + b"\n")

    def add_fields(self, records: list[dict[str, Any]]) -> None:
        names = {
            tuple(record["locator"]["field_path"]): self.prefix
            + "-field-"
            + digest(canonical_json(record["locator"]))
            for record in records
        }
        lines = []
        for record in records:
            locator = record["locator"]
            name = names[tuple(locator["field_path"])]
            title = citation_markdown(record["qualified_name"] or "Unnamed PDF field")
            physical = (
                "PDF field path "
                + "/".join(str(i) for i in locator["field_path"])
                + f" (zero-based), object {locator['object_id']} {locator['generation']}"
                + (" (direct dictionary)" if locator["object_id"] == 0 else "")
            )
            presentation = render_citation(
                self.contract,
                self.metadata,
                source_id=self.identity["asset_id"],
                asset_id=self.identity["asset_id"],
                title=self.identity["name"],
                locator={**locator, "section_hierarchy": [physical]},
            )
            pages = sorted(
                {
                    occurrence["locator"]["page"]["page_index"]
                    for widget in record["widgets"]
                    for occurrence in widget["page_occurrences"]
                }
            )
            page_links = [
                {
                    "page_index": index,
                    "note": self.page_notes[index] + ".md",
                    "preview_attachment": self.page_notes[index] + ".png",
                }
                for index in pages
            ]
            children = [
                names[tuple(child["field_path"])] for child in record["child_fields"]
            ]
            line = (
                canonical_json(
                    {
                        **record,
                        "note": name + ".md",
                        "page_links": page_links,
                        "child_field_notes": [child + ".md" for child in children],
                        "citation_presentation": presentation,
                    }
                )
                + b"\n"
            )
            self.reserve(len(line))
            lines.append(line)
            self.field_links.append(f"- [[{name}|{title}]] — {physical}")
            value = record["inherited_entries"].get("/V", {})
            value_text = value.get("text")
            display = (
                "Value text: " + citation_markdown(value_text)
                if isinstance(value_text, str)
                else "Native value and selection indices are retained in the complete field record."
            )
            views = (
                "\n\n".join(
                    f"[[{self.page_notes[index]}|Page {index + 1}]]\n\n![Actual page {index + 1}]({self.page_notes[index]}.png)"
                    for index in pages
                )
                or "No page Widget occurrence is owned by this field record; inspect its child fields and native issues."
            )
            child_links = "\n".join(f"- [[{child}|Child field]]" for child in children)
            evidence = record["evidence"]
            field_type = citation_markdown(record["field_type"] or "unspecified")
            text = (
                f"# {title}\n\n{physical}\n\nKind: {record['kind']}; native type: {field_type}.\n\n"
                f"{display}\n\nCitation: {citation_markdown(presentation['inline'])}\n\n"
                f"Reference: {citation_markdown(presentation['reference'])}\n\n"
                f"Source asset: `{evidence['asset_id']}`\n\nRevision: `{evidence['revision']}`\n\n"
                f"Field representation SHA-256: `{evidence['value_sha256']}`\n\n{views}\n\n{child_links}\n\n"
                f"[Original PDF]({self.source_name}) · [Complete fields](fields.jsonl) · [Field catalog](field-catalog.json) · [Operation receipt](operation-result.json)\n\n"
                "Names are labels, not identity. Values and native appearance streams are separate evidence; page images and viewer behavior require Agent review. Scripts are preserved without execution.\n\n"
                f"[[{self.index_name[:-3]}|Source index]]\n"
            )
            self.add_file(name + ".md", text.encode("utf-8"))
        self.files["fields.jsonl"] = b"".join(lines)

    def record_counts(self) -> dict[str, int]:
        return {**super().record_counts(), "field_count": len(self.field_links)}

    def manifest_details(self) -> dict[str, Any]:
        return {
            **super().manifest_details(),
            "field_records": "fields.jsonl",
            "field_catalog": "field-catalog.json",
            "operation_result_file": "operation-result.json",
            "extraction_scope": "Native pages/previews, annotation records and complete field-tree records with all owned Widget occurrences, hidden values, original PDF bytes and complete immutable operation receipt. No semantic or viewer-fidelity verdict.",
        }

    def review_required(self) -> list[str]:
        return list(dict.fromkeys([*super().review_required(), *FIELD_REVIEW]))

    def _index(self) -> bytes:
        return super()._index() + (
            "\n## Form fields\n\n[Complete fields](fields.jsonl) · [Native catalog](field-catalog.json) · [Operation receipt](operation-result.json)\n\n"
            + "\n".join(self.field_links)
            + "\n"
        ).encode("utf-8")
