"""Canonical frame/region evidence and complete candidate correspondence checks."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from src.domain.native_image import (
    NativeImageFrameReference,
    NativeImageRegionReference,
    NativeImageRegionSelector,
)


def image_canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def image_frame_reference(
    record: dict[str, Any], asset_id: str, revision: str
) -> NativeImageFrameReference:
    return NativeImageFrameReference(
        asset_id=asset_id,
        revision=revision,
        locator=record["locator"],
        value_sha256=hashlib.sha256(image_canonical(record)).hexdigest(),
    )


def image_catalog(data: bytes, records: list[dict[str, Any]]) -> dict[str, Any]:
    return image_catalog_for_revision(hashlib.sha256(data).hexdigest(), records)


def image_catalog_for_revision(
    revision: str, records: list[dict[str, Any]]
) -> dict[str, Any]:
    if not records:
        raise ValueError("Raster catalog cannot be empty")
    result = {
        "schema_version": "native-image-catalog-v1",
        "source_sha256": revision,
        "format": records[0]["format"],
        "frame_count": len(records),
        "frames": [
            {
                key: record[key]
                for key in (
                    "locator",
                    "stored_size_px",
                    "displayed_size_px",
                    "source_orientation",
                    "frame_role",
                    "duration_ms",
                    "loop",
                )
            }
            | {"record_sha256": hashlib.sha256(image_canonical(record)).hexdigest()}
            for record in records
        ],
    }
    return {
        **result,
        "catalog_sha256": hashlib.sha256(image_canonical(result)).hexdigest(),
    }


def image_region_bounds(
    selector: NativeImageRegionSelector, size: list[int] | tuple[int, int]
) -> list[int]:
    width, height = size
    x0, y0, x1, y1 = selector.rect
    return [
        math.floor(x0 * width),
        math.floor(y0 * height),
        math.ceil(x1 * width),
        math.ceil(y1 * height),
    ]


def image_region_record(
    parent: NativeImageFrameReference,
    selector: NativeImageRegionSelector,
    frame: dict[str, Any],
) -> dict[str, Any]:
    if image_frame_reference(frame, parent.asset_id, parent.revision) != parent:
        raise ValueError("Image region parent does not match its full frame record")
    record = {
        "schema_version": "native-image-region-v1",
        "parent": parent.model_dump(mode="json"),
        "selector": selector.model_dump(mode="json"),
        "displayed_size_px": frame["displayed_size_px"],
        "source_orientation": frame["source_orientation"],
        "source_pixel_bounds": image_region_bounds(
            selector, frame["displayed_size_px"]
        ),
        "coordinate_definition": "Displayed frame after EXIF orientation, top-left origin. Fractions round outward to whole pixels; preview size and color policy do not change identity.",
        "verification_scope": "Immutable source frame and selected geometry, not OCR or semantic support.",
    }
    reference = NativeImageRegionReference(
        asset_id=parent.asset_id,
        revision=parent.revision,
        parent=parent,
        selector=selector,
        value_sha256=hashlib.sha256(image_canonical(record)).hexdigest(),
    )
    return {**record, "evidence": reference.model_dump(mode="json")}
