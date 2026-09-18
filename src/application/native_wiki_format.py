"""Readable, revision-pinned native evidence notes and bounded portable artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.domain.native_wiki import MAX_WIKI_BYTES, NATIVE_WIKI_VERSION

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class NativeWikiContent:
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
    ):
        self.identity = identity
        self.contract = contract
        self.metadata = metadata
        self.snapshot_id = digest(
            canonical_json({k: identity[k] for k in ("asset_id", "revision")})
        )
        self.prefix = f"native-{self.snapshot_id}"
        self.index_name = f"{self.prefix}-index.md"
        self.source_name = self.prefix + (
            "." + identity["format"]
            if identity["format"] in {"xlsx", "xlsm"}
            else ".bin"
        )
        self.files: dict[str, bytes] = {}
        self.size = 0
        self.records: list[bytes] = []
        self.links: list[str] = []

    def add_file(self, name: str, data: bytes) -> None:
        if name in self.files:
            raise ValueError("Duplicate native wiki artifact identity")
        self.reserve(len(data))
        self.files[name] = data

    def reserve(self, size: int) -> None:
        self.size += size
        if self.size > MAX_WIKI_BYTES:
            raise ValueError("Native wiki exceeds the output byte limit")

    def add_cell(self, cell: dict[str, Any]) -> None:
        evidence = cell["evidence"]
        key = digest(canonical_json(evidence["locator"]))
        stem = f"{self.prefix}-cell-{key}"
        title = citation_markdown(f"{cell['sheet']}!{cell['cell']}")
        presentation = render_citation(
            self.contract,
            self.metadata,
            source_id=self.identity["asset_id"],
            asset_id=self.identity["asset_id"],
            title=self.identity["name"],
            locator={"sheet": cell["sheet"], "cell": cell["cell"]},
        )
        record = {**cell, "note": stem + ".md", "citation_presentation": presentation}
        line = canonical_json(record) + b"\n"
        self.reserve(len(line))
        self.records.append(line)
        self.links.append(f"- [[{stem}|{title}]]")
        self.add_file(stem + ".md", self._cell_note(cell, title, presentation))

    def _cell_note(
        self, cell: dict[str, Any], title: str, presentation: dict[str, str]
    ) -> bytes:
        evidence = cell["evidence"]
        stored = cell.get("raw_value", json.dumps(cell["value"], ensure_ascii=False))
        value = citation_markdown(stored)
        text = (
            f"# {title}\n\n"
            f"Stored {citation_markdown(cell['kind'])} representation: {value}\n\n"
            f"Citation: {citation_markdown(presentation['inline'])}\n\n"
            f"Reference: {citation_markdown(presentation['reference'])}\n\n"
            f"Source asset: `{evidence['asset_id']}`\n\n"
            f"Revision: `{evidence['revision']}`\n\n"
            f"Cell representation SHA-256: `{evidence['value_sha256']}`\n\n"
            "The complete native-cell-ref-v1 reference and representation are in "
            "[records.jsonl](records.jsonl). Integrity identifies stored evidence; "
            "semantic support, rendered layout and formula results require agent review.\n\n"
            f"[[{self.index_name[:-3]}|Source index]] · "
            f"[Original file]({self.source_name})\n"
        )
        return text.encode("utf-8")

    def finish(self, data: bytes) -> dict[str, bytes]:
        self.add_file(self.source_name, data)
        # Record bytes were counted while collecting them, before concatenation.
        self.files["records.jsonl"] = b"".join(self.records)
        self.add_file(self.index_name, self._index())
        manifest = {
            "schema_version": NATIVE_WIKI_VERSION,
            "snapshot_id": self.snapshot_id,
            **self.identity,
            "source_attachment": self.source_name,
            "index_note": self.index_name,
            "cell_count": len(self.records),
            "representation": "stored_cells"
            if self.identity["format"] in {"xlsx", "xlsm"}
            else "opaque_binary",
            "citation_contract": self.contract.model_dump(mode="json"),
            "citation_metadata": self.metadata.model_dump(mode="json"),
            "metadata_origin": "caller_supplied; title defaults to source name",
            "files": {
                name: {"sha256": digest(value), "size_bytes": len(value)}
                for name, value in sorted(self.files.items())
            },
        }
        self.add_file("manifest.json", canonical_json(manifest) + b"\n")
        return self.files

    def _index(self) -> bytes:
        title = citation_markdown(self.identity["name"])
        coverage = (
            f"{len(self.records)} stored cells (including stored blanks); unstored "
            "blank coordinates and chart/dialog sheets are not exported."
            if self.identity["format"] in {"xlsx", "xlsm"}
            else "Opaque source attachment; no native content interpretation is available."
        )
        text = (
            f"# {title}\n\n"
            f"Source asset: `{self.identity['asset_id']}`\n\n"
            f"Revision: `{self.identity['revision']}`\n\n"
            f"[Original file]({self.source_name}) · [Evidence records](records.jsonl)\n\n"
            f"{coverage}\n\n"
            "Formula caches are unverified. Semantic and rendered review belong to "
            "the agent. Keep synthesis in adjacent curated notes; this snapshot is "
            "immutable and exports never overwrite it.\n\n"
            + "\n".join(self.links)
            + "\n"
        )
        return text.encode("utf-8")
