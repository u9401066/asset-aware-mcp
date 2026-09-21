"""Retain exact inputs and full source references behind image operation receipts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_wiki_format import canonical_json, digest
from src.domain.native_file_reference import NativeFileReference
from src.domain.native_image import IMAGE_EXTENSIONS, NativeImageFrameReference
from src.domain.native_image_evidence import image_frame_reference

if TYPE_CHECKING:
    from src.application.native_image_wiki import NativeImageWikiContent
    from src.domain.native_assets import NativeAssetRepository
    from src.domain.native_image import NativeImageAdapter


def add_image_inputs(
    content: NativeImageWikiContent,
    assets: NativeAssetRepository,
    images: NativeImageAdapter,
) -> None:
    if content.operation is None:
        return
    inputs: dict[str, Any] = {}
    references: dict[str, Any] = {}
    versions: dict[str, Any] = {}
    frame_refs: dict[str, dict[int, NativeImageFrameReference]] = {}
    for change in content.operation["changes"]:
        values = [change.get("source"), change.get("candidate")]
        if "intent" in change:
            values.extend(change["intent"].get(key) for key in ("before", "after"))
        for value in values:
            if value is None:
                continue
            if value.get("schema_version") == "native-image-frame-ref-v1":
                frame_reference = NativeImageFrameReference.model_validate(value)
                reference: NativeImageFrameReference | NativeFileReference = (
                    frame_reference
                )
            else:
                reference = NativeFileReference.model_validate(value)
            key = f"{reference.asset_id}:{reference.revision}"
            if key not in versions:
                versions[key] = (
                    assets.load(reference.asset_id),
                    assets.read(reference.asset_id, reference.revision),
                )
            asset, data = versions[key]
            if isinstance(reference, NativeImageFrameReference):
                if asset.format not in IMAGE_EXTENSIONS:
                    raise ValueError("Image operation input has no raster adapter")
                if key not in frame_refs:
                    frame_refs[key] = {
                        record["locator"]["frame_index"]: image_frame_reference(
                            record, reference.asset_id, reference.revision
                        )
                        for record in images.records(data)
                    }
                if frame_refs[key].get(reference.locator.frame_index) != reference:
                    raise ValueError(
                        "Image operation input failed full frame verification"
                    )
            if key not in inputs:
                if (reference.asset_id, reference.revision) == (
                    content.identity["asset_id"],
                    content.identity["revision"],
                ):
                    name = content.source_name
                else:
                    suffix = asset.format if asset.format in IMAGE_EXTENSIONS else "bin"
                    name = f"{content.prefix}-input-{digest(key.encode())}.{suffix}"
                    content.add_file(name, data)
                inputs[key] = {
                    "asset_id": reference.asset_id,
                    "revision": reference.revision,
                    "name": asset.name,
                    "attachment": name,
                }
            ref_data = reference.model_dump(mode="json")
            references[digest(canonical_json(ref_data))] = ref_data
    if inputs:
        content.extra_manifest["image_inputs"] = {
            "attachments": inputs,
            "references": list(references.values()),
            "verification_scope": "mechanical operation input provenance; no semantic review asserted",
        }
        content.links.extend(
            f"- [Exact operation input]({item['attachment']})"
            for item in inputs.values()
        )
