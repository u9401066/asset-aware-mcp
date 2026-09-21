"""Managed PDF evidence, creation lineage, revision conflicts and source writes."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.domain.native_pdf import NativePdfPageEdit
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_pdf_helpers import build_pdf, page_reference, pixels
from tests.native_workbook_helpers import _call


@pytest.fixture
def managed_pdf(tmp_path):
    source = tmp_path / "source.pdf"
    source.write_bytes(build_pdf(links=True, forms=True, labels=True))
    repository = FileNativeAssetRepository(tmp_path / "store")
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((tmp_path / "store",)),
        pdfs=NativePdf(),
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def read_pdf_page(service, asset, locator):
    chunks, offset, digest = [], 0, None
    while True:
        result = _call(
            service,
            op="read_pdf_page",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            pdf_locator=locator,
            text_offset=offset,
            text_limit=4000,
        )["page"]
        digest = digest or result["text_sha256"]
        assert result["text_sha256"] == digest
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


def test_pdf_managed_reorder_evidence_and_writeback(managed_pdf):
    service, asset, source = managed_pdf
    original = source.read_bytes()
    assert asset["capabilities"]["edit_pdf_pages"]
    overview = _call(service, op="read_pdf", asset_id=asset["asset_id"], limit=1)
    assert overview["next_offset"] == 1
    record = read_pdf_page(service, asset, overview["pages"][0]["locator"])
    assert _call(service, op="verify", reference=record["evidence"])["valid"]
    refs = [
        page_reference(original, i, asset["asset_id"]).model_dump() for i in (2, 0, 1)
    ]
    changed = _call(
        service,
        op="reorder_pdf_pages",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pdf_order=refs,
    )
    assert not changed["source_written"] and source.read_bytes() == original
    current = changed["asset"]
    proof = _call(service, op="verify", reference=record["evidence"])
    assert proof["valid"] and not proof["is_current_managed_revision"]
    result = _call(
        service,
        op="writeback",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
        expected_source_sha256=asset["source"]["sha256"],
    )
    assert Path(result["backup_path"]).read_bytes() == original
    assert pixels(source.read_bytes()) == [pixels(original)[i] for i in (2, 0, 1)]


def test_pdf_creation_retains_source_lineage(managed_pdf):
    service, asset, source = managed_pdf
    inputs = [
        {
            "reference": page_reference(
                source.read_bytes(), i, asset["asset_id"]
            ).model_dump()
        }
        for i in range(3)
    ]
    created = _call(
        service, op="create_pdf", pdf_create={"name": "copied.pdf", "pages": inputs}
    )
    assert created["asset"]["source"] is None
    history = service.repository.load(created["asset"]["asset_id"]).history[0]
    result = service.repository.read_result(created["asset"]["asset_id"], history)
    assert result is not None
    assert [c["source_reference"] for c in result.changes] == [
        p["reference"] for p in inputs
    ]


def test_pdf_wiki_keeps_opaque_and_historical_snapshots(managed_pdf, tmp_path):
    service, asset, source = managed_pdf
    publisher = FileNativeWikiPublisher((tmp_path / "store",))
    old_service = NativeDocumentService(
        service.repository, service.spreadsheets, publisher
    )
    request = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "output_dir": str(tmp_path / "wiki"),
    }
    opaque = _call(old_service, **request)
    opaque_bytes = {
        p.name: p.read_bytes() for p in Path(opaque["output_dir"]).iterdir()
    }
    exported = _call(
        service,
        **request,
        citation_contract={"preset": "author-year"},
        citation_metadata={"authors": "Lin", "year": "2026"},
    )
    path = Path(exported["output_dir"])
    manifest = json.loads((path / "manifest.json").read_text())
    assert (
        manifest["projection"] == "pdf-annotations-v1" and exported["page_count"] == 3
    )
    assert exported["annotation_count"] == 8
    assert (path / manifest["source_attachment"]).read_bytes() == source.read_bytes()
    records = [json.loads(s) for s in (path / "records.jsonl").read_text().splitlines()]
    for record in records:
        assert _call(service, op="verify", reference=record["evidence"])["valid"]
        assert (
            hashlib.sha256(
                (path / record["preview_attachment"]).read_bytes()
            ).hexdigest()
            == record["preview_sha256"]
        )
        assert "Lin, 2026" in record["citation_presentation"]["inline"]
    assert {
        p.name: p.read_bytes() for p in Path(opaque["output_dir"]).iterdir()
    } == opaque_bytes
    note = path / records[0]["note"]
    note.write_text("Human synthesis")
    with pytest.raises(ValueError):
        _call(
            service,
            **request,
            citation_contract={"preset": "author-year"},
            citation_metadata={"authors": "Lin", "year": "2026"},
        )
    assert note.read_text() == "Human synthesis"


def test_pdf_concurrent_update_fails_without_source_write(managed_pdf, monkeypatch):
    service, asset, source = managed_pdf
    original = source.read_bytes()
    ref = page_reference(original, 0, asset["asset_id"])
    edit = service.pdfs.edit
    competing = None

    def interleave(data, edits):
        nonlocal competing
        candidate = edit(data, edits)
        other, report = edit(data, [NativePdfPageEdit(reference=ref, rotation=180)])
        competing = service.repository.commit(
            asset["asset_id"], asset["revision"], other, report
        ).revision
        return candidate

    monkeypatch.setattr(service.pdfs, "edit", interleave)
    with pytest.raises(ValueError, match="Stale"):
        _call(
            service,
            op="update_pdf",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pdf_edits=[{"reference": ref.model_dump(), "rotation": 90}],
        )
    assert service.repository.load(asset["asset_id"]).revision == competing
    assert source.read_bytes() == original


@pytest.mark.parametrize("failure", ["asset", "revision", "archived", "source"])
def test_pdf_reference_and_source_guards(managed_pdf, failure):
    service, asset, source = managed_pdf
    original = source.read_bytes()
    ref = page_reference(original, 0, asset["asset_id"]).model_dump()
    if failure in {"asset", "revision"}:
        ref["asset_id" if failure == "asset" else "revision"] = (
            "file_" + "0" * 32 if failure == "asset" else "0" * 64
        )
    elif failure == "archived":
        _call(
            service,
            op="archive",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
        )
    else:
        changed = _call(
            service,
            op="update_pdf",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pdf_edits=[{"reference": ref, "rotation": 90}],
        )
        source.write_bytes(original + b"human edit")
        with pytest.raises(ValueError, match="Source changed"):
            _call(
                service,
                op="writeback",
                asset_id=asset["asset_id"],
                expected_revision=changed["asset"]["revision"],
                expected_source_sha256=asset["source"]["sha256"],
            )
        assert source.read_bytes() == original + b"human edit"
        return
    with pytest.raises(ValueError):
        _call(
            service,
            op="update_pdf",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pdf_edits=[{"reference": ref, "rotation": 90}],
        )
    assert source.read_bytes() == original
