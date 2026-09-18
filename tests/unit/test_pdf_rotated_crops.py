"""Pixel-level regressions for cropbox offsets and rotated scanned assets."""

from __future__ import annotations

import io
from pathlib import Path

import pymupdf as fitz
import pytest
from PIL import Image

from src.infrastructure.pdf_extractor import PyMuPDFExtractor
from tests.codex_pdf.fixtures import build_pdf, sha256


@pytest.fixture
def extractor(monkeypatch: pytest.MonkeyPatch) -> PyMuPDFExtractor:
    for edge in ("X", "TOP", "BOTTOM"):
        monkeypatch.setenv(f"PYMUPDF_FIGURE_CROP_{edge}_PADDING", "0")
    monkeypatch.setenv("PYMUPDF_FIGURE_CROP_ZOOM", "1")
    return PyMuPDFExtractor()


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("cropped", [False, True])
def test_full_scan_matches_complete_visible_page(
    tmp_path: Path, extractor: PyMuPDFExtractor, rotation: int, cropped: bool
) -> None:
    source = tmp_path / "scan.pdf"
    build_pdf(source, "scanned")
    original = sha256(source)
    with fitz.open(source) as document:
        page = document[0]
        if cropped:
            page.set_cropbox(fitz.Rect(20, 30, 592, 762))
        page.set_rotation(rotation)
        before_rotation, before_cropbox = page.rotation, page.cropbox
        image_bbox = page.get_image_rects(page.get_images()[0][0])[0]
        actual = extractor._render_page_crop(page, image_bbox)
        assert actual is not None
        expected = page.get_pixmap(alpha=False)
        decoded = Image.open(io.BytesIO(actual["image"]))
        assert decoded.size == (expected.width, expected.height)
        assert decoded.tobytes() == expected.samples
        width, height = (572, 732) if cropped else (612, 792)
        assert actual["bbox"] == [0, 0, width, height]
        assert (page.rotation, page.cropbox) == (before_rotation, before_cropbox)
    assert sha256(source) == original


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("cropped", [False, True])
def test_partial_crop_selects_correct_pixels_and_unrotated_locator(
    extractor: PyMuPDFExtractor, rotation: int, cropped: bool
) -> None:
    with fitz.open() as document:
        page = document.new_page(width=300, height=400)
        for y in range(0, 400, 10):
            page.draw_rect(
                fitz.Rect(0, y, 300, y + 10),
                color=None,
                fill=(y / 400, 0.3, 1 - y / 400),
            )
        if cropped:
            page.set_cropbox(fitz.Rect(20, 30, 280, 370))
        page.set_rotation(rotation)
        width, height = (260, 340) if cropped else (300, 400)
        bbox = fitz.Rect(40, 70, 120, 190)
        expected_rect = {
            0: (40, 70, 120, 190),
            90: (height - 190, 40, height - 70, 120),
            180: (width - 120, height - 190, width - 40, height - 70),
            270: (70, width - 120, 190, width - 40),
        }[rotation]
        full = page.get_pixmap(alpha=False)
        expected = Image.frombytes("RGB", (full.width, full.height), full.samples).crop(
            expected_rect
        )
        actual = extractor._render_page_crop(page, bbox)
        assert actual is not None
        decoded = Image.open(io.BytesIO(actual["image"]))
        assert decoded.size == expected.size
        assert decoded.tobytes() == expected.tobytes()
        assert actual["bbox"] == list(bbox)
