"""Explicit color management and bounded RGBA8 previews."""

from __future__ import annotations

import hashlib
import io
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageCms, __version__

if TYPE_CHECKING:
    from src.domain.native_image import ImageColorPolicy


def _rgba(
    image: Image.Image, color_policy: ImageColorPolicy
) -> tuple[Image.Image, str]:
    if color_policy not in {"embedded_to_srgb", "unmanaged"}:
        raise ValueError("Unknown raster preview color policy")
    profile = image.info.get("icc_profile")
    if color_policy == "embedded_to_srgb" and profile:
        try:
            result = ImageCms.profileToProfile(
                image,
                io.BytesIO(profile),
                ImageCms.createProfile("sRGB"),
                outputMode="RGBA",
            )
            if result is None:
                raise ValueError("ICC transformation did not produce an image")
        except (ImageCms.PyCMSError, OSError, ValueError) as exc:
            raise ValueError(
                "Embedded ICC preview transform failed; inspect metadata before explicitly choosing unmanaged color"
            ) from exc
        return result, "embedded_icc_to_srgb"
    return image.convert("RGBA"), "unmanaged_rgba8"


def _preview(
    image: Image.Image,
    size: int,
    color_policy: ImageColorPolicy,
    bounds: tuple[int, int, int, int] | None = None,
) -> dict[str, Any]:
    if type(size) is not int or not 64 <= size <= 2048:
        raise ValueError("Raster preview size must be 64..2048")
    rgba, color_transform = _rgba(image, color_policy)
    try:
        if bounds is not None:
            cropped = rgba.crop(bounds)
            rgba.close()
            rgba = cropped
        rgba.thumbnail((size, size), Image.Resampling.LANCZOS)
        rgba.info.clear()  # Do not attach source CMYK/other profiles to RGBA pixels.
        output = io.BytesIO()
        rgba.save(output, format="PNG")
        png = output.getvalue()
        if len(png) > 3 * 1024 * 1024:
            raise ValueError(
                "Raster preview exceeds its output limit; request a smaller size"
            )
        return {
            "png": png,
            "width_px": rgba.width,
            "height_px": rgba.height,
            "png_sha256": hashlib.sha256(png).hexdigest(),
            "rendering": {
                "engine": "Pillow",
                "version": __version__,
                "color_transform": color_transform,
                "precision": "RGBA8 preview; no automatic HDR intensity scaling",
            },
        }
    finally:
        rgba.close()
