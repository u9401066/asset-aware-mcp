"""Asymmetric raster fixtures make orientation and frame loss independently visible."""

import io

from PIL import Image, ImageCms, PngImagePlugin


def grid() -> Image.Image:
    image = Image.new("RGB", (12, 8))
    image.putdata(
        [(x * 19, y * 29, ((x + 3 * y) % 11) * 23) for y in range(8) for x in range(12)]
    )
    return image


def encoded(format_name="PNG", orientation=1, **options) -> bytes:
    image = grid()
    exif = Image.Exif()
    exif[274] = orientation
    exif[270] = "Source image"
    exif[315] = "Agent fixture"
    if format_name == "PNG":
        info = PngImagePlugin.PngInfo()
        info.add_itxt("comment", "研究 007 µg; preserve metadata")
        options["pnginfo"] = info
    output = io.BytesIO()
    image.save(output, format=format_name, exif=exif, **options)
    image.close()
    return output.getvalue()


def srgb_profile() -> bytes:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
