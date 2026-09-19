"""Corpus drift, transcription traps and incomplete-region oracles fail visibly."""

import csv
import hashlib
import io
import os
import subprocess
import sys

import pytest
from PIL import Image

from src.domain.native_pdf_region import NativePdfRegionSelector
from src.infrastructure.native_pdf import NativePdf
from tests.native_pdf_helpers import page_reference
from tests.native_pdf_length_helpers import duplicate_length_pdf
from tests.real_pdf.checks import differences, expected_revisions, require_coverage
from tests.real_pdf.corpus import cases, check_source, fetch
from tests.real_pdf.raster import region_image
from tests.real_pdf.run import prompt


def test_real_tables_cover_distinct_document_features_without_prompt_answers(tmp_path):
    nist, nasa = cases()
    assert len(nist["rows"]) == 25 and len(nasa["rows"]) == 34
    assert nist["kind"] == "digital" and nasa["kind"] == "scan_with_ocr"
    assert nist["rows"][18][1] == "51.0 ± 1.5"
    assert nasa["rows"][7][1] == "02:44:16.2*"
    for case in cases():
        assert sum(p["row_count"] for p in case["pages"]) == len(case["rows"])
        assert all(len(r) == len(case["columns"]) for r in case["rows"])
        text = prompt(tmp_path, case)
        assert all(row[1] not in text for row in case["rows"])
        assert "offset/limit" in text and "page_offset" not in text


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
def test_revisions_preserve_every_source_string_and_distinguish_repeated_bytes(case):
    revisions = expected_revisions(case)
    assert len(revisions) == 7 and revisions[0] == revisions[2] == revisions[-1]
    tables = [
        list(csv.reader(io.StringIO(data.decode("utf-8-sig"), newline="")))
        for data in revisions
    ]
    assert tables[0] == [case["columns"], *case["rows"]]
    assert tables[1][1][1] == "__review__"
    assert tables[3][-1] == ["temporary"] * len(case["columns"])
    assert tables[4][-1][-1] == "checked" and tables[5][-1][0] != "temporary"
    assert all(
        data.startswith(b"\xef\xbb\xbf") and data.endswith(b"\r\n")
        for data in revisions
    )


@pytest.mark.parametrize(
    "wrong,right",
    [
        ("51 ± 1.5", "51.0 ± 1.5"),
        ("02:44:16.2", "02:44:16.2*"),
        ("mg/Kg", "mg/kg"),
        ("μg", "µg"),
    ],
)
def test_oracle_rejects_numeric_footnote_case_and_unicode_coercion(wrong, right):
    assert differences([[wrong]], [[right]]) == [
        {"row": 0, "column": 0, "actual": wrong, "expected": right}
    ]
    assert differences([], [[right]])[0]["actual"] is None


@pytest.mark.parametrize("edge", range(4))
def test_region_hash_and_pixels_do_not_excuse_clipped_source_glyphs(edge):
    bounds = [0.2, 0.3, 0.7, 0.8]
    require_coverage([0.1, 0.2, 0.8, 0.9], bounds)
    rect = bounds[:]
    rect[edge] += 0.001 if edge < 2 else -0.001
    with pytest.raises(ValueError, match="clips"):
        require_coverage(rect, bounds)


def test_changed_cached_pdf_fails_before_network_or_parse(tmp_path, monkeypatch):
    case = {**cases()[0], "size_bytes": 8}
    path = tmp_path / case["filename"]
    path.write_bytes(b"%PDF-bad")
    monkeypatch.setattr(
        "httpx.stream", lambda *a, **kw: pytest.fail("Unexpected download")
    )
    with pytest.raises(ValueError, match="SHA-256"):
        fetch(tmp_path, case)
    path.write_bytes(b"different length")
    with pytest.raises(ValueError, match="size"):
        check_source(path, case)


def test_utf8_oracle_survives_a_non_utf8_default_locale():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from tests.real_pdf.corpus import cases; assert cases()[0]['rows'][0][1] == '3.43 \\u00b1 0.13'",
        ],
        env={
            **os.environ,
            "PYTHONUTF8": "0",
            "PYTHONCOERCECLOCALE": "0",
            "LC_ALL": "C",
        },
        check=True,
        capture_output=True,
        timeout=20,
    )


def test_oversized_download_never_publishes_source(tmp_path, monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def raise_for_status(self):
            pass

        def iter_bytes(self):
            yield b"%PDF-oversized"

    monkeypatch.setattr("httpx.stream", lambda *a, **kw: Response())
    case = {**cases()[0], "size_bytes": 4}
    with pytest.raises(ValueError, match="limit"):
        fetch(tmp_path, case)
    assert not list(tmp_path.iterdir())


def test_forged_valid_png_and_hash_do_not_replace_original_source_pixels(tmp_path):
    data = duplicate_length_pdf(b"/Length 4")
    parent = page_reference(data, 0)
    rect = [0.1, 0.1, 0.9, 0.9]
    result = NativePdf().render_region(
        data, parent.locator, NativePdfRegionSelector(rect=rect), 128
    )
    ref = {
        "asset_id": parent.asset_id,
        "revision": parent.revision,
        "parent": parent.model_dump(),
        "selector": {"rect": rect},
    }
    path = (
        tmp_path
        / "data"
        / "native-assets"
        / parent.asset_id
        / "revisions"
        / parent.revision
    )
    path.parent.mkdir(parents=True)
    path.write_bytes(data)
    png = result["image_png"]
    proof = region_image(
        tmp_path, ref, {"image_sha256": hashlib.sha256(png).hexdigest()}, 128, png
    )
    assert proof["exact_direct_source_pixels"]
    assert proof["full_page_crop_mean_channel_difference"] == 0
    image = Image.open(io.BytesIO(png)).convert("RGB")
    image.putpixel((50, 50), (0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    forged = buffer.getvalue()
    with pytest.raises(ValueError, match="source rendering"):
        region_image(
            tmp_path,
            ref,
            {"image_sha256": hashlib.sha256(forged).hexdigest()},
            128,
            forged,
        )
