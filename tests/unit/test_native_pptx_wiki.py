"""PPTX snapshots preserve exact attachments, full references and older exports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.domain.native_pptx import NativePptxShapeLocator
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_pptx_package import NativePptxPackage
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_pptx_helpers import build_presentation
from tests.native_workbook_helpers import _call


def test_pptx_projection_preserves_opaque_snapshot_and_all_exact_parts(tmp_path):
    source = tmp_path / "slides.pptx"
    source.write_bytes(build_presentation())
    repository = FileNativeAssetRepository(tmp_path / "store")
    publisher = FileNativeWikiPublisher((tmp_path / "store",))
    old_service = NativeDocumentService(repository, SpreadsheetFileAdapter(), publisher)
    asset = _call(old_service, op="register", source_path=str(source))["asset"]
    request = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "output_dir": str(tmp_path / "wiki"),
    }
    legacy = _call(old_service, **request)
    legacy_dir = Path(legacy["output_dir"])
    old_bytes = {p.name: p.read_bytes() for p in legacy_dir.iterdir()}
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        publisher,
        presentations=NativePresentation(),
    )
    exported = _call(
        service,
        **request,
        citation_contract={"preset": "author-year"},
        citation_metadata={"authors": "Lin", "year": "2026"},
    )
    output = Path(exported["output_dir"])
    assert output != legacy_dir
    assert {p.name: p.read_bytes() for p in legacy_dir.iterdir()} == old_bytes
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["projection"] == "pptx-shapes-v1"
    assert exported["shape_count"] > 5
    package = NativePptxPackage(source.read_bytes())
    for part, info in manifest["part_attachments"].items():
        actual = (output / info["attachment"]).read_bytes()
        assert actual == package.parts[part]
        assert hashlib.sha256(actual).hexdigest() == info["sha256"]
    assert set(manifest["part_attachments"]) == set(package.parts)
    records = [
        json.loads(line)
        for line in (output / "records.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    for record in records:
        assert _call(service, op="verify", reference=record["evidence"])["valid"]
        source_record = service.presentations.read_shape(
            source.read_bytes(), NativePptxShapeLocator(**record["locator"])
        )
        assert record["xml"] == source_record["xml"]
        assert "Lin, 2026" in record["citation_presentation"]["inline"]
        assert "slide ID" in record["citation_presentation"]["inline"]
        assert (output / record["note"]).exists()
    assert (output / manifest["source_attachment"]).read_bytes() == source.read_bytes()
    assert (
        _call(
            service,
            **request,
            citation_contract={"preset": "author-year"},
            citation_metadata={"authors": "Lin", "year": "2026"},
        )["reused"]
        is True
    )
    note = output / records[0]["note"]
    note.write_text("Human synthesis", encoding="utf-8")
    with pytest.raises(ValueError):
        _call(service, **request)
    assert note.read_text(encoding="utf-8") == "Human synthesis"
