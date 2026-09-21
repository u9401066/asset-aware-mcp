"""Resolve source-bound raster representations without migrating old identities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from src.domain.native_image import IMAGE_EXTENSIONS, NativeImageRegionReference
from src.domain.native_image_evidence import (
    image_canonical,
    image_catalog,
    image_frame_reference,
)

if TYPE_CHECKING:
    from src.domain.native_assets import NativeAssetRepository
    from src.domain.native_image import (
        ImageColorPolicy,
        NativeImageAdapter,
        NativeImageFrameReference,
    )
    from src.domain.native_image_archive import NativeImageArchive


class NativeImageProjection:
    def __init__(
        self,
        repository: NativeAssetRepository,
        images: NativeImageAdapter,
        archive: NativeImageArchive | None = None,
    ):
        self.repository, self.images, self.archive = repository, images, archive

    def source(self, asset_id: str, revision: str) -> bytes:
        if self.repository.load(asset_id).format not in IMAGE_EXTENSIONS:
            raise ValueError("This asset has no native raster adapter")
        return self.repository.read(asset_id, revision)

    def records(
        self, asset_id: str, revision: str, catalog_sha256: str | None = None
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        data = self.source(asset_id, revision)
        if catalog_sha256 and self.archive:
            retained = self.archive.catalog(asset_id, revision, catalog_sha256)
            if retained is not None:
                return retained
        records = self.images.records(data)
        catalog = image_catalog(data, records)
        if catalog_sha256 and catalog["catalog_sha256"] != catalog_sha256:
            raise ValueError(
                "Requested image catalog is not retained and current decoder cannot reproduce it"
            )
        if self.archive:
            self.archive.retain_catalog(asset_id, revision, records)
        return catalog, records

    def frame(self, reference: NativeImageFrameReference) -> tuple[dict[str, Any], str]:
        data = self.source(reference.asset_id, reference.revision)
        if self.archive:
            retained = self.archive.frame(reference)
            if retained is not None:
                return retained, "retained_projection"
        record = self.images.read_frame(data, reference.locator)
        actual = image_frame_reference(record, reference.asset_id, reference.revision)
        if self.archive:
            self.archive.retain_frame(actual, record)
        return record, "current_decoder"

    def preview(
        self,
        reference: NativeImageFrameReference | NativeImageRegionReference,
        size: int,
        color_policy: ImageColorPolicy,
    ) -> tuple[dict[str, Any], str]:
        data = self.source(reference.asset_id, reference.revision)
        if self.archive:
            retained = self.archive.preview(reference, size, color_policy)
            if retained is not None:
                return retained, "retained_preview"
        parent = (
            reference.parent
            if isinstance(reference, NativeImageRegionReference)
            else reference
        )
        preview = (
            self.images.render_region(
                data, parent.locator, reference.selector, size, color_policy
            )
            if isinstance(reference, NativeImageRegionReference)
            else self.images.render(data, parent.locator, size, color_policy)
        )
        self._accept_preview(parent, preview)
        if self.archive:
            self.archive.retain_preview(reference, size, color_policy, preview)
        return preview, "current_decoder"

    @staticmethod
    def _accept_preview(
        reference: NativeImageFrameReference, preview: dict[str, Any]
    ) -> None:
        if (
            image_frame_reference(
                preview["record"], reference.asset_id, reference.revision
            )
            != reference
        ):
            raise ValueError(
                "Historical image preview is not retained and current decoder cannot reproduce its frame; use the original decoder or a previously retained preview recipe"
            )

    def wiki_frames(
        self,
        asset_id: str,
        revision: str,
        records: list[dict[str, Any]],
        color_policy: ImageColorPolicy,
    ) -> list[dict[str, Any]]:
        data = self.source(asset_id, revision)
        references = [
            image_frame_reference(record, asset_id, revision) for record in records
        ]
        previews = [
            self.archive.preview(ref, 768, color_policy) if self.archive else None
            for ref in references
        ]
        current = None
        if any(preview is None for preview in previews):
            current = {
                item["record"]["locator"]["frame_index"]: item
                for item in self.images.decompose(data, color_policy)
            }
        result, total = [], len(data)
        for ref, retained in zip(references, previews, strict=True):
            item = retained
            if item is None:
                assert current is not None
                item = current.get(ref.locator.frame_index)
                if item is None:
                    raise ValueError(
                        "Historical image frame is absent from current decoder"
                    )
                self._accept_preview(ref, item)
                item = {
                    **item,
                    "source_pixel_bounds": [0, 0, *item["record"]["displayed_size_px"]],
                }
                if self.archive:
                    self.archive.retain_preview(ref, 768, color_policy, item)
            total += len(image_canonical(item["record"])) + len(item["png"])
            if total > 96 * 1024 * 1024:
                raise ValueError("Raster decomposition exceeds its output budget")
            result.append(item)
        return result
