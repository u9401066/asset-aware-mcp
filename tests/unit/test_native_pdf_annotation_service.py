"""Actual managed annotation history, complete evidence and portable Wiki behavior."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pikepdf
import pytest

from src.application.native_pdf_operations import attach_pdf_evidence
from src.application.native_pdf_wiki import NativePdfWikiContent
from src.domain.citation_format import CitationMetadata, resolve_citation_format
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_pdf_annotation_helpers import catalog, complete, read, update
from tests.native_pdf_helpers import page_reference
from tests.native_workbook_helpers import _call
from tests.unit.test_native_pdf_operations import (
    managed_pdf as _managed_pdf,
)

managed_pdf = _managed_pdf


def test_full_records_metadata_history_selection_noop_and_source_preservation(
    managed_pdf,
):
    service, asset, source = managed_pdf
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    initial = catalog(service, asset)
    before = read(service, asset)
    assert initial["catalog"]["annotation_count"] == 8
    assert (
        asset["capabilities"]["read_pdf_annotations"]
        and asset["capabilities"]["edit_pdf_annotations"]
    )
    ref = before["evidence"]
    selected = _call(
        service, op="read_selection", reference=ref, selection={"pointer": "/contents"}
    )["evidence"]
    changed = update(
        service,
        asset,
        [
            {
                "op": "update",
                "reference": ref,
                "metadata": {"contents": "核對 007 µg -0.50 mg/L", "author": "user"},
            }
        ],
    )
    receipt = complete(service, **changed["review_request"])
    assert (
        receipt["operation_result"]["changes"][0]["after"]["contents"]
        == "核對 007 µg -0.50 mg/L"
    )
    assert changed["operation_result"]["committed"]
    new_record = read(
        service,
        changed["asset"],
        receipt["operation_result"]["changes"][0]["after"]["locator"],
    )
    same = update(
        service,
        changed["asset"],
        [
            {
                "op": "update",
                "reference": new_record["evidence"],
                "metadata": {"contents": new_record["contents"]},
            }
        ],
    )
    assert not same["operation_result"]["committed"]
    assert complete(service, **same["review_request"]) == receipt
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    assert read(service, asset) == before
    assert _call(service, op="verify", reference=ref)["valid"]
    assert not _call(service, op="verify", reference=ref)["is_current_managed_revision"]
    assert _call(service, op="verify", reference=selected)["valid"]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime


def test_complete_create_delete_receipts_and_deleted_historical_reference(managed_pdf):
    service, asset, source = managed_pdf
    changed = update(
        service,
        asset,
        [
            {
                "op": "create",
                "page_reference": page_reference(
                    source.read_bytes(), 1, asset["asset_id"]
                ).model_dump(),
                "appearance": {
                    "kind": "FreeText",
                    "rect": [0.1, 0.4, 0.8, 0.7],
                    "text": "Created 007 µg",
                },
            }
        ],
    )
    receipt = complete(service, **changed["review_request"])
    created = read(
        service,
        changed["asset"],
        receipt["operation_result"]["changes"][0]["after"]["locator"],
    )
    assert created["contents"] == "Created 007 µg"
    deleted = update(
        service,
        changed["asset"],
        [
            {
                "op": "delete",
                "reference": created["evidence"],
                "scope": "annotation_and_owned_popup",
            }
        ],
    )
    final = complete(service, **deleted["review_request"])
    assert final["catalog"]["annotation_count"] == 8
    assert (
        final["operation_result"]["changes"][0]["before"]["contents"]
        == created["contents"]
    )
    assert _call(service, op="verify", reference=created["evidence"])["valid"]


@pytest.mark.parametrize("fault", ["asset", "revision", "hash", "locator", "archived"])
def test_rejected_edits_leave_history_and_source_intact(managed_pdf, fault):
    service, asset, source = managed_pdf
    ref = read(service, asset)["evidence"]
    original = source.read_bytes()
    if fault == "asset":
        ref["asset_id"] = "file_" + "f" * 32
    if fault == "revision":
        ref["revision"] = "0" * 64
    if fault == "hash":
        ref["value_sha256"] = "0" * 64
    if fault == "locator":
        ref["locator"]["object_id"] = 99999
    if fault == "archived":
        _call(
            service,
            op="archive",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
        )
    history = len(service.repository.load(asset["asset_id"]).history)
    with pytest.raises(ValueError):
        update(
            service,
            asset,
            [{"op": "update", "reference": ref, "metadata": {"author": "changed"}}],
        )
    assert len(service.repository.load(asset["asset_id"]).history) == history
    assert source.read_bytes() == original


def test_receipt_size_is_checked_before_commit(managed_pdf, monkeypatch):
    import src.application.native_pdf_annotation_operations as module

    service, asset, _ = managed_pdf
    ref = read(service, asset)["evidence"]
    original = module.annotation_text

    def reject(record):
        if record.get("operation_result") is not None:
            raise ValueError("complete receipt budget exceeded")
        return original(record)

    monkeypatch.setattr(module, "annotation_text", reject)
    with pytest.raises(ValueError, match="receipt budget"):
        update(
            service,
            asset,
            [{"op": "update", "reference": ref, "metadata": {"author": "changed"}}],
        )
    assert len(service.repository.load(asset["asset_id"]).history) == 1


def test_annotated_wiki_keeps_legacy_projection_and_custom_citation_evidence(
    managed_pdf, tmp_path
):
    service, asset, source = managed_pdf
    identity = {
        key: asset[key]
        for key in ("asset_id", "revision", "name", "format", "media_type")
    }
    legacy = NativePdfWikiContent(
        identity, resolve_citation_format({"preset": "source"}), CitationMetadata()
    )
    for item in service.pdfs.decompose(source.read_bytes()):
        attach_pdf_evidence(item["record"], asset["asset_id"], asset["revision"])
        legacy.add_page(item["record"], item["png"])
    legacy_files = legacy.finish(source.read_bytes())
    published = FileNativeWikiPublisher().publish(
        str(tmp_path / "wiki"),
        legacy.snapshot_id,
        legacy_files,
        source_path=str(source),
    )
    old_root = Path(published["output_dir"])
    old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}
    fields = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "output_dir": str(tmp_path / "wiki"),
        "citation_contract": {
            "name": "annotations",
            "inline_template": "批註【{locator}】",
            "reference_template": "{title} | {locator}",
        },
    }
    exported = _call(service, **fields)
    root = Path(exported["output_dir"])
    assert root != old_root and exported["annotation_count"] == 8
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["projection"].startswith("pdf-fields-v1:")
    assert manifest["field_count"] > 0
    assert (root / "fields.jsonl").is_file()
    assert (root / manifest["source_attachment"]).read_bytes() == source.read_bytes()
    records = [
        json.loads(line)
        for line in (root / "annotations.jsonl").read_text().splitlines()
    ]
    assert all(
        _call(service, op="verify", reference=r["evidence"])["valid"] for r in records
    )
    assert all("批註【" in r["citation_presentation"]["inline"] for r in records)
    for record in records:
        loc = record["locator"]
        assert (
            f"p. {loc['page']['page_index'] + 1}"
            in record["citation_presentation"]["inline"]
        )
        assert (
            f"annotation index {loc['annotation_index']}"
            in record["citation_presentation"]["inline"]
        )
        assert (
            f"object {loc['object_id']} {loc['generation']}"
            in record["citation_presentation"]["inline"]
        )
    assert all(
        (root / r["preview_attachment"]).is_file() and (root / r["note"]).is_file()
        for r in records
    )
    before = read(service, asset)
    update(
        service,
        asset,
        [
            {
                "op": "update",
                "reference": before["evidence"],
                "metadata": {"contents": "REVISED"},
            }
        ],
    )
    assert _call(service, **fields)["output_dir"] != exported["output_dir"]
    assert (
        _call(service, **fields, revision=asset["revision"])["output_dir"]
        == exported["output_dir"]
    )
    assert {p.name: p.read_bytes() for p in old_root.iterdir()} == old_files
    note = root / records[0]["note"]
    note.write_text("Human synthesis must survive")
    with pytest.raises(ValueError):
        _call(service, **fields, revision=asset["revision"])
    assert note.read_text() == "Human synthesis must survive"


def test_unannotated_pdf_keeps_identical_legacy_projection(managed_pdf, tmp_path):
    service, _, _ = managed_pdf
    with pikepdf.Pdf.new() as pdf:
        pdf.add_blank_page()
        raw = io.BytesIO()
        pdf.save(raw)
    path = tmp_path / "blank.pdf"
    path.write_bytes(raw.getvalue())
    asset = _call(service, op="register", source_path=str(path))["asset"]
    identity = {
        key: asset[key]
        for key in ("asset_id", "revision", "name", "format", "media_type")
    }
    legacy = NativePdfWikiContent(
        identity, resolve_citation_format({"preset": "source"}), CitationMetadata()
    )
    for item in service.pdfs.decompose(raw.getvalue()):
        attach_pdf_evidence(item["record"], asset["asset_id"], asset["revision"])
        legacy.add_page(item["record"], item["png"])
    expected = legacy.finish(raw.getvalue())
    exported = _call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )
    root = Path(exported["output_dir"])
    assert {p.name: p.read_bytes() for p in root.iterdir()} == expected
    assert (
        json.loads((root / "manifest.json").read_text())["projection"] == "pdf-pages-v1"
    )
    assert hashlib.sha256(path.read_bytes()).hexdigest() == asset["revision"]
