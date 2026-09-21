import hashlib
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from src.application.native_document_service import NativeDocumentService
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_image_helpers import encoded, grid
from tests.native_image_service_helpers import frame, update
from tests.native_workbook_helpers import _call
from tests.unit.test_native_image_service import managed_image as _managed_image

managed_image = _managed_image


def export(service, asset, path, **kwargs):
    result = _call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        output_dir=str(path),
        **kwargs,
    )
    root = Path(result["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    for name, declared in manifest["files"].items():
        data = (root / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == declared["sha256"]
        assert len(data) == declared["size_bytes"]
    return root, manifest


def test_native_image_wiki_preserves_legacy_notes_complete_records_and_actual_png(
    managed_image, tmp_path
):
    service, asset, source = managed_image
    legacy = NativeDocumentService(
        service.repository, SpreadsheetFileAdapter(), FileNativeWikiPublisher()
    )
    old_root, old_manifest = export(legacy, asset, tmp_path / "wiki")
    assert old_manifest["representation"] == "opaque_binary"
    (old_root / "curated.md").write_text("human interpretation")
    old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}
    contract = {
        "name": "image-location",
        "inline_template": "[{source_id}|{locator}]",
        "reference_template": "{title}|{locator}",
    }
    root, manifest = export(
        service, asset, tmp_path / "wiki", citation_contract=contract
    )
    assert root != old_root and manifest["projection"] == "image-frames-v1"
    assert manifest["frame_count"] == 1
    assert (root / manifest["source_attachment"]).read_bytes() == source.read_bytes()
    records = [
        json.loads(line) for line in (root / "records.jsonl").read_text().splitlines()
    ]
    record = records[0]
    assert record["evidence"] == frame(service, asset)["evidence"]
    assert "研究 007" in json.dumps(record, ensure_ascii=False)
    assert "frame index 0 (zero-based)" in record["citation_presentation"]["inline"]
    with Image.open(
        io.BytesIO((root / record["preview_attachment"]).read_bytes())
    ) as actual:
        assert (
            actual.tobytes()
            == grid().transpose(Image.Transpose.ROTATE_270).convert("RGBA").tobytes()
        )
    assert "[[" in (root / record["note"]).read_text()
    assert old_files == {p.name: p.read_bytes() for p in old_root.iterdir()}


def test_wiki_receipts_retain_input_files_and_distinguish_repeated_byte_revisions(
    managed_image, tmp_path
):
    service, asset, source = managed_image
    old_root, _ = export(service, asset, tmp_path / "wiki")
    old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}
    ref = frame(service, asset)["evidence"]
    derivative = _call(
        service,
        op="extract_image",
        image_extract={
            "name": "crop.png",
            "reference": ref,
            "region": {"rect": [0.0, 0.0, 0.5, 0.5]},
            "pixel_policy": "preserve_decoded",
            "metadata_policy": "pixels_only",
        },
    )["asset"]
    root, manifest = export(service, derivative, tmp_path / "wiki")
    source_input = next(iter(manifest["image_inputs"]["attachments"].values()))
    assert (root / source_input["attachment"]).read_bytes() == source.read_bytes()
    assert manifest["image_inputs"]["references"] == [ref]
    derivative_ref = frame(service, derivative)["evidence"]
    changed = update(
        service,
        asset,
        derivative,
        [
            {
                "op": "map",
                "before": ref,
                "after": derivative_ref,
                "pixels": "replace",
                "metadata": "replace",
            }
        ],
    )["asset"]
    changed_ref = frame(service, changed)["evidence"]
    current_root, current_manifest = export(service, changed, tmp_path / "wiki")
    assert set(current_manifest["image_inputs"]["attachments"]) == {
        f"{asset['asset_id']}:{asset['revision']}",
        f"{derivative['asset_id']}:{derivative['revision']}",
    }
    restored = update(
        service,
        changed,
        asset,
        [
            {
                "op": "map",
                "before": changed_ref,
                "after": ref,
                "pixels": "replace",
                "metadata": "replace",
            }
        ],
    )["asset"]
    restored_root, restored_manifest = export(service, restored, tmp_path / "wiki")
    assert restored["revision"] == asset["revision"]
    assert restored_root != old_root and restored_root != current_root
    assert restored_manifest["image_operation_sha256"]
    assert old_files == {p.name: p.read_bytes() for p in old_root.iterdir()}
    assert (
        restored_root / restored_manifest["source_attachment"]
    ).read_bytes() == source.read_bytes()


def test_wiki_requires_explicit_unmanaged_color_for_invalid_icc(
    managed_image, tmp_path
):
    service, _, _ = managed_image
    path = tmp_path / "invalid-profile.png"
    path.write_bytes(encoded(icc_profile=b"invalid ICC"))
    asset = _call(service, op="register", source_path=str(path))["asset"]
    with pytest.raises(ValueError, match="ICC"):
        export(service, asset, tmp_path / "bad-wiki")
    assert not (tmp_path / "bad-wiki").exists()
    root, manifest = export(
        service, asset, tmp_path / "wiki", image_color_policy="unmanaged"
    )
    assert manifest["image_color_policy"] == "unmanaged"
    record = json.loads((root / "records.jsonl").read_text().splitlines()[0])
    assert record["rendering"]["color_transform"] == "unmanaged_rgba8"


def test_repeated_composition_inputs_decode_the_source_once_during_export(
    managed_image, tmp_path, monkeypatch
):
    service, asset, source = managed_image
    reference = frame(service, asset)["evidence"]
    created = _call(
        service,
        op="compose_images",
        image_compose={
            "name": "repeated.tif",
            "metadata_policy": "pixels_only",
            "frames": [{"reference": reference, "pixel_policy": "preserve_decoded"}]
            * 16,
        },
    )["asset"]
    calls = []
    original = source.read_bytes()
    for method_name in ("records", "read_frame"):
        method = getattr(service.images, method_name)

        def observe(data, *args, _method=method, **kwargs):
            if data == original:
                calls.append(True)
            return _method(data, *args, **kwargs)

        monkeypatch.setattr(service.images, method_name, observe)
    _, manifest = export(service, created, tmp_path / "wiki")
    assert manifest["frame_count"] == 16
    assert len(manifest["image_inputs"]["references"]) == 1
    assert len(calls) == 1
