"""Portable source attachments and provenance notes for a pinned native snapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.citation_format_service import citation_markdown
from src.application.native_derivation_service import REVIEW_BOUNDARY
from src.application.native_image_reference_wiki import add_image_reference
from src.application.native_pdf_region_wiki import add_region
from src.application.native_selection_service import NativeSelectionService
from src.domain.native_derivation import canonical, fingerprint
from src.domain.native_image import (
    IMAGE_EXTENSIONS,
    NativeImageFrameReference,
    NativeImageRegionReference,
)
from src.domain.native_pdf_region import NativePdfRegionReference
from src.domain.native_selection import NativeSelectionReference, canonical_selection

SOURCE_SUFFIXES = {
    "pdf",
    "docx",
    "pptx",
    "xlsx",
    "xlsm",
    "png",
    "jpg",
    "jpeg",
    "csv",
    "tsv",
} | IMAGE_EXTENSIONS

if TYPE_CHECKING:
    from src.application.native_derivation_service import NativeDerivationService
    from src.application.native_wiki_format import NativeWikiContent
    from src.domain.native_assets import NativeAssetRepository
    from src.domain.native_derivation import (
        NativeDerivationLedger,
        NativeDerivationRecord,
    )
    from src.domain.native_image import ImageColorPolicy


def add_derivations(
    content: NativeWikiContent,
    ledger: NativeDerivationLedger,
    service: NativeDerivationService,
    assets: NativeAssetRepository,
    *,
    image_color_policy: ImageColorPolicy = "embedded_to_srgb",
) -> None:
    if not ledger.events:
        return
    records = [
        record
        for record in ledger.active_records().values()
        if record.derivation.target.revision == content.identity["revision"]
    ]
    attachments: dict[str, Any] = {}
    selections: dict[str, Any] = {}
    regions: dict[str, Any] = {}
    image_records: dict[str, Any] = {}
    for record in records:
        service.require_valid(record.derivation.target)
        links = []
        for ref in [record.derivation.target, *record.derivation.sources]:
            if isinstance(ref, NativeSelectionReference):
                key = fingerprint(ref)
                if key not in selections:
                    selected = NativeSelectionService(service.evidence).record(ref)
                    name = f"{content.prefix}-selection-{key}.json"
                    content.add_file(name, canonical_selection(selected) + b"\n")
                    selections[key] = {
                        "reference": ref.model_dump(mode="json"),
                        "record_file": name,
                    }
                links.append(
                    f"- [Exact selection {key[:12]}]({selections[key]['record_file']})"
                )
        for ref in record.derivation.sources:
            service.require_valid(ref)
            key = f"{ref.asset_id}:{ref.revision}"
            if key not in attachments:
                asset = assets.load(ref.asset_id)
                suffix = asset.format if asset.format in SOURCE_SUFFIXES else "bin"
                name = f"{content.prefix}-evidence-{fingerprint(ref)}.{suffix}"
                content.add_file(name, assets.read(ref.asset_id, ref.revision))
                attachments[key] = {
                    "asset_id": ref.asset_id,
                    "revision": ref.revision,
                    "name": asset.name,
                    "format": asset.format,
                    "attachment": name,
                }
            links.append(
                f"- [{citation_markdown(attachments[key]['name'])}]({attachments[key]['attachment']})"
            )
        for ref in [record.derivation.target, *record.derivation.sources]:
            region = ref.parent if isinstance(ref, NativeSelectionReference) else ref
            if isinstance(
                region, NativeImageFrameReference | NativeImageRegionReference
            ):
                key = fingerprint(region)
                if key not in image_records:
                    same_source = (region.asset_id, region.revision) == (
                        content.identity["asset_id"],
                        content.identity["revision"],
                    )
                    attachment = (
                        content.source_name
                        if same_source
                        else attachments[f"{region.asset_id}:{region.revision}"][
                            "attachment"
                        ]
                    )
                    image_records[key] = add_image_reference(
                        content,
                        region,
                        service.evidence,
                        attachment,
                        image_color_policy,
                    )
                links.append(
                    f"- [[{image_records[key]['note'][:-3]}|Image evidence {key[:12]}]]"
                )
            if isinstance(region, NativePdfRegionReference):
                key = fingerprint(region)
                if key not in regions:
                    same_source = (region.asset_id, region.revision) == (
                        content.identity["asset_id"],
                        content.identity["revision"],
                    )
                    attachment = (
                        content.source_name
                        if same_source
                        else attachments[f"{region.asset_id}:{region.revision}"][
                            "attachment"
                        ]
                    )
                    regions[key] = add_region(
                        content, region, service.evidence, attachment
                    )
                links.append(
                    f"- [[{regions[key]['note'][:-3]}|Source region {key[:12]}]]"
                )
        _add_note(content, record, links)
    content.add_file("derivations.json", canonical(ledger) + b"\n")
    content.extra_manifest["derivations"] = {
        "ledger_file": "derivations.json",
        "ledger_sha256": fingerprint(ledger),
        "active_ids_for_revision": [r.derivation_id for r in records],
        "source_attachments": attachments,
        **({"selection_records": selections} if selections else {}),
        **({"region_records": regions} if regions else {}),
        **({"image_records": image_records} if image_records else {}),
        "verification_scope": "immutable_endpoint_references; active records for exported revision only",
        "review_boundary": REVIEW_BOUNDARY,
    }
    _add_history_note(content, ledger, len(records))


def _add_history_note(
    content: NativeWikiContent, ledger: NativeDerivationLedger, count: int
) -> None:
    stem = content.prefix + "-derivations"
    content.links.append(f"- [[{stem}|Derivation history]]")
    content.add_file(
        stem + ".md",
        (
            "# Derivation history\n\n[Full append-only ledger](derivations.json)\n\n"
            + f"Ledger SHA-256: `{fingerprint(ledger)}`\n\n"
            + f"{count} active assertions target this exact exported revision. "
            + "Other revisions and withdrawn assertions remain in the ledger for audit; "
            + "their endpoints are not revalidated or attached by this export.\n\n"
            + REVIEW_BOUNDARY
            + "\n"
        ).encode("utf-8"),
    )


def _add_note(
    content: NativeWikiContent, record: NativeDerivationRecord, links: list[str]
) -> None:
    stem = f"{content.prefix}-derivation-{record.derivation_id}"
    content.links.append(f"- [[{stem}|Derivation {record.derivation_id[:12]}]]")
    claim = record.derivation
    content.add_file(
        stem + ".md",
        (
            f"# Derivation {record.derivation_id[:12]}\n\n"
            f"Activity: {citation_markdown(claim.activity)}\n\n"
            f"Agent (caller supplied): {citation_markdown(claim.agent)}\n\n"
            f"Target revision: `{claim.target.revision}`\n\n"
            f"Semantic review: {claim.review.semantic_accuracy}; "
            f"layout: {claim.review.rendered_layout}; formulas: {claim.review.formula_results}.\n\n"
            f"{citation_markdown(claim.review.notes)}\n\n"
            + "\n".join(links)
            + "\n\nComplete target/source references are in [derivations.json](derivations.json).\n\n"
            + REVIEW_BOUNDARY
            + f"\n\n[[{content.index_name[:-3]}|Target index]]\n"
        ).encode("utf-8"),
    )
