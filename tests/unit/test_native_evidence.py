"""Native reference verification preserves old evidence and rejects tampering."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeDocumentRequest
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from tests.native_workbook_helpers import _call


@pytest.fixture
def service(tmp_path: Path) -> NativeDocumentService:
    return NativeDocumentService(
        FileNativeAssetRepository(tmp_path / "store"), SpreadsheetFileAdapter()
    )


def _create_reference(service: NativeDocumentService) -> dict:
    asset = _call(
        service,
        op="create",
        workbook={
            "edits": [
                {"sheet": "Sheet1", "cell": "A1", "value": "Same content"},
                {"sheet": "Sheet1", "cell": "A2", "value": "Same content"},
            ]
        },
    )["asset"]
    return _call(
        service,
        op="read_cell",
        asset_id=asset["asset_id"],
        sheet="Sheet1",
        cell="A1",
        text_limit=3,
    )["cell"]["evidence"]


def test_old_reference_remains_valid_after_update_and_archive(
    service: NativeDocumentService,
) -> None:
    ref = _create_reference(service)
    first = _call(service, op="verify", reference=ref)
    assert first["valid"] is True
    assert first["is_current_managed_revision"] is True
    assert first["verification_scope"] == "immutable_native_representation"
    assert "formula_results" in first["review_required"]
    current = _call(
        service,
        op="update",
        asset_id=ref["asset_id"],
        expected_revision=ref["revision"],
        edits=[{"sheet": "Sheet1", "cell": "A1", "value": "New content"}],
    )["asset"]
    old = _call(service, op="verify", reference=ref)
    assert old["valid"] is True
    assert old["is_current_managed_revision"] is False
    _call(
        service,
        op="archive",
        asset_id=ref["asset_id"],
        expected_revision=current["revision"],
    )
    archived = _call(service, op="verify", reference=ref)
    assert archived["valid"] is True
    assert archived["archived"] is True


def test_tampered_hash_is_invalid_without_losing_successful_checks(
    service: NativeDocumentService,
) -> None:
    ref = _create_reference(service)
    ref["value_sha256"] = "f" * 64
    result = _call(service, op="verify", reference=ref)
    assert result["success"] is True
    assert result["valid"] is False
    assert result["checks"] == {
        "revision_hash": True,
        "native_locator": True,
        "cell_representation_hash": False,
    }


def test_same_text_at_another_cell_does_not_validate_the_wrong_locator(
    service: NativeDocumentService,
) -> None:
    ref = _create_reference(service)
    ref["locator"]["cell"] = "A2"
    assert _call(service, op="verify", reference=ref)["valid"] is False


@pytest.mark.parametrize(
    "key,value",
    [("part", "xl/worksheets/missing.xml"), ("sheet_id", "42"), ("kind", "invented")],
)
def test_forged_worksheet_identity_fails_closed(
    service: NativeDocumentService, key: str, value: str
) -> None:
    ref = _create_reference(service)
    ref["locator"][key] = value
    with pytest.raises(ValueError, match="locator"):
        _call(service, op="verify", reference=ref)


def test_revision_must_belong_to_the_asset(service: NativeDocumentService) -> None:
    ref = _create_reference(service)
    ref["revision"] = "f" * 64
    with pytest.raises(ValueError, match="does not belong"):
        _call(service, op="verify", reference=ref)


def test_corrupted_revision_blob_is_rejected(service: NativeDocumentService) -> None:
    ref = _create_reference(service)
    repository = service.repository
    assert isinstance(repository, FileNativeAssetRepository)
    repository._blob(ref["asset_id"], ref["revision"]).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="hash verification"):
        _call(service, op="verify", reference=ref)


def test_pdf_preview_and_extra_fields_are_not_native_references(
    service: NativeDocumentService,
) -> None:
    ref = _create_reference(service)
    preview = deepcopy(ref)
    preview["schema_version"] = "asset-ref-preview-v1"
    with pytest.raises(ValueError):
        NativeDocumentRequest.model_validate({"op": "verify", "reference": preview})
    ref["value_excerpt"] = "Same"
    with pytest.raises(ValueError):
        NativeDocumentRequest.model_validate({"op": "verify", "reference": ref})
