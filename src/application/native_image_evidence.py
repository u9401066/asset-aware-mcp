"""Source-bound frame/region verification and actual raster previews."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.application.native_image_projection import NativeImageProjection
from src.domain.native_image import (
    NativeImageFrameReference,
    NativeImageRegionReference,
)
from src.domain.native_image_evidence import image_frame_reference, image_region_record

if TYPE_CHECKING:
    from src.domain.native_assets import NativeAssetRepository, NativeDocumentRequest
    from src.domain.native_image import NativeImageAdapter, NativeImageRegionSelector
    from src.domain.native_image_archive import NativeImageArchive

IMAGE_REVIEW = [
    "actual_frame_appearance_and_region_coverage",
    "meaning_and_transcription",
    "color_precision_and_metadata",
    "animation_timing_and_viewer_behavior",
]


class NativeImageEvidence:
    def __init__(
        self,
        repository: NativeAssetRepository,
        images: NativeImageAdapter,
        archive: NativeImageArchive | None = None,
    ):
        self.repository, self.images = repository, images
        self.projection = NativeImageProjection(repository, images, archive)

    def source(self, asset_id: str, revision: str) -> bytes:
        return self.projection.source(asset_id, revision)

    def frame(self, reference: NativeImageFrameReference) -> dict[str, Any]:
        record, _ = self.projection.frame(reference)
        return {
            **record,
            "evidence": image_frame_reference(
                record, reference.asset_id, reference.revision
            ).model_dump(mode="json"),
        }

    def region(
        self,
        reference: NativeImageFrameReference | NativeImageRegionReference,
        selector: NativeImageRegionSelector | None = None,
    ) -> dict[str, Any]:
        if isinstance(reference, NativeImageRegionReference):
            if selector is not None:
                raise ValueError("Cannot override an existing image region selector")
            parent, selector = reference.parent, reference.selector
        else:
            parent = reference
            if selector is None:
                raise ValueError(
                    "An image frame reference requires an explicit image_region"
                )
        frame = self.frame(parent)
        if frame.pop("evidence") != parent.model_dump(mode="json"):
            raise ValueError(
                "Image region parent failed complete reference verification"
            )
        record = image_region_record(parent, selector, frame)
        if isinstance(reference, NativeImageRegionReference) and record[
            "evidence"
        ] != reference.model_dump(mode="json"):
            raise ValueError("Image region failed complete reference verification")
        return record

    def verify(
        self, reference: NativeImageFrameReference | NativeImageRegionReference
    ) -> dict[str, Any]:
        asset = self.repository.load(reference.asset_id)
        parent = (
            reference.parent
            if isinstance(reference, NativeImageRegionReference)
            else reference
        )
        record, origin = self.projection.frame(parent)
        parent_valid = (
            image_frame_reference(record, parent.asset_id, parent.revision) == parent
        )
        valid = parent_valid
        if valid and isinstance(reference, NativeImageRegionReference):
            valid = image_region_record(parent, reference.selector, record)[
                "evidence"
            ] == reference.model_dump(mode="json")
        return {
            "success": True,
            "valid": valid,
            "asset_id": reference.asset_id,
            "revision": reference.revision,
            "is_current_managed_revision": asset.revision == reference.revision,
            "archived": asset.archived,
            "verification_scope": reference.verification_scope,
            "checks": {
                "revision_hash": True,
                "parent_reference": parent_valid,
                "representation_hash": valid,
            },
            "representation_origin": origin,
            "current_decoder_reproduction": "not_checked"
            if origin == "retained_projection"
            else "matched"
            if valid
            else "mismatched",
            "source_freshness": "not_checked; refresh tracks external human edits",
            "review_required": IMAGE_REVIEW,
        }

    def render(self, request: NativeDocumentRequest) -> dict[str, Any]:
        reference = request.reference
        if not isinstance(
            reference, NativeImageFrameReference | NativeImageRegionReference
        ):
            raise ValueError(
                "Image preview requires a complete image frame or region reference"
            )
        region = None
        if request.op == "read_image_region":
            region = self.region(reference, request.image_region)
            bound = NativeImageRegionReference.model_validate(region["evidence"])
            parent = bound.parent
        else:
            if not isinstance(reference, NativeImageFrameReference):
                raise ValueError(
                    "Frame rendering requires a complete image frame reference"
                )
            parent = reference
            if self.frame(parent)["evidence"] != parent.model_dump(mode="json"):
                raise ValueError("Image preview failed complete reference verification")
        preview, origin = self.projection.preview(
            bound if region else parent, request.render_size, request.image_color_policy
        )
        return {
            "success": True,
            "asset_id": parent.asset_id,
            "inspected_revision": parent.revision,
            "reference": region["evidence"]
            if region
            else parent.model_dump(mode="json"),
            **({"region": region} if region else {}),
            "preview_origin": origin,
            "current_decoder_reproduction": "not_checked"
            if origin == "retained_preview"
            else "matched",
            "image_png": preview["png"],
            "image_sha256": preview["png_sha256"],
            "source_pixel_bounds": preview["source_pixel_bounds"],
            "preview_size_px": [preview["width_px"], preview["height_px"]],
            "rendering": preview["rendering"],
            "source_written": False,
            "review_required": IMAGE_REVIEW,
        }
