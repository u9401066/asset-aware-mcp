"""Preview identity, unavailable converters, bounded output and process cleanup."""

from __future__ import annotations

import hashlib
import io
import os
import sys
import time

import pytest
from PIL import Image

from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_pptx_slides import NativePptxSlideKey
from src.infrastructure import native_office_process as office
from src.infrastructure import native_pptx_render as rendering
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_pptx_package import NativePptxPackage
from tests.native_pptx_render_helpers import colored_deck
from tests.native_workbook_helpers import _call, _replace
from tests.unit.test_native_pptx_operations import managed as managed


def keys(data):
    return [NativePptxSlideKey(**key) for key in NativePptxPackage(data).slides]


def test_raw_part_identity_survives_reorder_and_hidden_slide():
    data = colored_deck()
    order = list(reversed(keys(data)))
    updated, _ = NativePresentation().reorder_slides(data, order)
    assert rendering.rendering_source(updated, order[0]) == (0, 3, False)
    assert rendering.rendering_source(updated, order[1]) == (1, 3, True)
    assert order[0].part.endswith("slide3.xml")
    wrong = NativePptxSlideKey(slide_id=order[0].slide_id, part=order[1].part)
    with pytest.raises(ValueError, match="identity"):
        rendering.rendering_source(updated, wrong)


@pytest.mark.parametrize(
    "replacement,pattern",
    [
        ({"ppt/media/danger.svg": b"<svg/>"}, "SVG"),
        (
            {
                "ppt/presProps.xml": b'<p:presentationPr xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:showPr><p:sldRg st="1" end="1"/></p:showPr></p:presentationPr>'
            },
            "ranges",
        ),
        (
            {
                "ppt/_rels/linked.xml.rels": b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="r1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="file:///private/image.png" TargetMode="External"/></Relationships>'
            },
            "external",
        ),
    ],
)
def test_rendering_rejects_unsupported_resource_or_show_mapping(replacement, pattern):
    data = colored_deck()
    with pytest.raises(ValueError, match=pattern):
        rendering.rendering_source(_replace(data, replacement), keys(data)[0])


def test_hyperlinks_do_not_block_static_preview(managed):
    _, _, source = managed
    data = source.read_bytes()
    assert rendering.rendering_source(data, keys(data)[0]) == (0, 2, False)


def test_preview_requires_explicit_revision_and_slide_key():
    base = {
        "op": "render_pptx_slide",
        "asset_id": "file_" + "a" * 32,
        "revision": "b" * 64,
        "pptx_slide_key": {"slide_id": "256", "part": "ppt/slides/slide1.xml"},
    }
    assert NativeDocumentRequest(**base).render_size == 1024
    for field in ("revision", "pptx_slide_key"):
        with pytest.raises(ValueError, match="Missing"):
            NativeDocumentRequest(**{k: v for k, v in base.items() if k != field})


def test_historical_preview_never_reads_current_or_writes_source(managed):
    service, asset, source = managed
    data = source.read_bytes()
    key = keys(data)[0]

    class Renderer:
        def render(self, actual, slide, size):
            assert actual == data and slide == key and size == 640
            return {"image_png": b"PNG"}

    service.pptx_operations.renderer = Renderer()
    service.pptx_renderer = service.pptx_operations.renderer
    contract = _call(service, op="contract", for_op="render_pptx_slide")
    assert contract["pptx_rendering"]["configured"] is True
    assert "render_pptx_slide" in contract["formats"]["pptx"]
    updated = _call(
        service,
        op="reorder_pptx_slides",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pptx_slide_order=[k.model_dump() for k in reversed(keys(data))],
    )
    assert updated["asset"]["revision"] != asset["revision"]
    result = _call(
        service,
        op="render_pptx_slide",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        pptx_slide_key=key.model_dump(),
        render_size=640,
    )
    assert result["inspected_revision"] == hashlib.sha256(data).hexdigest()
    assert result["source_written"] is False and source.read_bytes() == data


@pytest.fixture
def fake_conversion(monkeypatch):
    monkeypatch.setattr(rendering, "office_binary", lambda: "office")
    calls = []

    def run(command, directory, timeout):
        calls.append((command, directory))
        if "--version" in command:
            return "LibreOffice test-renderer"
        (directory / "source.pdf").write_bytes(b"%PDF-placeholder")
        return ""

    monkeypatch.setattr(rendering, "run_office", run)

    class Pdf:
        def __init__(self, timeout):
            assert timeout > 0

        def inspect(self, data):
            return {
                "page_count": 3,
                "pages": [
                    {"locator": {"page_index": i, "object_id": i + 3, "generation": 0}}
                    for i in range(3)
                ],
            }

        def render(self, data, locator, size):
            assert locator.page_index == 1 and size == 640
            out = io.BytesIO()
            Image.new("RGB", (640, 480), "green").save(out, "PNG")
            return out.getvalue()

    monkeypatch.setattr(rendering, "ProcessNativePdf", Pdf)
    return calls, run, Pdf


def test_full_preview_metadata_and_private_cleanup(fake_conversion):
    calls, _, _ = fake_conversion
    data = colored_deck()
    result = rendering.LibreOfficePresentationRenderer().render(
        data, keys(data)[1], 640
    )
    assert result["hidden"] is True and result["slide_index"] == 1
    assert result["image_sha256"] == hashlib.sha256(result["image_png"]).hexdigest()
    assert "verdict" in result["limitations"][-1]
    assert all(not directory.exists() for _, directory in calls)


@pytest.mark.parametrize(
    "fault,pattern",
    [
        ("missing", "no slide PDF"),
        ("count", "page count"),
        ("large", "byte limit"),
        ("source", "temporary source"),
        ("version", "renderer version"),
    ],
)
def test_bad_converter_output_fails_and_cleans_up(
    fake_conversion, monkeypatch, fault, pattern
):
    calls, run, pdf = fake_conversion

    def broken(command, directory, timeout):
        output = run(command, directory, timeout)
        if "--version" in command:
            return "unidentified" if fault == "version" else output
        if fault == "missing":
            (directory / "source.pdf").unlink()
        if fault == "source":
            (directory / "source.pptx").write_bytes(b"changed")
        return output

    monkeypatch.setattr(rendering, "run_office", broken)
    if fault == "count":
        monkeypatch.setattr(pdf, "inspect", lambda *_: {"page_count": 2})
    if fault == "large":
        monkeypatch.setattr(rendering, "MAX_NATIVE_BYTES", 1)
    data = colored_deck()
    with pytest.raises(ValueError, match=pattern):
        rendering.LibreOfficePresentationRenderer().render(data, keys(data)[1], 640)
    assert all(not directory.exists() for _, directory in calls)


def test_missing_or_invalid_office_binary(monkeypatch):
    monkeypatch.setenv("LIBREOFFICE_BIN", "/absent/impress")
    monkeypatch.setattr(office.shutil, "which", lambda _: None)
    with pytest.raises(ValueError, match="LIBREOFFICE_BIN"):
        office.office_binary()
    monkeypatch.delenv("LIBREOFFICE_BIN")
    with pytest.raises(ValueError, match="with Impress"):
        office.office_binary()


def test_office_failure_and_timeout(tmp_path):
    with pytest.raises(ValueError, match="unsuccessfully"):
        office.run_office([sys.executable, "-c", "raise SystemExit(7)"], tmp_path, 5)
    with pytest.raises(ValueError, match="time limit"):
        office.run_office(
            [sys.executable, "-c", "import time; time.sleep(10)"], tmp_path, 0.1
        )


def test_noisy_converter_has_bounded_diagnostics(tmp_path):
    with pytest.raises(ValueError, match="output limit"):
        office.run_office([sys.executable, "-c", "print('x'*70000)"], tmp_path, 5)


@pytest.mark.skipif(os.name != "posix", reason="POSIX process group assertion")
def test_timeout_kills_converter_descendants(tmp_path):
    marker = tmp_path / "escaped-child"
    child = "import time; from pathlib import Path; time.sleep(.7); Path('escaped-child').touch()"
    parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(20)"
    with pytest.raises(ValueError, match="time limit"):
        office.run_office([sys.executable, "-c", parent], tmp_path, 0.2)
    time.sleep(0.8)
    assert not marker.exists()
