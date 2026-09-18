"""Managed tables enforce version/CAS guards and retain immutable table evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_pptx_helpers import build_presentation
from tests.native_pptx_table_helpers import table_addition
from tests.native_workbook_helpers import _call
from tests.unit.test_native_pptx_operations import read_shape


@pytest.fixture
def managed(tmp_path):
    source = tmp_path / "source.pptx"
    source.write_bytes(build_presentation())
    repository = FileNativeAssetRepository(tmp_path / "store")
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((tmp_path / "store",)),
        presentations=NativePresentation(),
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    item = table_addition(source.read_bytes()).model_dump()
    return service, asset, item, source


def add(managed):
    service, asset, item, _ = managed
    return _call(
        service,
        op="add_pptx_tables",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pptx_tables=[item],
    )


def test_table_evidence_wiki_and_source_backup(managed, tmp_path):
    service, asset, _, source = managed
    old = source.read_bytes()
    result = add(managed)
    current = result["asset"]
    locator = result["operation_result"]["changes"][0]["locator"]
    record = read_shape(service, current, locator)
    assert (
        record["table"]["rows"][1]["cells"][1]["paragraphs"][0]["items"][0]["text"]
        == "007"
    )
    assert _call(service, op="verify", reference=record["evidence"])["valid"]
    wiki = _call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )
    directory = Path(wiki["output_dir"])
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["projection"] == "pptx-shapes-v1"
    assert (
        directory / manifest["source_attachment"]
    ).read_bytes() == service.repository.read(asset["asset_id"])
    assert source.read_bytes() == old
    written = _call(
        service,
        op="writeback",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
        expected_source_sha256=asset["source"]["sha256"],
    )
    assert Path(written["backup_path"]).read_bytes() == old
    assert source.read_bytes() == service.repository.read(asset["asset_id"])
    deleted = _call(
        service,
        op="delete_pptx_shapes",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
        pptx_shape_refs=[record["evidence"]],
    )
    assert deleted["success"]
    proof = _call(service, op="verify", reference=record["evidence"])
    assert proof["valid"] and not proof["is_current_managed_revision"]


@pytest.mark.parametrize(
    "failure", ["stale", "archived", "bad_container", "second_bad"]
)
def test_table_failure_never_publishes_partial_revision(managed, failure):
    service, asset, item, source = managed
    if failure == "archived":
        _call(
            service,
            op="archive",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
        )
    if failure == "stale":
        add(managed)
    if failure == "bad_container":
        item["container"]["slide_id"] = "999"
    batch = [item]
    if failure == "second_bad":
        batch += [{**item, "container": {**item["container"], "slide_id": "999"}}]
    before = service.repository.load(asset["asset_id"])
    with pytest.raises(ValueError):
        _call(
            service,
            op="add_pptx_tables",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pptx_tables=batch,
        )
    after = service.repository.load(asset["asset_id"])
    assert after.revision == before.revision and len(after.history) == len(
        before.history
    )
    assert source.read_bytes() == service.repository.read(
        asset["asset_id"], asset["revision"]
    )


def test_table_interleaved_commit_keeps_winning_revision(managed, monkeypatch):
    service, asset, _item, source = managed
    original = service.presentations.add_tables

    def interleaved(data, items):
        updated, checks = original(data, items)
        service.repository.commit(asset["asset_id"], asset["revision"], updated, checks)
        return updated, checks

    monkeypatch.setattr(service.presentations, "add_tables", interleaved)
    with pytest.raises(ValueError, match=r"revision|changed|Stale|stale"):
        add(managed)
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    assert source.read_bytes() == service.repository.read(
        asset["asset_id"], asset["revision"]
    )
