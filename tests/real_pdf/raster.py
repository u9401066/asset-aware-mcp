"""Exact source-render pixels and explicit scan resampling diagnostics."""

import io

import pymupdf
from PIL import Image, ImageChops, ImageStat

from tests.codex_native_pdf.trace import digest
from tests.codex_pdf.trace import require


def region_image(workspace, reference, result, size, png):
    path = (
        workspace
        / "data"
        / "native-assets"
        / reference["asset_id"]
        / "revisions"
        / reference["revision"]
    )
    require(
        digest(path.read_bytes()) == reference["revision"], "Wrong region source bytes"
    )
    require(digest(png) == result["image_sha256"], "Region PNG hash mismatch")
    with pymupdf.open(path) as pdf:
        page = pdf[reference["parent"]["locator"]["page_index"]]
        left, top, right, bottom = reference["selector"]["rect"]
        clip = pymupdf.Rect(
            left * page.rect.width,
            top * page.rect.height,
            right * page.rect.width,
            bottom * page.rect.height,
        )
        clip.transform(pymupdf.Identity)
        scale = size / max(clip.width, clip.height)
        matrix = pymupdf.Matrix(scale, scale)
        bounds = (clip * matrix).irect
        require(
            max(page.rect.width, page.rect.height) * scale < 8000,
            "Corpus raster budget exceeded",
        )
        direct = page.get_pixmap(
            matrix=matrix, clip=clip, colorspace=pymupdf.csRGB, alpha=False, annots=True
        )
        actual = Image.open(io.BytesIO(png)).convert("RGB")
        require(
            actual.size
            == (bounds.width, bounds.height)
            == (direct.width, direct.height)
            and actual.tobytes() == direct.samples,
            "Delivered region differs from independent direct source rendering",
        )
        full = page.get_pixmap(
            matrix=matrix, colorspace=pymupdf.csRGB, alpha=False, annots=True
        )
        expected = Image.frombytes("RGB", (full.width, full.height), full.samples).crop(
            tuple(bounds)
        )
        difference = ImageChops.difference(actual, expected)
        return {
            "exact_direct_source_pixels": True,
            "full_page_crop_mean_channel_difference": max(
                ImageStat.Stat(difference).mean
            ),
            "full_page_crop_sha256": digest(expected.tobytes()),
            "full_page_comparison_role": "diagnostic; clipped scans may use different resampling",
            "renderer": pymupdf.VersionBind,
        }
