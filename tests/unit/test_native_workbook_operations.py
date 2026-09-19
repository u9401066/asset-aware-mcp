"""Complete paged structure reads, immutable evidence and stale-write protection."""

import hashlib
import json

import pytest

from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_workbook_structure import NativeWorkbookStructure
from src.presentation.response_limits import format_limited_json_response
from tests.native_workbook_helpers import _call, build_workbook


def service_at(path):
    return NativeDocumentService(
        FileNativeAssetRepository(path),
        SpreadsheetFileAdapter(),
        workbook_structure=NativeWorkbookStructure(),
    )


def read(service, asset, view="structure", limit=4000):
    chunks, offset, sha = [], 0, None
    while True:
        result = _call(
            service,
            op="read_workbook",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            workbook_view=view,
            text_offset=offset,
            text_limit=limit,
        )
        assert result["source_written"] is False
        assert "response_truncated" not in format_limited_json_response(
            title="Workbook", payload=result
        )
        sha = sha or result["text_sha256"]
        assert result["text_sha256"] == sha
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    encoded = "".join(chunks).encode("utf-8")
    assert hashlib.sha256(encoded).hexdigest() == sha
    return json.loads(encoded)


def test_service_full_lifecycle_and_historical_cell_evidence(tmp_path):
    service = service_at(tmp_path / "store")
    source = tmp_path / "source.xlsx"
    source.write_bytes(build_workbook())
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    first = asset = _call(service, op="register", source_path=str(source))["asset"]
    assert asset["capabilities"]["edit_worksheets"]
    evidence = _call(
        service, op="read_cell", asset_id=asset["asset_id"], sheet="Data", cell="A1"
    )["cell"]["evidence"]
    initial = read(service, first, "references", 139)
    key = initial["worksheets"][0]["key"]
    changed = _call(
        service,
        op="rename_worksheet",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        worksheet_rename={"key": key, "name": "研究 O'Brien"},
    )
    asset = changed["asset"]
    current = read(service, asset, "references")
    assert current["operation_result"]["changes"][0]["operation"] == "rename_worksheet"
    assert current["worksheets"][0]["key"] == key
    assert any(field["text"] == "'研究 O''Brien'!A2" for field in current["references"])
    assert read(service, first, "references") == initial
    proof = _call(service, op="verify", reference=evidence)
    assert proof["valid"] and not proof["is_current_managed_revision"]
    with pytest.raises(ValueError, match="stale"):
        _call(
            service,
            op="delete_worksheets",
            asset_id=asset["asset_id"],
            expected_revision=first["revision"],
            worksheet_keys=[key],
        )
    for op, payload in [
        ("add_worksheets", {"worksheet_insert": {"index": 0, "names": ["Temporary"]}}),
        ("reorder_worksheets", None),
        ("delete_worksheets", None),
    ]:
        structure = read(service, asset)
        if op == "reorder_worksheets":
            payload = {
                "worksheet_order": [
                    item["key"] for item in reversed(structure["worksheets"])
                ]
            }
        if op == "delete_worksheets":
            payload = {
                "worksheet_keys": [
                    item["key"]
                    for item in structure["worksheets"]
                    if item["name"] == "Temporary"
                ]
            }
        asset = _call(
            service,
            op=op,
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            **payload,
        )["asset"]
    assert [item["name"] for item in read(service, asset)["worksheets"]] == [
        "Other",
        "研究 O'Brien",
    ]
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
    )
    with pytest.raises(ValueError, match="Archived"):
        _call(
            service,
            op="add_worksheets",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            worksheet_insert={"index": 0, "names": ["Late"]},
        )
    assert read(service, first) and source.read_bytes() == original
    assert source.stat().st_mtime_ns == mtime


def test_contract_availability_and_operation_specific_schemas(tmp_path):
    service = service_at(tmp_path / "store")
    contract = _call(service, op="contract", for_op="add_worksheets")
    assert contract["workbook_structure_enabled"]
    assert "add_worksheets" in contract["formats"]["xlsx"]
    basic = NativeDocumentService(service.repository, SpreadsheetFileAdapter())
    assert "add_worksheets" not in _call(basic, op="contract")["formats"]["xlsx"]
    for op, payload in [
        ("add_worksheets", {"worksheet_insert": {"index": 0, "names": ["Valid"]}}),
        (
            "rename_worksheet",
            {
                "worksheet_rename": {
                    "key": {"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"},
                    "name": "新名稱",
                }
            },
        ),
    ]:
        with pytest.raises(ValueError, match="expected_revision"):
            NativeDocumentRequest.model_validate(
                {"op": op, "asset_id": "file_" + "a" * 32, **payload}
            )
    with pytest.raises(ValueError, match="Fields not used"):
        NativeDocumentRequest(op="contract", allow_3d_membership_change=True)
