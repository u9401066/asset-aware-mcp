"""Independent full-page raster crops, source identity and portable region evidence."""

import hashlib
import io
import json
from copy import deepcopy
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_pdf_region import NativePdfRegionSelector
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_pdf_process import ProcessNativePdf
from tests.native_derivation_helpers import pair, record, service_at
from tests.native_pdf_helpers import build_pdf, page_reference, rewrite
from tests.native_workbook_helpers import _call


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("offset", [False, True])
@pytest.mark.parametrize("unit", [1, 2])
def test_region_pixels_match_independent_full_page_crop(rotation, offset, unit):
    def geometry(pdf):
        page = pdf.pages[0]
        page.obj.Rotate = rotation
        page.obj.UserUnit = unit
        if offset:
            page.obj.MediaBox = [-40, -60, 360, 440]
            page.obj.CropBox = [-20, -20, 340, 420]

    data = rewrite(build_pdf(), geometry)
    ref = page_reference(data, 0)
    # Independent oracle: raster the WHOLE page at exactly 2x, then crop pixels.
    # This never calls the region adapter, its clip math or its reported bounds.
    with pymupdf.open(stream=data, filetype="pdf") as pdf:
        pix = pdf[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False, annots=True)
        full = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    expected = full.crop(
        (pix.width // 4, pix.height // 4, pix.width * 3 // 4, pix.height * 3 // 4)
    )
    result = NativePdf().render_region(
        data,
        ref.locator,
        NativePdfRegionSelector(rect=[0.25, 0.25, 0.75, 0.75]),
        max(pix.width, pix.height) // 2,
    )
    actual = Image.open(io.BytesIO(result["image_png"]))
    assert actual.size == expected.size
    assert actual.tobytes() == expected.tobytes()
    assert hashlib.sha256(data).hexdigest() == ref.revision
    assert result["rendering"]["rotation"] == rotation
    assert result["rendering"]["annotations"] == "included"


@pytest.mark.parametrize(
    "rect",
    [
        [0, 0, 0, 1],
        [0, 1, 1, 0],
        [-0.01, 0, 1, 1],
        [0, 0, 1.01, 1],
        [0, 0, float("nan"), 1],
        [0, 0, float("inf"), 1],
        [0, 0, True, 1],
        [0, 0, 1],
        [0, 0, "1", 1],
    ],
)
def test_selector_rejects_invalid_geometry_without_clipping(rect):
    with pytest.raises(ValueError):
        NativePdfRegionSelector(rect=rect)


def test_tiny_region_and_changed_page_locator_rejected():
    data = build_pdf()
    ref = page_reference(data, 0)
    with pytest.raises(ValueError, match=r"small|coordinates"):
        NativePdf().render_region(
            data,
            ref.locator,
            NativePdfRegionSelector(rect=[0.5, 0.5, 0.50000000001, 0.50000000001]),
            2048,
        )
    bad = ref.locator.model_copy(update={"object_id": ref.locator.object_id + 1})
    with pytest.raises(ValueError):
        NativePdf().render_region(
            data, bad, NativePdfRegionSelector(rect=[0, 0, 1, 1]), 128
        )


def region_source(tmp_path):
    service = service_at(tmp_path)
    source = tmp_path / "source.pdf"
    data = build_pdf()
    source.write_bytes(data)
    asset = _call(service, op="register", source_path=str(source))["asset"]
    parent = page_reference(data, 0, asset["asset_id"]).model_dump(mode="json")
    region = _call(
        service,
        op="read_pdf_region",
        reference=parent,
        pdf_region={"rect": [0.1, 0.1, 0.8, 0.8]},
        render_size=128,
    )
    assert region["success"]
    return service, source, asset, parent, region


def test_resolution_identity_history_and_tampering(tmp_path):
    service, source, asset, parent, result = region_source(tmp_path)
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    ref = result["region"]["evidence"]
    larger = _call(service, op="read_pdf_region", reference=ref, render_size=256)
    assert larger["region"] == result["region"]
    assert larger["image_sha256"] != result["image_sha256"]
    assert not larger["source_written"]
    assert _call(service, op="verify", reference=ref)["valid"]
    assert len(service.repository.load(asset["asset_id"]).history) == 1
    for field in ("value_sha256", "parent", "selector"):
        bad = deepcopy(ref)
        if field == "value_sha256":
            bad[field] = "0" * 64
        elif field == "parent":
            bad[field]["value_sha256"] = "0" * 64
        else:
            bad[field]["rect"][0] = 0.2
        assert not _call(service, op="verify", reference=bad)["valid"]
        with pytest.raises(ValueError, match="integrity"):
            _call(service, op="read_pdf_region", reference=bad)
    with pytest.raises(ValueError, match="override"):
        _call(
            service,
            op="read_pdf_region",
            reference=ref,
            pdf_region={"rect": [0, 0, 1, 1]},
        )
    with pytest.raises(ValueError, match="explicit"):
        _call(service, op="read_pdf_region", reference=parent)
    changed = _call(
        service,
        op="update_pdf",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pdf_edits=[{"reference": parent, "rotation": 90}],
    )
    assert changed["success"]
    proof = _call(service, op="verify", reference=ref)
    assert proof["valid"] and not proof["is_current_managed_revision"]
    historical = _call(service, op="read_pdf_region", reference=ref, render_size=128)
    assert historical["region"] == result["region"]
    assert historical["image_png"] == result["image_png"]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime


@pytest.mark.parametrize("selection", [False, True])
@pytest.mark.parametrize("academic", [False, True])
def test_derivation_wiki_retains_regions_and_correct_source_metadata(
    tmp_path, selection, academic
):
    service, source, _, _, result = region_source(tmp_path)
    target, claim = pair(service)
    ref = result["region"]["evidence"]
    if selection:
        selected = _call(
            service,
            op="read_selection",
            reference=ref,
            selection={"pointer": "/selector/rect"},
        )
        claim["sources"] = [selected["evidence"]]
    else:
        claim["sources"] = [ref]
    assert record(service, target, claim)["success"]
    wiki_request = {
        "op": "export_wiki",
        "asset_id": target["asset_id"],
        "output_dir": str(tmp_path / "wiki"),
        "citation_contract": {"preset": "author-year"}
        if academic
        else {
            "inline_template": "({source_id}: {locator})",
            "reference_template": "{title}",
        },
        "citation_metadata": {
            "authors": "Target author",
            "year": "2026",
            "title": "Target title",
        },
    }
    wiki = _call(service, **wiki_request)
    root = Path(wiki["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    region = next(iter(manifest["derivations"]["region_records"].values()))
    record_path = root / region["record_file"]
    stored = json.loads(record_path.read_text())
    assert stored["evidence"] == ref
    assert (root / stored["source_attachment"]).read_bytes() == source.read_bytes()
    png = (root / region["preview_attachment"]).read_bytes()
    assert hashlib.sha256(png).hexdigest() == stored["preview_sha256"]
    assert not stored["citation_metadata"]["authors"]
    if academic:
        assert "authors" in stored["citation_unavailable"]
        assert "citation_presentation" not in stored
    else:
        presentation = stored["citation_presentation"]
        assert "displayed CropBox fractions" in presentation["inline"]
        assert presentation["reference"] == "source.pdf"
    note = (root / region["note"]).read_text()
    assert region["preview_attachment"] in note
    assert "Target author" not in note
    assert _call(service, **wiki_request)["output_dir"] == str(root)
    # Existing output is immutable, even when it was curated by a human.
    record_path.write_text("human curation")
    with pytest.raises(ValueError):
        _call(service, **wiki_request)
    assert record_path.read_text() == "human curation"


def test_region_worker_and_public_contract_budget(tmp_path):
    _, source, _, parent, _ = region_source(tmp_path)
    data = source.read_bytes()
    locator = page_reference(data, 0).locator
    selector = NativePdfRegionSelector(rect=[0, 0, 0.5, 0.5])
    assert ProcessNativePdf().render_region(
        data, locator, selector, 128
    ) == NativePdf().render_region(data, locator, selector, 128)
    request = NativeDocumentRequest(
        op="read_pdf_region", reference=parent, pdf_region={"rect": [0, 0, 1, 1]}
    )
    assert request.pdf_region.rect == [0, 0, 1, 1]


def test_actual_agent_image_audit_rejects_shift_even_with_updated_hash(tmp_path):
    from PIL import ImageChops

    from tests.codex_pdf_regions.audit import region_image

    service, _, asset, _, result = region_source(tmp_path)
    ref = result["region"]["evidence"]
    path = (
        tmp_path
        / "data"
        / "native-assets"
        / asset["asset_id"]
        / "revisions"
        / asset["revision"]
    )
    path.parent.mkdir(parents=True)
    path.write_bytes(service.repository.read(asset["asset_id"], asset["revision"]))
    region_image(tmp_path, ref, result, 128, result["image_png"])
    image = Image.open(io.BytesIO(result["image_png"]))
    shifted = ImageChops.offset(image, 1, 0)
    stream = io.BytesIO()
    shifted.save(stream, format="PNG")
    changed = stream.getvalue()
    with pytest.raises(ValueError, match="independent direct"):
        region_image(
            tmp_path,
            ref,
            {"image_sha256": hashlib.sha256(changed).hexdigest()},
            128,
            changed,
        )
