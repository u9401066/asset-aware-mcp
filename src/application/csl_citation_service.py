"""Render whole citation documents and publish immutable evidence-backed wiki notes."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown
from src.application.csl_markup import citation_preview, safe_csl_html
from src.domain.csl_citations import MAX_CSL_OUTPUT_BYTES, CslDocument
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_wiki import MAX_WIKI_BYTES

if TYPE_CHECKING:
    from src.application.native_evidence_service import NativeEvidenceService
    from src.domain.csl_citations import CslProcessor
    from src.domain.native_wiki import NativeWikiPublisher


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def citation_page(
    value: Any, offset: int, limit: int, expected: str | None
) -> dict[str, Any]:
    if (
        type(offset) is not int
        or offset < 0
        or type(limit) is not int
        or not 1 <= limit <= 8000
    ):
        raise ValueError(
            "Citation paging requires nonnegative text_offset and text_limit 1..8000"
        )
    data = canonical(value)
    if len(data) > MAX_CSL_OUTPUT_BYTES:
        raise ValueError("Citation document result exceeds output byte limit")
    sha = digest(data)
    if expected is not None and expected != sha:
        raise ValueError("Citation document changed; restart reading at its new hash")
    text = data.decode("utf-8")
    start = min(offset, len(text))
    end = min(start + limit, len(text))
    while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
        end = start + (end - start) // 2
    return {
        "success": True,
        "schema_version": "csl-citation-page-v1",
        "text_sha256": sha,
        "text_length": len(text),
        "text_excerpt": text[start:end],
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "representation_complete": start == 0 and end == len(text),
        "serialization": "canonical-json; UTF-8 SHA-256",
    }


class CslCitationService:
    def __init__(
        self,
        processor: CslProcessor,
        evidence: NativeEvidenceService,
        publisher: NativeWikiPublisher,
    ):
        self.processor, self.evidence, self.publisher = processor, evidence, publisher

    def contract(self) -> dict[str, Any]:
        return {
            "schema_version": "csl-citation-contract-v1",
            **self.processor.capabilities(),
            "document_schema": CslDocument.model_json_schema(),
            "operations": ["csl_contract", "render_citations"],
            "source_reference_schema": "document native contract for_op=verify; use complete references",
            "review_required": [
                "bibliographic_metadata",
                "semantic_support",
                "printed_locator_correspondence",
                "rendered_typography",
            ],
        }

    def render(
        self,
        document: CslDocument,
        wiki_root: str = "",
        expected_hash: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        sources: dict[str, Any] = {}
        attachments: dict[str, bytes] = {}
        for key, value in document.sources.items():
            reference = NativeDocumentRequest.model_validate(
                {"op": "verify", "reference": value}
            ).reference
            if reference is None:
                raise ValueError("Citation source requires a complete native reference")
            verification = self.evidence.verify(reference)
            if not verification.get("valid"):
                raise ValueError(
                    "Citation source reference failed verification: " + key
                )
            record = {
                "reference": reference.model_dump(mode="json"),
                "verification": {
                    "valid": True,
                    "verification_scope": verification["verification_scope"],
                    "checks": verification.get("checks", {}),
                },
                "semantic_support": "not_checked",
            }
            asset = self.evidence.repository.load(reference.asset_id)
            data = self.evidence.repository.read(reference.asset_id, reference.revision)
            if digest(data) != reference.revision:
                raise ValueError("Citation attachment revision mismatch")
            extension = (
                asset.format
                if asset.format
                in {
                    "pdf",
                    "docx",
                    "pptx",
                    "xlsx",
                    "xlsm",
                    "csv",
                    "tsv",
                    "png",
                    "jpeg",
                    "jpg",
                }
                else "bin"
            )
            name = f"source-{reference.revision}.{extension}"
            if wiki_root:
                attachments[name] = data
            if (
                sum(map(len, attachments.values()))
                > MAX_WIKI_BYTES - MAX_CSL_OUTPUT_BYTES
            ):
                raise ValueError("Citation source attachments exceed wiki byte limit")
            record["attachment"] = {
                "name": name,
                "sha256": digest(data),
                "size_bytes": len(data),
            }
            sources[key] = record
        output = self.processor.render(document)
        citations = []
        for index, cluster in enumerate(document.clusters):
            citations.append(
                {
                    "id": cluster.id,
                    "note_index": cluster.note_index,
                    "text": output["text"]["citations"][index],
                    "html": safe_csl_html(output["html"]["citations"][index]),
                    "cites": [cite.model_dump(mode="json") for cite in cluster.cites],
                }
            )
        bibliography = [
            {
                "item_ids": ids,
                "text": output["text"]["bibliography"][i],
                "html": safe_csl_html(output["html"]["bibliography"][i]),
            }
            for i, ids in enumerate(output["text"]["entry_ids"])
        ]
        result = {
            "schema_version": "csl-citation-result-v1",
            "document": document.model_dump(mode="json"),
            "document_sha256": digest(canonical(document.model_dump(mode="json"))),
            "citations": citations,
            "bibliography": bibliography,
            "bibliography_options": output["html"]["bibliography_options"],
            "resources": output["resources"],
            "warnings": output["warnings"],
            "sources": sources,
            "missing_metadata": [
                {
                    "id": item["id"],
                    "fields": [
                        field
                        for field in ("author", "issued", "title")
                        if not item.get(field)
                    ],
                }
                for item in document.items
                if any(not item.get(field) for field in ("author", "issued", "title"))
            ],
            "metadata_origin": "caller_supplied; no metadata was inferred",
            "printed_locator_scope": "caller-supplied display; correspondence to native evidence is not verified",
            "review_required": [
                "bibliographic_metadata",
                "semantic_support",
                "printed_locator_correspondence",
                "rendered_typography",
            ],
            "processor_attribution": "Citations and bibliography rendered by citeproc-js, Frank Bennett; official CSL styles/locales.",
        }
        if len(canonical(result)) > MAX_CSL_OUTPUT_BYTES:
            raise ValueError("Citation result exceeds output byte limit")
        if expected_hash is not None and digest(canonical(result)) != expected_hash:
            raise ValueError("Citation document changed; no wiki was published")
        publication = (
            self._publish(wiki_root, result, attachments) if wiki_root else None
        )
        return result, publication

    def _publish(
        self, wiki_root: str, result: dict[str, Any], attachments: dict[str, bytes]
    ) -> dict[str, Any]:
        data = canonical(result)
        snapshot = digest(data)
        prefix = "csl-" + snapshot
        files = {**attachments, "citations.json": data}
        files["references.html"] = citation_preview(
            result["citations"], result["bibliography"], result["bibliography_options"]
        )
        links = []
        for cluster in result["citations"]:
            stem = prefix + "-" + digest(cluster["id"].encode("utf-8"))
            keys = sorted(
                {key for cite in cluster["cites"] for key in cite["source_keys"]}
            )
            source_links = [
                f"- [Source {citation_markdown(key)}]({result['sources'][key]['attachment']['name']})"
                for key in keys
            ]
            note = (
                f"# {citation_markdown(cluster['id'])}\n\n<div>{cluster['html']}</div>\n\n"
                + "\n".join(source_links)
            )
            note += f"\n\nComplete canonical references and printed locators: [citations.json](citations.json).\n\n[[{prefix}-index|Citation index]]\n"
            files[stem + ".md"] = note.encode("utf-8")
            links.append(f"- [[{stem}|{citation_markdown(cluster['id'])}]]")
        bibliography = "\n".join(entry["html"] for entry in result["bibliography"])
        index = (
            "# Citation document\n\n[Typography preview](references.html) · [Complete evidence](citations.json)\n\n"
            + "\n".join(links)
            + "\n\n## Bibliography\n\n"
            + bibliography
        )
        index += (
            "\n\n"
            + result["processor_attribution"]
            + "\n\nCanonical sources are verified at immutable revisions. Bibliographic metadata, printed locator correspondence, semantic support and rendered typography require Agent review.\n"
        )
        files[prefix + "-index.md"] = index.encode("utf-8")
        manifest = {
            "schema_version": "csl-citation-wiki-v1",
            "snapshot_id": snapshot,
            "index_note": prefix + "-index.md",
            "citation_result_sha256": digest(data),
            "files": {
                name: {"sha256": digest(value), "size_bytes": len(value)}
                for name, value in sorted(files.items())
            },
        }
        files["manifest.json"] = canonical(manifest)
        return self.publisher.publish(wiki_root, snapshot, files, source_path=None)
