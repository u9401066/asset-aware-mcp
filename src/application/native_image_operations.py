"""Complete raster records and atomic, reviewable native file transactions."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from src.application.native_document_contract import native_asset_summary
from src.application.native_image_evidence import IMAGE_REVIEW, NativeImageEvidence
from src.application.native_operation_results import revision_result_dict
from src.domain.native_asset_models import MAX_NATIVE_BYTES
from src.domain.native_image import NativeImageFrameReference
from src.domain.native_image_evidence import (
    image_canonical,
    image_catalog,
    image_frame_reference,
)

if TYPE_CHECKING:
    from src.domain.native_assets import (
        NativeAssetRepository,
        NativeDocumentRequest,
        NativeEditResult,
        NativeFileAsset,
    )
    from src.domain.native_image import NativeImageAdapter
    from src.domain.native_image_archive import NativeImageArchive

MAX_IMAGE_READ_BYTES = 16 * 1024 * 1024
RECEIPT_POLICY = "Latest stored operation for this matching file SHA; repeated bytes can have a newer receipt. Pin the complete text_sha256 across all read pages. A no-op retains the previous stored receipt."


def image_text(record: dict[str, Any]) -> str:
    data = image_canonical(record)
    if len(data) > MAX_IMAGE_READ_BYTES:
        raise ValueError("Image record and operation receipt exceed the read budget")
    return data.decode("utf-8")


def image_page(record: dict[str, Any], offset: int, limit: int) -> dict[str, Any]:
    text = image_text(record)
    start = min(offset, len(text))
    end = min(start + limit, len(text))
    while len(json.dumps(text[start:end], ensure_ascii=False)) > 8000:
        end = start + (end - start) // 2
    return {
        "text_excerpt": text[start:end],
        "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "text_length": len(text),
        "excerpt_char_range": [start, end],
        "next_text_offset": end if end < len(text) else None,
        "representation_complete": start == 0 and end == len(text),
        "serialization": "canonical-json; UTF-8 SHA-256",
    }


class NativeImageOperations:
    def __init__(
        self,
        repository: NativeAssetRepository,
        images: NativeImageAdapter,
        archive: NativeImageArchive | None = None,
    ):
        self.repository, self.images = repository, images
        self.evidence = NativeImageEvidence(repository, images, archive)

    def execute(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if request.op in {"create_image", "extract_image", "compose_images"}:
            return self._create(request)
        if request.op in {"render_image_frame", "read_image_region"}:
            return self.evidence.render(request)
        if request.op == "update_image":
            return self._update(request)
        return self._read(request)

    def catalog(
        self, data: bytes, asset_id: str, records: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        if records is None:
            records = self.images.records(data)
        catalog = image_catalog(data, records)
        revision = catalog["source_sha256"]
        return {
            "catalog": catalog,
            "frame_references": [
                image_frame_reference(record, asset_id, revision).model_dump(
                    mode="json"
                )
                for record in records
            ],
        }

    def _read(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.revision is not None
        data = self.evidence.source(request.asset_id, request.revision)
        asset = self.repository.load(request.asset_id)
        if request.op == "read_image":
            _, frames = self.evidence.projection.records(
                asset.asset_id, request.revision, request.image_catalog_sha256
            )
            record = self.catalog(data, asset.asset_id, frames)
        else:
            assert request.image_locator is not None
            if request.reference is not None:
                ref = request.reference
                if not isinstance(ref, NativeImageFrameReference) or (
                    ref.asset_id,
                    ref.revision,
                    ref.locator,
                ) != (asset.asset_id, request.revision, request.image_locator):
                    raise ValueError(
                        "Pinned image frame reference must match asset, revision and locator"
                    )
                record = self.evidence.frame(ref)
                if record["evidence"] != ref.model_dump(mode="json"):
                    raise ValueError(
                        "Requested frame is not retained and current decoder cannot reproduce it"
                    )
            else:
                record = self.images.read_frame(data, request.image_locator)
                ref = image_frame_reference(record, asset.asset_id, request.revision)
                if self.evidence.projection.archive:
                    self.evidence.projection.archive.retain_frame(ref, record)
                record["evidence"] = ref.model_dump(mode="json")
        latest = next(
            item for item in reversed(asset.history) if item.sha256 == request.revision
        )
        record["operation_result"] = revision_result_dict(
            self.repository, asset, latest
        )
        record["operation_receipt_policy"] = RECEIPT_POLICY
        return {
            "success": True,
            "asset_id": asset.asset_id,
            "inspected_revision": request.revision,
            "image": image_page(record, request.text_offset, request.text_limit),
            "image_evidence_retention_enabled": self.evidence.projection.archive
            is not None,
            **(
                {"image_catalog_sha256": record["catalog"]["catalog_sha256"]}
                if request.op == "read_image"
                else {}
            ),
            "source_written": False,
            "review_required": IMAGE_REVIEW,
        }

    def _check_output(
        self, data: bytes, result: NativeEditResult, asset_id: str
    ) -> None:
        records = self.images.records(data)
        catalog = self.catalog(data, asset_id, records)
        receipt = {
            "operation_result": result.model_dump(mode="json"),
            "operation_receipt_policy": RECEIPT_POLICY,
        }
        image_text({**catalog, **receipt})
        for record, reference in zip(records, catalog["frame_references"], strict=True):
            # Ensure each complete frame read remains retrievable before committing.
            image_text({**record, "evidence": reference, **receipt})

    def _create(self, request: NativeDocumentRequest) -> dict[str, Any]:
        if request.op == "create_image":
            assert request.image_create is not None
            name = request.image_create.name
            data, result = self.images.create(request.image_create)
        elif request.op == "extract_image":
            assert request.image_extract is not None
            name = request.image_extract.name
            ref = request.image_extract.reference
            data, result = self.images.extract(
                self.evidence.source(ref.asset_id, ref.revision), request.image_extract
            )
        else:
            assert request.image_compose is not None
            name = request.image_compose.name
            sources: dict[str, bytes] = {}
            size = 0
            for part in request.image_compose.frames:
                ref = part.reference
                key = f"{ref.asset_id}:{ref.revision}"
                if key in sources:
                    continue
                sources[key] = self.evidence.source(ref.asset_id, ref.revision)
                size += len(sources[key])
                if size > MAX_NATIVE_BYTES:
                    raise ValueError(
                        "Image composition sources exceed 64 MiB in aggregate"
                    )
            data, result = self.images.compose(request.image_compose, sources)
        # A fixed-length valid identity reserves the exact future reference overhead.
        self._check_output(data, result, "file_" + "0" * 32)
        extension = name.rsplit(".", 1)[-1].lower()
        media = "image/png" if extension == "png" else "image/tiff"
        asset = self.repository.create(name, data, extension, media, result=result)
        return self._result(asset, result, True)

    def _update(self, request: NativeDocumentRequest) -> dict[str, Any]:
        assert request.asset_id is not None and request.expected_revision is not None
        assert request.image_update is not None
        asset = self.repository.load(request.asset_id)
        if asset.archived or asset.revision != request.expected_revision:
            raise ValueError("Archived or stale image; inspect before editing")
        data = self.evidence.source(asset.asset_id, request.expected_revision)
        candidate_ref = request.image_update.candidate
        candidate = self.evidence.source(candidate_ref.asset_id, candidate_ref.revision)
        updated, result = self.images.accept_candidate(
            data, candidate, request.image_update, asset.asset_id
        )
        self._check_output(updated, result, asset.asset_id)
        committed = self.repository.commit(
            asset.asset_id, request.expected_revision, updated, result
        )
        return self._result(committed, result, updated != data)

    def _result(
        self, asset: NativeFileAsset, result: NativeEditResult, committed: bool
    ) -> dict[str, Any]:
        return {
            "success": True,
            "asset": native_asset_summary(asset, images_enabled=True),
            "source_written": False,
            "operation_result": {
                "committed": committed,
                "changed_parts": result.changed_parts,
                "checks": result.checks,
                "review_required": result.review_required,
                "full_result_in": "read_image.operation_result" if committed else None,
            },
            "review_request": {
                "op": "read_image",
                "asset_id": asset.asset_id,
                "revision": asset.revision,
            },
        }
