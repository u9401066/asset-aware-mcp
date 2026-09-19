"""Public grid operations retain revision CAS, complete receipts and old evidence."""

import pytest

from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_workbook_grid import NativeWorkbookGrid
from src.infrastructure.native_workbook_structure import NativeWorkbookStructure
from tests.native_workbook_helpers import _call, _edit, build_workbook
from tests.unit.test_native_workbook_operations import read


def service_at(path, *, enabled=True):
    return NativeDocumentService(
        FileNativeAssetRepository(path),
        SpreadsheetFileAdapter(),
        workbook_structure=NativeWorkbookStructure(),
        workbook_grid=NativeWorkbookGrid() if enabled else None,
    )


def edit_request(asset, key):
    return {
        "op": "update_worksheet_grid",
        "asset_id": asset["asset_id"],
        "expected_revision": asset["revision"],
        "worksheet_grid": {
            "worksheet": key,
            "edits": [{"axis": "row", "operation": "insert", "at": 1}],
        },
    }


def test_grid_service_history_evidence_and_source_publication_are_separate(tmp_path):
    service = service_at(tmp_path / "store")
    path = tmp_path / "original.xlsx"
    original = build_workbook()
    path.write_bytes(original)
    mtime = path.stat().st_mtime_ns
    asset = _call(service, op="register", source_path=str(path))["asset"]
    assert asset["capabilities"]["update_worksheet_grid"]
    reference = _call(
        service, op="read_cell", asset_id=asset["asset_id"], sheet="Data", cell="A1"
    )["cell"]["evidence"]
    before = read(service, asset)
    key = before["worksheets"][0]["key"]
    changed = _call(service, **edit_request(asset, key))
    assert changed["success"] and not changed["source_written"]
    assert changed["asset"]["capabilities"]["update_worksheet_grid"]
    after = read(service, changed["asset"], "references", 173)
    assert (
        after["operation_result"]["changes"][0]["operation"] == "update_worksheet_grid"
    )
    assert changed["review_request"]["revision"] == changed["asset"]["revision"]
    assert read(service, asset) == before
    proof = _call(service, op="verify", reference=reference)
    assert proof["valid"] and not proof["is_current_managed_revision"]
    assert (
        _call(
            service, op="read_cell", asset_id=asset["asset_id"], sheet="Data", cell="A2"
        )["cell"]["value_excerpt"]
        == "Original"
    )
    with pytest.raises(ValueError, match="stale"):
        _call(service, **edit_request(asset, key))
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    assert path.read_bytes() == original and path.stat().st_mtime_ns == mtime


def test_grid_capabilities_and_required_payload_are_truthful(tmp_path):
    service = service_at(tmp_path / "store")
    enabled = _call(service, op="contract", for_op="update_worksheet_grid")
    assert enabled["workbook_grid_enabled"]
    assert "update_worksheet_grid" in enabled["formats"]["xlsx"]
    disabled = service_at(tmp_path / "basic", enabled=False)
    contract = _call(disabled, op="contract")
    assert not contract["workbook_grid_enabled"]
    assert "update_worksheet_grid" not in contract["formats"]["xlsx"]
    source = tmp_path / "original.xlsx"
    source.write_bytes(build_workbook())
    asset = _call(disabled, op="register", source_path=str(source))["asset"]
    key = read(disabled, asset)["worksheets"][0]["key"]
    with pytest.raises(ValueError, match="not configured"):
        _call(disabled, **edit_request(asset, key))
    with pytest.raises(ValueError, match="read-back support"):
        NativeDocumentService(
            service.repository, service.spreadsheets, workbook_grid=NativeWorkbookGrid()
        )
    payload = edit_request(asset, key)
    payload.pop("expected_revision")
    with pytest.raises(ValueError, match="expected_revision"):
        NativeDocumentRequest.model_validate(payload)


def test_late_grid_cas_failure_preserves_the_concurrent_revision(tmp_path):
    service = service_at(tmp_path / "store")
    path = tmp_path / "original.xlsx"
    path.write_bytes(build_workbook())
    asset = _call(service, op="register", source_path=str(path))["asset"]
    key = read(service, asset)["worksheets"][0]["key"]

    class ConcurrentGrid:
        def update(self, data, request):
            planned = NativeWorkbookGrid().update(data, request)
            newer, checks = service.spreadsheets.edit(data, [_edit("A1", "Concurrent")])
            service.repository.commit(
                asset["asset_id"], asset["revision"], newer, checks
            )
            return planned

    service.workbook_operations.grid = ConcurrentGrid()
    with pytest.raises(ValueError, match="revision"):
        _call(service, **edit_request(asset, key))
    assert (
        _call(
            service, op="read_cell", asset_id=asset["asset_id"], sheet="Data", cell="A1"
        )["cell"]["value_excerpt"]
        == "Concurrent"
    )
    assert len(service.repository.load(asset["asset_id"]).history) == 2
