"""Attach exact source regions without borrowing target bibliographic metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_pdf_region_service import (
    REGION_BOUNDARY,
    NativePdfRegionService,
)
from src.application.native_wiki_format import canonical_json
from src.domain.citation_format import CitationMetadata
from src.domain.native_derivation import fingerprint

if TYPE_CHECKING:
    from src.application.native_evidence_service import NativeEvidenceService
    from src.application.native_wiki_format import NativeWikiContent
    from src.domain.native_pdf_region import NativePdfRegionReference


def add_region(
    content: NativeWikiContent,
    reference: NativePdfRegionReference,
    evidence: NativeEvidenceService,
    source_attachment: str,
) -> dict[str, Any]:
    result = NativePdfRegionService(evidence).preview(reference, 768)
    key = fingerprint(reference)
    stem = f"{content.prefix}-region-{key}"
    asset = evidence.repository.load(reference.asset_id)
    metadata = (
        content.metadata
        if reference.asset_id == content.identity["asset_id"]
        else CitationMetadata()
    )
    record = {
        **result["region"],
        "preview_attachment": stem + ".png",
        "preview_sha256": result["image_sha256"],
        "rendering": result["rendering"],
        "source_attachment": source_attachment,
        "citation_contract": content.contract.model_dump(mode="json"),
        "citation_metadata": metadata.model_dump(mode="json"),
        "metadata_origin": "exported asset metadata"
        if reference.asset_id == content.identity["asset_id"]
        else "external source name only; target metadata is not inherited",
    }
    try:
        presentation = render_citation(
            content.contract,
            metadata,
            source_id=reference.asset_id,
            asset_id=reference.asset_id,
            title=asset.name,
            locator={
                "page": reference.parent.locator.page_index + 1,
                "pdf_region": reference.selector.rect,
            },
        )
        record["citation_presentation"] = presentation
        display = f"Citation: {citation_markdown(presentation['inline'])}\n\nReference: {citation_markdown(presentation['reference'])}"
    except ValueError as exc:
        record["citation_unavailable"] = str(exc)
        display = "Citation display unavailable: " + citation_markdown(str(exc))
    content.add_file(stem + ".png", result["image_png"])
    content.add_file(stem + ".json", canonical_json(record) + b"\n")
    content.add_file(
        stem + ".md",
        (
            f"# PDF region {key[:12]}\n\n![Region preview]({stem}.png)\n\n"
            f"{display}\n\nSource: `{reference.asset_id}`\n\nRevision: `{reference.revision}`\n\n"
            f"Page: {reference.parent.locator.page_index + 1}; displayed CropBox fractions: `{reference.selector.rect}`\n\n"
            f"Region representation SHA-256: `{reference.value_sha256}`\n\n"
            f"[Full region and rendering record]({stem}.json) · [Original PDF]({source_attachment})\n\n"
            f"{REGION_BOUNDARY}\n\n[[{content.index_name[:-3]}|Target index]]\n"
        ).encode(),
    )
    content.links.append(f"- [[{stem}|PDF region {key[:12]}]]")
    return {
        "reference": reference.model_dump(mode="json"),
        "record_file": stem + ".json",
        "note": stem + ".md",
        "preview_attachment": stem + ".png",
        "preview_sha256": result["image_sha256"],
    }
