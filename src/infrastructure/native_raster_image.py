"""Bounded raster validation and previews; embedding always uses original bytes."""

from __future__ import annotations

import hashlib
import io
import warnings
from typing import Any

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 16 * 1024 * 1024
MAX_IMAGE_PIXELS = 16_000_000


def inspect_image(data: bytes) -> dict[str, Any]:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Native image must contain 1 byte to 16 MiB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                metadata = _metadata(image, data)
                image.load()  # Validate decoded content as well as container checksums.
        return metadata
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise ValueError(f"Invalid or unsupported native image: {exc}") from exc


def _metadata(image: Image.Image, data: bytes) -> dict[str, Any]:
    if image.format not in {"PNG", "JPEG"}:
        raise ValueError("Native picture sources must be PNG or JPEG")
    if image.width * image.height > MAX_IMAGE_PIXELS:
        raise ValueError("Native image exceeds 16 million decoded pixels")
    if getattr(image, "n_frames", 1) != 1:
        raise ValueError(
            "Animated or multi-frame image needs an explicit frame workflow"
        )
    if image.getexif().get(274, 1) != 1:
        raise ValueError("EXIF-oriented image needs an explicit orientation transform")
    return {
        "format": image.format,
        "extension": "png" if image.format == "PNG" else "jpg",
        "media_type": "image/png" if image.format == "PNG" else "image/jpeg",
        "width_px": image.width,
        "height_px": image.height,
        "color_mode": image.mode,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "icc_profile_sha256": hashlib.sha256(image.info["icc_profile"]).hexdigest()
        if image.info.get("icc_profile")
        else None,
    }


def preview_image(data: bytes, max_size: int) -> bytes:
    if not 64 <= max_size <= 2048:
        raise ValueError("Image preview size must be 64..2048")
    inspect_image(data)
    with Image.open(io.BytesIO(data)) as image:
        image.thumbnail((max_size, max_size))
        converted = image.convert("RGBA")
        output = io.BytesIO()
        converted.save(output, format="PNG")
    png = output.getvalue()
    if len(png) > 3 * 1024 * 1024:
        raise ValueError("Image preview exceeds limit; request a smaller render_size")
    return png
