"""Bounded complete raster decoding with explicit orientation and precision."""

from __future__ import annotations

import hashlib
import io
import warnings
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageOps, TiffImagePlugin, UnidentifiedImageError, __version__

from src.domain.native_asset_models import MAX_NATIVE_BYTES
from src.domain.native_image import (
    IMAGE_FORMATS,
    MAX_DOCUMENT_PIXELS,
    MAX_FRAME_PIXELS,
    MAX_IMAGE_FRAMES,
)
from src.infrastructure.native_image_metadata import canonical, metadata_record
from src.infrastructure.native_image_structure import gif_frame_count, tiff_frame_count

if TYPE_CHECKING:
    from collections.abc import Iterator


def _dimensions(image: Image.Image) -> tuple[int, int]:
    if isinstance(image, TiffImagePlugin.TiffImageFile):
        return int(image.tag_v2[256]), int(image.tag_v2[257])
    return image.size


def _encoded_bits(image: Image.Image, data: bytes) -> list[int] | None:
    if image.format == "PNG":
        return [data[24]]
    if isinstance(image, TiffImagePlugin.TiffImageFile):
        value = image.tag_v2.get(258, (1,))
        return [int(v) for v in value] if isinstance(value, tuple) else [int(value)]
    if image.format == "JPEG":
        bits = getattr(image, "bits", None)
        return [bits] if type(bits) is int else None
    if image.format in {"GIF", "WEBP"}:
        return [8]
    if image.format == "BMP" and data[:2] == b"BM":
        header = int.from_bytes(data[14:18], "little")
        if header == 12 and len(data) >= 26:
            bits = int.from_bytes(data[24:26], "little")
        elif header >= 40 and len(data) >= 34:
            bits = int.from_bytes(data[28:30], "little")
            if int.from_bytes(data[30:34], "little") not in {0, 1, 2}:
                return None  # Bitfields may have greater precision than RGB8.
        else:
            return None
        return [bits] if bits in {1, 4, 8} else [8, 8, 8] if bits == 24 else None
    # AVIF may have higher source precision than Pillow exposes; never invent it.
    return None


def _decoded_bits(mode: str) -> int | None:
    if mode == "1":
        return 1
    if mode.startswith("I;16"):
        return 16
    if mode in {"I", "F"}:
        return 32
    if mode in {
        "L",
        "LA",
        "P",
        "PA",
        "RGB",
        "RGBA",
        "RGBX",
        "CMYK",
        "YCbCr",
        "LAB",
        "HSV",
    }:
        return 8
    return None


def _frames(data: bytes) -> Iterator[tuple[dict[str, Any], Image.Image]]:
    if not data or len(data) > MAX_NATIVE_BYTES:
        raise ValueError("Raster document must contain 1 byte to 64 MiB")
    expected_frames = tiff_frame_count(data) or gif_frame_count(data)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=list(IMAGE_FORMATS)) as check:
                check.verify()
            with Image.open(io.BytesIO(data), formats=list(IMAGE_FORMATS)) as image:
                if image.format in {"PNG", "WEBP", "AVIF"}:
                    expected_frames = getattr(image, "n_frames", None)
                    if type(expected_frames) is not int or expected_frames < 1:
                        raise ValueError(
                            "Raster decoder omitted its declared frame count"
                        )
                    if expected_frames > MAX_IMAGE_FRAMES:
                        raise ValueError("Raster document exceeds its frame limit")
                total = 0
                for index in range(MAX_IMAGE_FRAMES + 1):
                    try:
                        image.seek(index)
                    except EOFError:
                        if expected_frames is not None and index != expected_frames:
                            raise ValueError(
                                "Raster decoder did not return the complete declared frame sequence"
                            ) from None
                        return
                    if index == MAX_IMAGE_FRAMES:
                        raise ValueError("Raster document exceeds its frame limit")
                    stored_size = _dimensions(image)
                    pixels = stored_size[0] * stored_size[1]
                    if min(stored_size) < 1 or pixels > MAX_FRAME_PIXELS:
                        raise ValueError("Raster frame exceeds its decoded pixel limit")
                    total += pixels
                    if total > MAX_DOCUMENT_PIXELS:
                        raise ValueError(
                            "Raster document exceeds its aggregate pixel limit"
                        )
                    orientation = image.getexif().get(274, 1)
                    if type(orientation) is not int or orientation not in range(1, 9):
                        raise ValueError("Raster frame has an invalid EXIF orientation")
                    bits = _encoded_bits(image, data)
                    # TIFF decoding applies orientation and removes its tag. Capture
                    # the stored IFD before load; ImageOps then sees no second rotation.
                    metadata = (
                        metadata_record(image) if image.format == "TIFF" else None
                    )
                    image.load()
                    if metadata is None:
                        metadata = metadata_record(image)
                    display = ImageOps.exif_transpose(image)
                    try:
                        disposal_extent = getattr(image, "dispose_extent", None)
                        record = {
                            "schema_version": "native-image-frame-v1",
                            "decoder": {"name": "Pillow", "version": __version__},
                            "locator": {"frame_index": index},
                            "format": image.format,
                            "stored_size_px": list(stored_size),
                            "displayed_size_px": list(display.size),
                            "source_orientation": orientation,
                            "source_bits_per_sample": bits,
                            "decoded_mode": display.mode,
                            "decoded_bits_per_sample": _decoded_bits(display.mode),
                            "decoded_pixels_sha256": hashlib.sha256(
                                display.tobytes()
                            ).hexdigest(),
                            "decoded_rgba8_sha256": rgba_hash(display),
                            "decoded_pixel_order": "displayed frame after EXIF orientation; animation frames are decoder-composited",
                            "metadata": metadata,
                            "frame_role": "default_image"
                            if image.format == "PNG"
                            and index == 0
                            and image.info.get("default_image")
                            else "frame",
                            "duration_ms": image.info.get("duration"),
                            "loop": image.info.get("loop"),
                            "disposal": getattr(
                                image,
                                "disposal_method",
                                getattr(image, "dispose_op", None),
                            ),
                            "blend": getattr(image, "blend_op", None),
                            "disposal_extent": list(disposal_extent)
                            if disposal_extent is not None
                            else None,
                            "representation_policy": "Decoded frame and decoder-exposed metadata. Original file bytes preserve private fields, high precision, sub-IFDs and layers outside this projection.",
                        }
                        canonical(record)
                        yield record, display
                    finally:
                        display.close()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError(f"Invalid or unsupported raster document: {exc}") from exc


def rgba_hash(image: Image.Image) -> str | None:
    """Supplement native samples with palette/transparent-color interpretation."""
    if image.mode == "LAB":
        return None  # Native samples are preserved; RGB conversion needs a profile.
    with image.convert("RGBA") as rgba:
        return hashlib.sha256(rgba.tobytes()).hexdigest()
