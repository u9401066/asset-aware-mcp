"""Persisted PDF receipts bind exact historical workbooks and never migrate."""

import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from src.application.native_document_service import NativeDocumentService
from src.application.native_schema import request_schema
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_pdf import NativePdfCreate
from src.domain.native_rendition import NativeWorkbookRendition
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_workbook_helpers import _call
from tests.native_workbook_render_helpers import rendered_workbook


@pytest.fixture
def rendition(tmp_path):
    source = tmp_path / "source.xlsx"
    source.write_bytes(rendered_workbook())
    repository = FileNativeAssetRepository(tmp_path / "assets")
    pdf, _ = NativePdf().create(
        NativePdfCreate(name="a.pdf", pages=[{"blank": {}}]), {}
    )

    class Renderer:
        def __init__(self):
            self.inputs = []

        def convert(self, data, request):
            self.inputs.append(data)
            return pdf, {
                "rendered_pdf_sha256": hashlib.sha256(pdf).hexdigest(),
                "page_count": 1,
                "mode": request.mode,
                "source_copy_unchanged": True,
            }

    renderer = Renderer()
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        pdfs=NativePdf(),
        workbook_renderer=renderer,
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source, renderer


def create(service, asset, **kwargs):
    return _call(
        service,
        op="create_workbook_rendition",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        workbook_rendition={"mode": "print", "calculation": "prefer_cache", **kwargs},
    )


def read(service, asset):
    chunks, offset, digest = [], 0, None
    while True:
        result = _call(
            service,
            op="read_rendition",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            text_offset=offset,
            text_limit=71,
        )
        assert len(json.dumps(result, ensure_ascii=False)) < 10000
        assert result["excerpt_char_range"][0] == offset
        if digest is not None:
            assert digest == result["text_sha256"]
        digest = result["text_sha256"]
        chunks.append(result["text_excerpt"])
        offset = result["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


def test_explicit_revision_and_policies_in_runtime_and_schema():
    request = {
        "op": "create_workbook_rendition",
        "asset_id": "file_" + "a" * 32,
        "revision": "b" * 64,
        "workbook_rendition": {"mode": "whole_sheet", "calculation": "recalculate"},
    }
    validator = Draft202012Validator(request_schema(request["op"]))
    validator.validate(request)
    NativeDocumentRequest.model_validate(request)
    for field in ("revision", "workbook_rendition"):
        bad = {k: v for k, v in request.items() if k != field}
        assert not validator.is_valid(bad)
        with pytest.raises(ValueError):
            NativeDocumentRequest.model_validate(bad)
    for options in (
        {"mode": "print"},
        {"calculation": "recalculate"},
        {"mode": "auto", "calculation": "prefer_cache"},
    ):
        bad = {**request, "workbook_rendition": options}
        assert not validator.is_valid(bad)
        with pytest.raises(ValueError):
            NativeDocumentRequest.model_validate(bad)
    for name in ("a.xlsx", "../a.pdf", "a\\b.pdf", "C:a.pdf", "a\x00.pdf"):
        with pytest.raises(ValueError):
            NativeWorkbookRendition(name=name, mode="print", calculation="prefer_cache")


def test_historical_source_and_pdf_receipt_remain_immutable(rendition):
    service, asset, source, renderer = rendition
    data, mtime = source.read_bytes(), source.stat().st_mtime_ns
    current = _call(
        service,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "First", "cell": "A1", "value": "CHANGED"}],
    )["asset"]
    before = service.repository.load(asset["asset_id"]).model_dump()
    created = create(service, asset)
    pdf_asset = created["asset"]
    assert pdf_asset["asset_id"] != asset["asset_id"] and pdf_asset["source"] is None
    assert renderer.inputs == [data]
    assert service.repository.load(asset["asset_id"]).model_dump() == before
    assert source.read_bytes() == data and source.stat().st_mtime_ns == mtime
    receipt = read(service, pdf_asset)
    assert receipt["changes"][0]["source_reference"] == asset["file_reference"]
    assert set(receipt["review_required"]) == {
        "semantic_accuracy",
        "rendered_layout",
        "formula_results",
    }
    assert current["revision"] != asset["revision"]
    assert len(renderer.inputs) == 1  # Reading every receipt page never reconverts.
    page = _call(
        service,
        op="read_pdf",
        asset_id=pdf_asset["asset_id"],
        revision=pdf_asset["revision"],
    )["pages"][0]
    record = _call(
        service,
        op="read_pdf_page",
        asset_id=pdf_asset["asset_id"],
        revision=pdf_asset["revision"],
        pdf_locator=page["locator"],
    )
    changed = _call(
        service,
        op="update_pdf",
        asset_id=pdf_asset["asset_id"],
        expected_revision=pdf_asset["revision"],
        pdf_edits=[{"reference": record["page"]["evidence"], "rotation": 90}],
    )["asset"]
    with pytest.raises(ValueError, match="creation revision"):
        read(service, changed)
    assert read(service, pdf_asset) == receipt


def test_unconfigured_and_wrong_format_do_not_create_assets(rendition):
    service, asset, _, _ = rendition
    created = create(service, asset)["asset"]
    before = service.repository.list_assets(0, 100)
    with pytest.raises(ValueError, match="XLSX"):
        create(service, created)
    service.rendition_operations.renderer = None
    contract = _call(service, op="contract", for_op="create_workbook_rendition")
    assert not contract["workbook_rendering"]["configured"]
    assert "create_workbook_rendition" not in contract["formats"]["xlsx"]
    with pytest.raises(ValueError, match="not configured"):
        create(service, asset)
    assert read(service, created)
    assert service.repository.list_assets(0, 100) == before


def test_oversized_receipt_rejects_before_creating_asset(rendition, monkeypatch):
    from src.application import native_rendition_operations

    service, asset, _, _ = rendition
    before = service.repository.list_assets(0, 100)
    monkeypatch.setattr(native_rendition_operations, "MAX_RENDITION_RECEIPT_BYTES", 10)
    with pytest.raises(ValueError, match="budget"):
        create(service, asset)
    assert service.repository.list_assets(0, 100) == before


def test_wiki_retains_exact_historical_input_and_receipt(rendition, tmp_path):
    service, asset, source, renderer = rendition
    pdf = create(service, asset)["asset"]
    _call(
        service,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "First", "cell": "B2", "kind": "formula", "value": "=2+3"}],
    )
    exporter = NativeDocumentService(
        service.repository,
        service.spreadsheets,
        FileNativeWikiPublisher((service.repository.root,)),
        pdfs=NativePdf(),
    )
    request = {
        "op": "export_wiki",
        "asset_id": pdf["asset_id"],
        "revision": pdf["revision"],
        "output_dir": str(tmp_path / "wiki"),
    }
    result = _call(exporter, **request)
    folder = Path(result["output_dir"])
    manifest = json.loads((folder / "manifest.json").read_text())
    record = manifest["rendition"]
    assert record["source_reference"] == asset["file_reference"]
    assert (folder / record["source_attachment"]).read_bytes() == source.read_bytes()
    assert json.loads((folder / "rendition.json").read_text()) == read(service, pdf)
    assert (
        hashlib.sha256((folder / "rendition.json").read_bytes()).hexdigest()
        == record["receipt_sha256"]
    )
    assert _call(exporter, **request)["reused"]
    assert len(renderer.inputs) == 1
