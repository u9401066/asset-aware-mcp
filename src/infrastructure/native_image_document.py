"""Native raster adapter for frame reads, previews and explicit revisions."""

from __future__ import annotations

import hashlib
import math
from typing import TYPE_CHECKING, Any

from src.infrastructure.native_image_decode import _frames
from src.infrastructure.native_image_metadata import canonical
from src.infrastructure.native_image_preview import _preview

if TYPE_CHECKING:
    from src.domain.native_asset_models import NativeEditResult
    from src.domain.native_image import (
        ImageColorPolicy,
        NativeImageBlank,
        NativeImageCompose,
        NativeImageExtract,
        NativeImageFrameLocator,
        NativeImageRegionSelector,
        NativeImageRevisionPlan,
    )


class NativeImage:
    def records(self, data: bytes) -> list[dict[str, Any]]:
        records, size = [], 0
        for record, _ in _frames(data):
            size += len(canonical(record))
            if size > 16 * 1024 * 1024:
                raise ValueError(
                    "Raster frame records exceed their aggregate output budget"
                )
            records.append(record)
        return records

    def create(self, request: NativeImageBlank) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_image_creation import create_blank_image

        return create_blank_image(request)

    def compose(
        self, request: NativeImageCompose, sources: dict[str, bytes]
    ) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_image_compose import compose_images

        return compose_images(request, sources)

    def extract(
        self, data: bytes, request: NativeImageExtract
    ) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_image_creation import extract_image

        return extract_image(data, request)

    def accept_candidate(
        self,
        data: bytes,
        candidate: bytes,
        request: NativeImageRevisionPlan,
        asset_id: str,
    ) -> tuple[bytes, NativeEditResult]:
        from src.infrastructure.native_image_revision import validate_image_candidate

        report = validate_image_candidate(
            data,
            candidate,
            self.records(data),
            self.records(candidate),
            request,
            asset_id,
        )
        return candidate, report

    def inspect(self, data: bytes) -> dict[str, Any]:
        frames = []
        format_name = None
        for record, _ in _frames(data):
            format_name = record["format"]
            frames.append(
                {
                    key: record[key]
                    for key in (
                        "locator",
                        "stored_size_px",
                        "displayed_size_px",
                        "source_orientation",
                        "decoded_mode",
                        "frame_role",
                        "duration_ms",
                        "loop",
                    )
                }
            )
        return {
            "format": format_name,
            "frame_count": len(frames),
            "frames": frames,
            "frame_scope": "Main decoder frame sequence, including APNG default images; not every private thumbnail/sub-IFD/layer",
            "source_sha256": hashlib.sha256(data).hexdigest(),
            "size_bytes": len(data),
        }

    def read_frame(
        self, data: bytes, locator: NativeImageFrameLocator
    ) -> dict[str, Any]:
        result = None
        for record, _ in _frames(data):
            if record["locator"] == locator.model_dump():
                result = record
        if result is None:
            raise ValueError("Image frame locator is outside the source sequence")
        return result

    def render(
        self,
        data: bytes,
        locator: NativeImageFrameLocator,
        size: int,
        color_policy: ImageColorPolicy = "embedded_to_srgb",
    ) -> dict[str, Any]:
        return self._render(data, locator, size, color_policy, None)

    def render_region(
        self,
        data: bytes,
        locator: NativeImageFrameLocator,
        selector: NativeImageRegionSelector,
        size: int,
        color_policy: ImageColorPolicy = "embedded_to_srgb",
    ) -> dict[str, Any]:
        return self._render(data, locator, size, color_policy, selector)

    def _render(
        self,
        data: bytes,
        locator: NativeImageFrameLocator,
        size: int,
        color_policy: ImageColorPolicy,
        selector: NativeImageRegionSelector | None,
    ) -> dict[str, Any]:
        result = None
        for record, image in _frames(data):
            if record["locator"] != locator.model_dump():
                continue
            bounds = None
            if selector is not None:
                x0, y0, x1, y1 = selector.rect
                bounds = (
                    math.floor(x0 * image.width),
                    math.floor(y0 * image.height),
                    math.ceil(x1 * image.width),
                    math.ceil(y1 * image.height),
                )
            result = {
                **_preview(image, size, color_policy, bounds),
                "record": record,
                "source_pixel_bounds": list(bounds)
                if bounds
                else [0, 0, image.width, image.height],
            }
        if result is None:
            raise ValueError("Image frame locator is outside the source sequence")
        return result

    def decompose(
        self, data: bytes, color_policy: ImageColorPolicy = "embedded_to_srgb"
    ) -> list[dict[str, Any]]:
        result, size = [], len(data)
        for record, image in _frames(data):
            preview = _preview(image, 768, color_policy)
            size += len(canonical(record)) + len(preview["png"])
            if size > 96 * 1024 * 1024:
                raise ValueError("Raster decomposition exceeds its output budget")
            result.append({"record": record, **preview})
        return result
