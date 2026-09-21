"""Image assets retain lineage, immutable evidence, wiki bytes and source guards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_pptx_helpers import build_presentation
from tests.native_pptx_picture_helpers import raster, request
from tests.native_workbook_helpers import _call
from tests.unit.test_native_pptx_operations import read_shape


@pytest.fixture
def managed(tmp_path):
    source = tmp_path / "source.pptx"
    source.write_bytes(build_presentation())
    image = tmp_path / "original.png"
    image.write_bytes(raster())
    repository = FileNativeAssetRepository(tmp_path / "store")
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((tmp_path / "store",)),
        presentations=NativePresentation(),
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    picture = _call(service, op="register", source_path=str(image))["asset"]
    item = request(source.read_bytes(), image.read_bytes()).model_dump()
    item["image"] = picture["file_reference"]
    return service, asset, picture, item, source, image


def add(managed):
    service, asset, _, item, _, _ = managed
    return _call(
        service,
        op="add_pptx_pictures",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pptx_pictures=[item],
    )


def test_picture_extract_lineage_and_immutable_file_reference(managed):
    service, asset, image_asset, _, source, image = managed
    result = add(managed)
    current = result["asset"]
    locator = result["operation_result"]["changes"][0]["locator"]
    read = _call(
        service,
        op="read_pptx_picture",
        asset_id=asset["asset_id"],
        revision=current["revision"],
        pptx_locator=locator,
    )
    assert read["image"]["sha256"] == image_asset["revision"]
    assert hashlib.sha256(read["image_png"]).hexdigest() == read["image_sha256"]
    assert "embedded_raster_only" in read["preview_scope"] and "image_bytes" not in read
    extracted = _call(
        service,
        op="extract_pptx_picture",
        asset_id=asset["asset_id"],
        revision=current["revision"],
        pptx_locator=locator,
    )
    child = extracted["asset"]
    assert service.repository.read(child["asset_id"]) == image.read_bytes()
    assert child["revision"] == image_asset["revision"] and child["source"] is None
    initial = service.repository.load(child["asset_id"]).history[0]
    result = service.repository.read_result(child["asset_id"], initial)
    assert result is not None
    assert result.changes[0]["source_reference"] == read["shape_reference"]
    for ref in [
        child["file_reference"],
        image_asset["file_reference"],
        read["shape_reference"],
        asset["file_reference"],
    ]:
        assert _call(service, op="verify", reference=ref)["valid"]
    assert not _call(service, op="verify", reference=asset["file_reference"])[
        "is_current_managed_revision"
    ]
    assert source.read_bytes() == service.repository.read(
        asset["asset_id"], asset["revision"]
    )


def test_picture_wiki_keeps_exact_media_and_source_backup(managed, tmp_path):
    service, asset, _, _, source, image = managed
    result = add(managed)
    current = result["asset"]
    old = source.read_bytes()
    wiki = _call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )
    directory = Path(wiki["output_dir"])
    manifest = json.loads((directory / "manifest.json").read_text())
    media = result["operation_result"]["changes"][0]["media_part"]
    attachment = manifest["part_attachments"][media]["attachment"]
    assert (directory / attachment).read_bytes() == image.read_bytes()
    written = _call(
        service,
        op="writeback",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
        expected_source_sha256=asset["source"]["sha256"],
    )
    assert Path(written["backup_path"]).read_bytes() == old
    assert source.read_bytes() == service.repository.read(asset["asset_id"])


@pytest.mark.parametrize("failure", ["stale", "asset", "archive", "source"])
def test_picture_managed_guards(managed, failure):
    service, asset, image_asset, _, source, _ = managed
    original = source.read_bytes()
    result = add(managed)
    current = result["asset"]
    locator = result["operation_result"]["changes"][0]["locator"]
    ref = read_shape(service, current, locator)["evidence"]
    if failure == "stale":
        ref["revision"] = asset["revision"]
    elif failure == "asset":
        ref["asset_id"] = image_asset["asset_id"]
    elif failure == "archive":
        _call(
            service,
            op="archive",
            asset_id=current["asset_id"],
            expected_revision=current["revision"],
        )
    else:
        source.write_bytes(original + b"human change")
        with pytest.raises(ValueError, match="Source changed"):
            _call(
                service,
                op="writeback",
                asset_id=current["asset_id"],
                expected_revision=current["revision"],
                expected_source_sha256=asset["source"]["sha256"],
            )
        assert source.read_bytes() == original + b"human change"
        return
    with pytest.raises(ValueError):
        _call(
            service,
            op="replace_pptx_pictures",
            asset_id=current["asset_id"],
            expected_revision=current["revision"],
            pptx_picture_edits=[
                {"reference": ref, "image": image_asset["file_reference"]}
            ],
        )
    assert source.read_bytes() == original


def test_concurrent_picture_update_keeps_the_winning_revision(managed, monkeypatch):
    service, asset, _, _item, source, _ = managed
    original = source.read_bytes()
    operation = service.presentations.add_pictures
    winning = []

    def interleave(data, items, sources):
        candidate, report = operation(data, items, sources)
        winning.append(
            service.repository.commit(
                asset["asset_id"], asset["revision"], candidate, report
            ).revision
        )
        return candidate, report

    monkeypatch.setattr(service.presentations, "add_pictures", interleave)
    with pytest.raises(ValueError, match="Stale"):
        add(managed)
    assert service.repository.load(asset["asset_id"]).revision == winning[0]
    assert source.read_bytes() == original
