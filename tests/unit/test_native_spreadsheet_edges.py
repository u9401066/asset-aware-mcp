"""Workbook encoding, formula dependencies and process-interruption regressions."""

from __future__ import annotations

import hashlib
import io
import os
import subprocess
import sys
from pathlib import Path

import pytest
from lxml import etree
from openpyxl import load_workbook

from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeWorkbookCreate
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_ooxml import DOC_REL_NS, REL_NS, SHEET_NS, TYPE_NS
from src.infrastructure.native_spreadsheet import (
    NativeSpreadsheet,
    SpreadsheetFileAdapter,
)
from tests.native_workbook_helpers import _call, _edit, _parts, _replace


@pytest.fixture
def service(tmp_path: Path) -> NativeDocumentService:
    return NativeDocumentService(
        FileNativeAssetRepository(tmp_path / "store"), SpreadsheetFileAdapter()
    )


@pytest.mark.parametrize("value", ["_x0041_", "_x005F_x0041_", "_x000d_\r\n繁體中文😀"])
def test_literal_ooxml_escapes_survive_creation_and_edit(value: str) -> None:
    data = SpreadsheetFileAdapter().create(
        NativeWorkbookCreate(edits=[_edit("A1", value, sheet="Sheet1")])
    )
    assert NativeSpreadsheet(data).read_cell("Sheet1", "A1")["value"] == value
    updated, _ = NativeSpreadsheet(data).edit([_edit("A2", value, sheet="Sheet1")])
    assert NativeSpreadsheet(updated).read_cell("Sheet1", "A2")["value"] == value
    # openpyxl does not decode escaped inline strings. Assert the literal wire
    # representation as well as our decoded read, not a false independent pass.
    root = etree.fromstring(_parts(updated)["xl/worksheets/sheet1.xml"])
    text = root.find(f".//{{{SHEET_NS}}}is/{{{SHEET_NS}}}t").text
    assert text.startswith("_x005F_")
    if "\r" in value:
        assert "_x000D_" in text
        assert "\r" not in text


def test_encoded_surrogate_pairs_read_as_unicode() -> None:
    data = SpreadsheetFileAdapter().create(
        NativeWorkbookCreate(edits=[_edit("A1", "placeholder", sheet="Sheet1")])
    )
    parts = _parts(data)
    data = _replace(
        data,
        {
            "xl/worksheets/sheet1.xml": parts["xl/worksheets/sheet1.xml"].replace(
                b"placeholder", b"_xD83D__xDE00_"
            )
        },
    )
    assert NativeSpreadsheet(data).read_cell("Sheet1", "A1")["value"] == "😀"


def test_shared_formula_followers_are_not_fabricated_as_empty_formulas() -> None:
    data = SpreadsheetFileAdapter().create(
        NativeWorkbookCreate(edits=[_edit("A1", "=1+1", "formula", "Sheet1")])
    )
    parts = _parts(data)
    root = etree.fromstring(parts["xl/worksheets/sheet1.xml"])
    formula = root.find(f".//{{{SHEET_NS}}}f")
    formula.text = None
    formula.set("t", "shared")
    formula.set("si", "0")
    data = _replace(data, {"xl/worksheets/sheet1.xml": etree.tostring(root)})
    cell = NativeSpreadsheet(data).read_cell("Sheet1", "A1")
    assert cell["value"] is None
    assert cell["formula_resolved"] is False
    with pytest.raises(ValueError, match="range-aware"):
        NativeSpreadsheet(data).edit([_edit("A1", 4, "number", "Sheet1")])


def test_stale_calculation_chain_removed_with_relationship_and_content_type() -> None:
    data = SpreadsheetFileAdapter().create(
        NativeWorkbookCreate(edits=[_edit("A1", "=1+1", "formula", "Sheet1")])
    )
    parts = _parts(data)
    rels = etree.fromstring(parts["xl/_rels/workbook.xml.rels"])
    etree.SubElement(
        rels,
        f"{{{REL_NS}}}Relationship",
        Id="rIdChain",
        Type=f"{DOC_REL_NS}/calcChain",
        Target="calcChain.xml",
    )
    types = etree.fromstring(parts["[Content_Types].xml"])
    etree.SubElement(
        types,
        f"{{{TYPE_NS}}}Override",
        PartName="/xl/calcChain.xml",
        ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.calcChain+xml",
    )
    data = _replace(
        data,
        {
            "xl/_rels/workbook.xml.rels": etree.tostring(rels),
            "[Content_Types].xml": etree.tostring(types),
            "xl/calcChain.xml": f'<calcChain xmlns="{SHEET_NS}"><c r="A1" i="1"/></calcChain>'.encode(),
        },
    )
    updated, report = NativeSpreadsheet(data).edit(
        [_edit("A1", "=2+2", "formula", "Sheet1")]
    )
    after = _parts(updated)
    assert "xl/calcChain.xml" not in after
    assert b"calcChain" not in after["xl/_rels/workbook.xml.rels"]
    assert b"calcChain" not in after["[Content_Types].xml"]
    assert "stale_calculation_chain_removed" in report.repairs
    assert load_workbook(io.BytesIO(updated)).active["A1"].value == "=2+2"


def test_long_cell_excerpt_retains_full_evidence_identity(
    service: NativeDocumentService,
) -> None:
    value = "中文😀_x0041_" * 2000
    asset = _call(
        service,
        op="create",
        workbook={"edits": [{"sheet": "Sheet1", "cell": "A1", "value": value}]},
    )["asset"]
    canonical = _call(service, op="inspect", asset_id=asset["asset_id"])["content"][
        "cells"
    ][0]
    chunks = []
    offset = 0
    while True:
        cell = _call(
            service,
            op="read_cell",
            asset_id=asset["asset_id"],
            sheet="Sheet1",
            cell="A1",
            text_offset=offset,
            text_limit=1700,
        )["cell"]
        assert cell["evidence"] == canonical["evidence"]
        assert cell["value_text_sha256"] == hashlib.sha256(value.encode()).hexdigest()
        assert cell["representation_complete"] is False
        assert "value" not in cell
        chunks.append(cell["value_excerpt"])
        if cell["next_text_offset"] is None:
            break
        offset = cell["next_text_offset"]
    assert "".join(chunks) == value


def test_concurrent_operation_is_rejected_then_lock_is_reusable(tmp_path: Path) -> None:
    repository = FileNativeAssetRepository(tmp_path / "store")
    asset = repository.create("test.txt", b"original", "txt", "text/plain")
    with repository._lock(asset.asset_id), pytest.raises(ValueError, match="busy"):
        repository.archive(asset.asset_id, asset.revision)
    assert repository.archive(asset.asset_id, asset.revision).archived


def test_crashed_process_does_not_leave_a_stale_operation_lock(tmp_path: Path) -> None:
    repository = FileNativeAssetRepository(tmp_path / "store")
    asset = repository.create("test.txt", b"original", "txt", "text/plain")
    script = """
import os, sys
from pathlib import Path
from src.infrastructure.native_asset_store import FileNativeAssetRepository
repository = FileNativeAssetRepository(Path(sys.argv[1]))
with repository._lock(sys.argv[2]):
    os._exit(17)
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(repository.root), asset.asset_id],
        capture_output=True,
        timeout=20,
        check=False,
    )
    assert process.returncode == 17, process.stderr.decode()
    assert repository.archive(asset.asset_id, asset.revision).archived


def test_human_changes_refresh_same_asset_and_preserve_old_revision(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    data = SpreadsheetFileAdapter().create(NativeWorkbookCreate())
    path = tmp_path / "source.xlsx"
    path.write_bytes(data)
    asset = _call(service, op="register", source_path=str(path))["asset"]
    external, _ = NativeSpreadsheet(data).edit(
        [_edit("A1", "Human edit", sheet="Sheet1")]
    )
    path.write_bytes(external)
    refreshed = _call(
        service,
        op="refresh",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        expected_source_sha256=asset["source"]["sha256"],
    )["asset"]
    assert refreshed["asset_id"] == asset["asset_id"]
    assert refreshed["revision"] == hashlib.sha256(external).hexdigest()
    assert refreshed["source"]["sha256"] == refreshed["revision"]
    assert service.repository.read(asset["asset_id"], asset["revision"]) == data
    assert path.read_bytes() == external


def test_refresh_refuses_divergence_without_discarding_agent_or_human_edits(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    data = SpreadsheetFileAdapter().create(NativeWorkbookCreate())
    path = tmp_path / "source.xlsx"
    path.write_bytes(data)
    asset = _call(service, op="register", source_path=str(path))["asset"]
    managed = _call(
        service,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "Sheet1", "cell": "A1", "value": "Agent edit"}],
    )["asset"]
    external, _ = NativeSpreadsheet(data).edit(
        [_edit("A1", "Human edit", sheet="Sheet1")]
    )
    path.write_bytes(external)
    with pytest.raises(ValueError, match="diverged"):
        _call(
            service,
            op="refresh",
            asset_id=asset["asset_id"],
            expected_revision=managed["revision"],
            expected_source_sha256=asset["revision"],
        )
    assert service.repository.load(asset["asset_id"]).revision == managed["revision"]
    assert path.read_bytes() == external


def test_refresh_reconciles_writeback_metadata_failure(
    service: NativeDocumentService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = SpreadsheetFileAdapter().create(NativeWorkbookCreate())
    path = tmp_path / "source.xlsx"
    path.write_bytes(data)
    asset = _call(service, op="register", source_path=str(path))["asset"]
    managed = _call(
        service,
        op="update",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        edits=[{"sheet": "Sheet1", "cell": "A1", "value": "Agent edit"}],
    )["asset"]
    with monkeypatch.context() as patch:

        def fail(_asset: object) -> None:
            raise OSError("simulated failed metadata write")

        patch.setattr(service.repository, "_save", fail)
        result = _call(
            service,
            op="writeback",
            asset_id=asset["asset_id"],
            expected_revision=managed["revision"],
            expected_source_sha256=asset["revision"],
        )
    assert result["source_written"] is True and result["success"] is False
    refreshed = _call(
        service,
        op="refresh",
        asset_id=asset["asset_id"],
        expected_revision=managed["revision"],
        expected_source_sha256=asset["revision"],
    )["asset"]
    assert refreshed["revision_count"] == 2
    assert refreshed["source"]["sha256"] == managed["revision"]


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO behavior")
@pytest.mark.timeout(5)
def test_register_rejects_fifo_without_waiting_for_a_writer(
    service: NativeDocumentService, tmp_path: Path
) -> None:
    path = tmp_path / "not-a-file.txt"
    os.mkfifo(path)
    with pytest.raises(ValueError, match="regular file"):
        _call(service, op="register", source_path=str(path))
