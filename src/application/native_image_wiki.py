"""Portable native raster frames, exact sources, complete records and receipts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_image_evidence import IMAGE_REVIEW
from src.application.native_wiki_format import NativeWikiContent, canonical_json, digest
from src.domain.native_image_evidence import image_catalog, image_frame_reference

if TYPE_CHECKING:
    from src.domain.citation_format import CitationFormatContract, CitationMetadata
    from src.domain.native_image import ImageColorPolicy


class NativeImageWikiContent(NativeWikiContent):
    def __init__(
        self,
        identity: dict[str, str],
        contract: CitationFormatContract,
        metadata: CitationMetadata,
        catalog: dict[str, Any],
        operation: dict[str, Any] | None,
        color_policy: ImageColorPolicy,
    ):
        identity = {
            **identity,
            "image_catalog_sha256": catalog["catalog_sha256"],
            "image_operation_sha256": digest(canonical_json(operation)),
            "image_color_policy": color_policy,
        }
        super().__init__(identity, contract, metadata, projection="image-frames-v1")
        self.source_name = self.prefix + "." + identity["format"]
        self.catalog = catalog
        self.operation = operation
        self.color_policy = color_policy

    def add_frames(self, data: bytes, frames: list[dict[str, Any]]) -> None:
        records = [frame["record"] for frame in frames]
        if image_catalog(data, records) != self.catalog:
            raise ValueError("Image decomposition changed its pinned frame catalog")
        self.add_file("image-catalog.json", canonical_json(self.catalog) + b"\n")
        self.add_file("image-operation.json", canonical_json(self.operation) + b"\n")
        for item in frames:
            raw = item["record"]
            reference = image_frame_reference(
                raw, self.identity["asset_id"], self.identity["revision"]
            )
            stem = f"{self.prefix}-frame-{reference.locator.frame_index}"
            title = f"Frame index {reference.locator.frame_index} (zero-based)"
            presentation = render_citation(
                self.contract,
                self.metadata,
                source_id=reference.asset_id,
                asset_id=reference.asset_id,
                title=self.identity["name"],
                locator=reference.locator.model_dump(),
            )
            record = {
                **raw,
                "evidence": reference.model_dump(mode="json"),
                "note": stem + ".md",
                "preview_attachment": stem + ".png",
                "preview_sha256": digest(item["png"]),
                "rendering": item["rendering"],
                "citation_presentation": presentation,
            }
            line = canonical_json(record) + b"\n"
            self.reserve(len(line))
            self.records.append(line)
            self.add_file(stem + ".png", item["png"])
            self.add_file(
                stem + ".md",
                (
                    f"# {title}\n\n![Frame preview]({stem}.png)\n\n"
                    f"Role: {raw['frame_role']}; displayed pixels: {raw['displayed_size_px']}; duration ms: {raw['duration_ms']}.\n\n"
                    f"Citation: {citation_markdown(presentation['inline'])}\n\nReference: {citation_markdown(presentation['reference'])}\n\n"
                    f"Source: `{reference.asset_id}`\n\nRevision: `{reference.revision}`\n\nFrame representation: `{reference.value_sha256}`\n\n"
                    f"[Original raster]({self.source_name}) · [Complete frame records](records.jsonl) · [Catalog](image-catalog.json)\n\n"
                    "Preview is RGBA8, not OCR or proof of source precision. Original bytes retain unmodeled layers and private fields. Agent reviews meaning, color, metadata and animation behavior.\n\n"
                    f"[[{self.index_name[:-3]}|Source index]]\n"
                ).encode(),
            )
            self.links.append(f"- [[{stem}|{title}]]")

    def record_counts(self) -> dict[str, int]:
        return {"cell_count": 0, "frame_count": len(self.records)}

    def manifest_details(self) -> dict[str, Any]:
        return {
            **self.record_counts(),
            "representation": "raster_frames",
            "projection": "image-frames-v1",
            "image_catalog": "image-catalog.json",
            "image_operation": "image-operation.json",
            "extraction_scope": "Complete main decoder frame sequence, typed metadata, source-bound previews and exact file bytes; not OCR or every layer/private field",
        }

    def review_required(self) -> list[str]:
        return list(IMAGE_REVIEW)

    def _index(self) -> bytes:
        return (
            f"# {citation_markdown(self.identity['name'])}\n\n"
            f"Source: `{self.identity['asset_id']}`\n\nRevision: `{self.identity['revision']}`\n\n"
            f"[Original raster]({self.source_name}) · [Complete frame records](records.jsonl) · [Operation receipt](image-operation.json)\n\n"
            f"{len(self.records)} oriented frames with explicit preview color/precision. Agent reviews actual images and meaning. Keep curated synthesis in adjacent notes; this snapshot is immutable.\n\n"
            + "\n".join(self.links)
            + "\n"
        ).encode()
