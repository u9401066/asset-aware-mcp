"""Explicit new canvases and pixel-only derivatives; source files are never encoded again."""

from __future__ import annotations

import hashlib
import io
from typing import TYPE_CHECKING

from PIL import Image

from src.domain.native_asset_models import MAX_NATIVE_BYTES, NativeEditResult
from src.domain.native_image_evidence import image_frame_reference, image_region_bounds
from src.infrastructure.native_image_decode import _frames, rgba_hash
from src.infrastructure.native_image_preview import _rgba

if TYPE_CHECKING:
    from src.domain.native_image import NativeImageBlank, NativeImageExtract


def _save_checked(image: Image.Image, format_name: str) -> bytes:
    expected_mode, expected_size = image.mode, image.size
    expected_pixels = hashlib.sha256(image.tobytes()).hexdigest()
    expected_rgba = rgba_hash(image)
    image.info.clear()
    output = io.BytesIO()
    try:
        image.save(
            output,
            format=format_name,
            **({"compression": "tiff_deflate"} if format_name == "TIFF" else {}),
        )
    except OSError as exc:
        raise ValueError(
            "This output format cannot retain the decoded pixel mode; choose TIFF or explicitly request srgb_rgba8"
        ) from exc
    data = output.getvalue()
    if len(data) > MAX_NATIVE_BYTES:
        raise ValueError("Created raster document exceeds 64 MiB")
    actual = [record for record, _ in _frames(data)]
    if len(actual) != 1:
        raise ValueError("Raster creation did not preserve a single frame")
    record = actual[0]
    if (
        record["decoded_mode"],
        tuple(record["displayed_size_px"]),
        record["decoded_pixels_sha256"],
    ) != (expected_mode, expected_size, expected_pixels):
        raise ValueError(
            "Raster encoding changed requested sample values, pixel mode or geometry"
        )
    with Image.open(io.BytesIO(data)) as decoded:
        if rgba_hash(decoded) != expected_rgba:
            raise ValueError(
                "Raster encoding changed the palette or decoded display colors"
            )
    return data


def create_blank_image(request: NativeImageBlank) -> tuple[bytes, NativeEditResult]:
    with Image.new(
        "RGBA", (request.width, request.height), tuple(request.rgba)
    ) as image:
        data = _save_checked(image, "PNG")
    return data, NativeEditResult(
        changed_parts=["frame:0"],
        preserved_parts=0,
        changes=[{"canvas": request.model_dump(mode="json")}],
        checks=[
            "decoded_sample_exact_readback",
            "geometry_and_pixel_mode",
            "palette_and_rgba_readback",
        ],
        review_required=["intended_canvas_and_color"],
    )


def extract_image(
    data: bytes, request: NativeImageExtract
) -> tuple[bytes, NativeEditResult]:
    reference = request.reference
    if hashlib.sha256(data).hexdigest() != reference.revision:
        raise ValueError(
            "Image extraction source bytes do not match the frame revision"
        )
    result = None
    for record, image in _frames(data):
        if record["locator"] != reference.locator.model_dump():
            continue
        if (
            image_frame_reference(record, reference.asset_id, reference.revision)
            != reference
        ):
            raise ValueError(
                "Image extraction requires the complete current source frame reference"
            )
        if request.pixel_policy == "srgb_rgba8":
            selected, color_transform = _rgba(image, "embedded_to_srgb")
        else:
            source_bits, decoded_bits = (
                record["source_bits_per_sample"],
                record["decoded_bits_per_sample"],
            )
            if not source_bits or not decoded_bits or max(source_bits) > decoded_bits:
                raise ValueError(
                    "Decoder precision cannot preserve source samples; an explicit srgb_rgba8 projection is required"
                )
            selected, color_transform = image.copy(), "unchanged_decoded_samples"
        try:
            bounds = (
                image_region_bounds(request.region, image.size)
                if request.region
                else [0, 0, image.width, image.height]
            )
            x0, y0, x1, y1 = bounds
            cropped = selected.crop((x0, y0, x1, y1))
            selected.close()
            selected = cropped
            output = _save_checked(
                selected, "PNG" if request.name.lower().endswith(".png") else "TIFF"
            )
            report = NativeEditResult(
                changed_parts=["frame:0"],
                preserved_parts=0,
                changes=[
                    {
                        "source": reference.model_dump(mode="json"),
                        "region": request.region.model_dump(mode="json")
                        if request.region
                        else None,
                        "source_pixel_bounds": bounds,
                        "pixel_policy": request.pixel_policy,
                        "metadata_policy": request.metadata_policy,
                        "color_transform": color_transform,
                        "discarded_metadata_sha256": record["metadata"][
                            "metadata_sha256"
                        ],
                        "source_preserved": True,
                    }
                ],
                checks=[
                    "complete_source_frame_reference",
                    "explicit_projection_and_metadata_policy",
                    "decoded_sample_exact_readback",
                    "geometry_and_pixel_mode",
                    "palette_and_rgba_readback",
                ],
                review_required=[
                    "region_coverage",
                    "meaning_and_transcription",
                    "color_and_precision",
                    "metadata_omission_in_derived_file",
                ],
            )
            result = output, report
        finally:
            selected.close()
    if result is None:
        raise ValueError("Image extraction frame is outside the source sequence")
    return result
