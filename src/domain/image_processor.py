"""
Domain Layer - Image Processor

Smart image resizing for Vision Language Models.
Simple approach: specify max_size (longest edge), default 1024.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass

# Default max size - works well for most VLMs
DEFAULT_MAX_SIZE = 1024


@dataclass
class ProcessedImage:
    """Result of image processing."""

    data: bytes
    base64: str
    width: int
    height: int
    original_width: int
    original_height: int
    original_bytes: int
    processed_bytes: int
    quality: int
    resized: bool

    @property
    def compression_ratio(self) -> float:
        """How much smaller the processed image is."""
        if self.processed_bytes == 0:
            return 1.0
        return self.original_bytes / self.processed_bytes

    @property
    def size_reduction_percent(self) -> float:
        """Percentage of size reduction."""
        if self.original_bytes == 0:
            return 0.0
        return (1 - self.processed_bytes / self.original_bytes) * 100


def process_image(
    image_bytes: bytes,
    max_size: int = DEFAULT_MAX_SIZE,
    quality: int = 85,
) -> ProcessedImage:
    """
    Process image for VLM consumption.

    Args:
        image_bytes: Original image bytes
        max_size: Maximum size for longest edge (default 1024)
                  Set to 0 or None to skip resizing (original size)
        quality: JPEG quality 1-100 (default 85)

    Returns:
        ProcessedImage with base64 and metadata

    Example:
        # Default: resize to 1024 max
        result = process_image(img_bytes)

        # Custom size for smaller models
        result = process_image(img_bytes, max_size=512)

        # Original size, just compress
        result = process_image(img_bytes, max_size=0)
    """
    from PIL import Image

    # Load image
    img: Image.Image = Image.open(io.BytesIO(image_bytes))
    original_width, original_height = img.size
    original_bytes = len(image_bytes)

    # Determine if resize needed
    resized = False
    if max_size and max_size > 0:
        longest_edge = max(original_width, original_height)
        if longest_edge > max_size:
            # Calculate new dimensions preserving aspect ratio
            if original_width > original_height:
                new_width = max_size
                new_height = int(original_height * (max_size / original_width))
            else:
                new_height = max_size
                new_width = int(original_width * (max_size / original_height))

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            resized = True

    # Convert to RGB for JPEG (handle RGBA, P modes)
    if img.mode in ("RGBA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # Compress to JPEG
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    processed_bytes = output.getvalue()

    # Convert to base64
    b64 = base64.b64encode(processed_bytes).decode("utf-8")

    return ProcessedImage(
        data=processed_bytes,
        base64=b64,
        width=img.width,
        height=img.height,
        original_width=original_width,
        original_height=original_height,
        original_bytes=original_bytes,
        processed_bytes=len(processed_bytes),
        quality=quality,
        resized=resized,
    )


def process_to_base64(
    image_bytes: bytes,
    max_size: int = DEFAULT_MAX_SIZE,
    quality: int = 85,
) -> tuple[str, int, int]:
    """
    Quick helper: process and return base64 + dimensions.

    Args:
        image_bytes: Original image bytes
        max_size: Maximum longest edge (default 1024, 0=no resize)
        quality: JPEG quality

    Returns:
        Tuple of (base64_string, width, height)
    """
    result = process_image(image_bytes, max_size, quality)
    return result.base64, result.width, result.height
