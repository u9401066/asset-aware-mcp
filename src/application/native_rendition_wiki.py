"""Carry mechanical conversion provenance into portable PDF evidence snapshots."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from src.application.native_rendition_operations import receipt_text, rendition_receipt
from src.domain.native_file_reference import NativeFileReference

if TYPE_CHECKING:
    from src.application.native_wiki_format import NativeWikiContent
    from src.domain.native_assets import NativeAssetRepository, NativeFileAsset


def add_rendition(
    content: NativeWikiContent, asset: NativeFileAsset, assets: NativeAssetRepository
) -> None:
    report = rendition_receipt(asset, content.identity["revision"], assets)
    if report is None:
        return
    reference = NativeFileReference.model_validate(
        report.changes[0]["source_reference"]
    )
    source = assets.load(reference.asset_id)
    data = assets.read(reference.asset_id, reference.revision)
    suffix = "xlsx" if source.format == "xlsx" else "bin"
    name = f"{content.prefix}-rendition-source.{suffix}"
    receipt = receipt_text(report.model_dump()).encode("utf-8")
    content.add_file("rendition.json", receipt)
    content.add_file(name, data)
    content.links.append(
        f"- [Conversion receipt](rendition.json) · [Exact conversion source]({name})"
    )
    content.extra_manifest["rendition"] = {
        "receipt_file": "rendition.json",
        "receipt_sha256": hashlib.sha256(receipt).hexdigest(),
        "source_reference": reference.model_dump(),
        "source_attachment": name,
        "review_boundary": "Mechanical conversion provenance; no Agent semantic, visual or formula-result review is asserted.",
    }
