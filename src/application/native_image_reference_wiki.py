"""Readable frame/region evidence in cross-format derivation snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown, render_citation
from src.application.native_image_evidence import NativeImageEvidence
from src.application.native_wiki_format import canonical_json
from src.domain.citation_format import CitationMetadata
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_derivation import fingerprint
from src.domain.native_image import NativeImageRegionReference

if TYPE_CHECKING:
    from src.application.native_evidence_service import NativeEvidenceService
    from src.application.native_wiki_format import NativeWikiContent
    from src.domain.native_image import ImageColorPolicy, NativeImageFrameReference


def add_image_reference(
    content: NativeWikiContent,
    reference: NativeImageFrameReference | NativeImageRegionReference,
    evidence: NativeEvidenceService,
    source_attachment: str,
    color_policy: ImageColorPolicy,
) -> dict[str, Any]:
    if evidence.images is None:
        raise ValueError("Image evidence renderer is not configured")
    reader = NativeImageEvidence(
        evidence.repository, evidence.images, evidence.image_archive
    )
    region = isinstance(reference, NativeImageRegionReference)
    raw = (
        reader.region(reference)
        if isinstance(reference, NativeImageRegionReference)
        else reader.frame(reference)
    )
    result = reader.render(
        NativeDocumentRequest.model_validate(
            {
                "op": "read_image_region" if region else "render_image_frame",
                "reference": reference.model_dump(mode="json"),
                "render_size": 768,
                "image_color_policy": color_policy,
            }
        )
    )
    key = fingerprint(reference)
    stem = f"{content.prefix}-image-evidence-{key}"
    asset = evidence.repository.load(reference.asset_id)
    local = reference.asset_id == content.identity["asset_id"]
    metadata = content.metadata if local else CitationMetadata()
    locator = (
        reference.parent.locator.model_dump()
        if isinstance(reference, NativeImageRegionReference)
        else reference.locator.model_dump()
    )
    if isinstance(reference, NativeImageRegionReference):
        locator["image_region"] = reference.selector.rect
    record = {
        **raw,
        "preview_attachment": stem + ".png",
        "preview_sha256": result["image_sha256"],
        "rendering": result["rendering"],
        "source_attachment": source_attachment,
        "citation_contract": content.contract.model_dump(mode="json"),
        "citation_metadata": metadata.model_dump(mode="json"),
        "metadata_origin": "exported asset metadata"
        if local
        else "external source name only; target metadata is not inherited",
    }
    try:
        presentation = render_citation(
            content.contract,
            metadata,
            source_id=reference.asset_id,
            asset_id=reference.asset_id,
            title=asset.name,
            locator=locator,
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
            f"# Image evidence {key[:12]}\n\n![Source preview]({stem}.png)\n\n{display}\n\n"
            f"Source: `{reference.asset_id}`\n\nRevision: `{reference.revision}`\n\n"
            f"[Complete evidence record]({stem}.json) · [Original raster]({source_attachment})\n\n"
            "Source and geometry verification does not prove transcription or meaning. Agent reviews actual pixels, color and selected coverage.\n\n"
            f"[[{content.index_name[:-3]}|Target index]]\n"
        ).encode(),
    )
    return {
        "reference": reference.model_dump(mode="json"),
        "record_file": stem + ".json",
        "note": stem + ".md",
        "preview_attachment": stem + ".png",
        "preview_sha256": result["image_sha256"],
    }
