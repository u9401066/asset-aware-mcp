"""Explicit new TIFF sequences with complete source references and sample readback."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from src.domain.native_asset_models import MAX_NATIVE_BYTES, NativeEditResult
from src.domain.native_image import MAX_DOCUMENT_PIXELS, NativeImageExtract
from src.infrastructure.native_image_creation import extract_image
from src.infrastructure.native_image_decode import _frames

if TYPE_CHECKING:
    from PIL import Image

    from src.domain.native_image import NativeImageCompose


def compose_images(
    request: NativeImageCompose, sources: dict[str, bytes]
) -> tuple[bytes, NativeEditResult]:
    keys = {f"{f.reference.asset_id}:{f.reference.revision}" for f in request.frames}
    if set(sources) != keys:
        raise ValueError("Image composition requires exactly its referenced sources")
    if sum(len(data) for data in sources.values()) > MAX_NATIVE_BYTES:
        raise ValueError("Image composition sources exceed 64 MiB in aggregate")
    images: list[Image.Image] = []
    expected = []
    changes = []
    total = 0
    try:
        for index, frame in enumerate(request.frames):
            data = sources[f"{frame.reference.asset_id}:{frame.reference.revision}"]
            derived, report = extract_image(
                data,
                NativeImageExtract(
                    name="frame.tif",
                    reference=frame.reference,
                    region=frame.region,
                    pixel_policy=frame.pixel_policy,
                    metadata_policy=request.metadata_policy,
                ),
            )
            for record, image in _frames(derived):
                total += image.width * image.height
                if total > MAX_DOCUMENT_PIXELS:
                    raise ValueError("Image composition exceeds aggregate pixel limit")
                saved = image.copy()
                saved.info.clear()
                images.append(saved)
                expected.append(record)
            changes.append({"output_frame": index, **report.changes[0]})
        output = io.BytesIO()
        images[0].save(
            output,
            format="TIFF",
            compression="tiff_deflate",
            save_all=True,
            append_images=images[1:],
        )
        encoded = output.getvalue()
        if len(encoded) > MAX_NATIVE_BYTES:
            raise ValueError("Created TIFF exceeds 64 MiB")
        actual = [record for record, _ in _frames(encoded)]
        if len(actual) != len(expected):
            raise ValueError("TIFF composition changed the requested frame count")
        fields = (
            "displayed_size_px",
            "decoded_mode",
            "decoded_pixels_sha256",
            "decoded_rgba8_sha256",
        )
        if any(
            before[key] != after[key]
            for before, after in zip(expected, actual, strict=True)
            for key in fields
        ):
            raise ValueError("TIFF composition changed requested samples or colors")
        return encoded, NativeEditResult(
            changed_parts=[f"frame:{index}" for index in range(len(images))],
            preserved_parts=0,
            changes=changes,
            checks=[
                "complete_source_frame_references",
                "explicit_projection_and_metadata_policy",
                "all_output_frames_reopened",
                "exact_frame_count_order_geometry_samples_colors",
            ],
            review_required=[
                "intended_frame_order_and_correspondence",
                "actual_frame_appearance",
                "meaning_and_transcription",
                "color_and_precision",
                "metadata_and_animation_timing_omission",
            ],
        )
    finally:
        for image in images:
            image.close()
