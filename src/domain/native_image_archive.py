"""Immutable raster representations; storage does not certify decoder correctness."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.domain.native_image import (
        ImageColorPolicy,
        NativeImageFrameReference,
        NativeImageRegionReference,
    )

MAX_IMAGE_RECORD_BYTES = 16 * 1024 * 1024
MAX_IMAGE_PREVIEW_BYTES = 3 * 1024 * 1024


class NativeImageArchive(Protocol):
    def retain_frame(
        self, reference: NativeImageFrameReference, record: dict[str, Any]
    ) -> None: ...

    def frame(self, reference: NativeImageFrameReference) -> dict[str, Any] | None: ...

    def retain_catalog(
        self, asset_id: str, revision: str, records: list[dict[str, Any]]
    ) -> dict[str, Any]: ...

    def catalog(
        self, asset_id: str, revision: str, catalog_sha256: str
    ) -> tuple[dict[str, Any], list[dict[str, Any]]] | None: ...

    def retain_preview(
        self,
        reference: NativeImageFrameReference | NativeImageRegionReference,
        size: int,
        color_policy: ImageColorPolicy,
        preview: dict[str, Any],
    ) -> None: ...

    def preview(
        self,
        reference: NativeImageFrameReference | NativeImageRegionReference,
        size: int,
        color_policy: ImageColorPolicy,
    ) -> dict[str, Any] | None: ...
