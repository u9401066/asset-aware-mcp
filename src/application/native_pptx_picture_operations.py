"""Compose and extract exact image assets through native presentation revisions."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.domain.native_assets import NativeEditResult
from src.domain.native_pptx import shape_representation_sha256

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeFileAsset,
    )
    from src.domain.native_pptx import NativePresentationAdapter

PICTURE_REVIEW = [
    "semantic_accuracy",
    "rendered_slide_layout",
    "crop_and_image_mapping",
    "effects_and_color_profiles",
    "accessibility_alt_text",
]


class NativePptxPictureOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        presentations: NativePresentationAdapter,
    ):
        self.repository = repository
        self.presentations = presentations

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None
        asset = self.repository.load(request.asset_id)
        if asset.format != "pptx":
            raise ValueError("Picture operation requires a native PPTX asset")
        revision = request.revision or asset.revision
        data = self.repository.read(asset.asset_id, revision)
        if request.op in {"read_pptx_picture", "extract_pptx_picture"}:
            return self._read(request, asset, revision, data)
        return self._mutate(request, asset, data)

    def _read(
        self,
        request: NativeDocumentRequest,
        asset: NativeFileAsset,
        revision: str,
        data: bytes,
    ) -> dict[str, Any]:
        assert request.pptx_locator is not None
        preview = request.op == "read_pptx_picture"
        result = self.presentations.read_picture(
            data, request.pptx_locator, request.render_size if preview else None
        )
        raw = result.pop("image_bytes")
        result.pop(
            "mapping_xml"
        )  # Complete shape JSON is available through read_pptx_shape.
        shape = self.presentations.read_shape(data, request.pptx_locator)
        evidence = {
            "schema_version": "native-pptx-shape-ref-v1",
            "asset_id": asset.asset_id,
            "revision": revision,
            "locator": shape["locator"],
            "value_sha256": shape_representation_sha256(shape),
            "verification_scope": "immutable_native_representation",
        }
        if preview:
            return {
                "success": True,
                "asset_id": asset.asset_id,
                "inspected_revision": revision,
                **result,
                "shape_reference": evidence,
                "image_sha256": hashlib.sha256(result["image_png"]).hexdigest(),
                "review_required": PICTURE_REVIEW,
            }
        return self._extract(result, raw, evidence)

    def _extract(self, result: dict, raw: bytes, evidence: dict) -> dict[str, Any]:
        checks = NativeEditResult(
            changed_parts=[result["media_part"]],
            preserved_parts=0,
            checks=[
                "source_revision_hash",
                "internal_image_relationship",
                "exact_extracted_media_bytes",
            ],
            changes=[
                {
                    "operation": "extract_picture",
                    "source_reference": evidence,
                    "media_part": result["media_part"],
                    "media_sha256": result["image"]["sha256"],
                }
            ],
            review_required=PICTURE_REVIEW,
        )
        extracted = self.repository.create(
            "picture-"
            + result["image"]["sha256"][:12]
            + "."
            + result["image"]["extension"],
            raw,
            result["image"]["extension"],
            result["image"]["media_type"],
            result=checks,
        )
        return {
            "success": True,
            "asset": native_asset_summary(extracted),
            "source_written": False,
            "operation_result": checks.model_dump(),
            "review_required": PICTURE_REVIEW,
        }

    def _sources(self, items: list) -> dict[str, bytes]:
        result, size = {}, 0
        for item in items:
            ref = item.image
            key = f"{ref.asset_id}:{ref.revision}"
            if key not in result:
                result[key] = self.repository.read(ref.asset_id, ref.revision)
                size += len(result[key])
                if size > 32 * 1024 * 1024:
                    raise ValueError("Picture source bytes exceed 32 MiB")
        return result

    def _mutate(
        self, request: NativeDocumentRequest, asset: NativeFileAsset, data: bytes
    ) -> dict[str, Any]:
        assert request.expected_revision is not None
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale presentation asset")
        for edit in request.pptx_picture_edits:
            if (
                edit.reference.asset_id != asset.asset_id
                or edit.reference.revision != asset.revision
            ):
                raise ValueError(
                    "Picture replacement reference has different asset or revision"
                )
        if request.op == "add_pptx_pictures":
            updated, checks = self.presentations.add_pictures(
                data, request.pptx_pictures, self._sources(request.pptx_pictures)
            )
        else:
            updated, checks = self.presentations.replace_pictures(
                data,
                request.pptx_picture_edits,
                self._sources(request.pptx_picture_edits),
            )
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, checks
        )
        return {
            "success": True,
            "asset": native_asset_summary(committed, pptx_enabled=True),
            "operation_result": checks.model_dump(),
            "source_written": False,
            "review_request": {
                "op": "read_pptx",
                "asset_id": asset.asset_id,
                "revision": committed.revision,
            },
        }
