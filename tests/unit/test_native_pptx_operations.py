"""Managed presentation revisions, evidence, chunking and guarded writeback."""

from __future__ import annotations

import hashlib
import json

import pytest

from src.application.native_document_service import NativeDocumentService
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_pptx import NativePptxTextEdit, NativePresentationCreate
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pptx import NativePresentation
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.presentation.response_limits import format_limited_json_response
from tests.native_pptx_helpers import build_presentation, edit_run, find_shape
from tests.native_workbook_helpers import _call


@pytest.fixture
def managed(tmp_path):
    source = tmp_path / "source.pptx"
    source.write_bytes(build_presentation())
    service = NativeDocumentService(
        FileNativeAssetRepository(tmp_path / "store"),
        SpreadsheetFileAdapter(),
        presentations=NativePresentation(),
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def read_shape(service, asset, locator):
    offset = 0
    chunks = []
    digest = None
    while True:
        result = _call(
            service,
            op="read_pptx_shape",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            pptx_locator=locator,
            text_offset=offset,
            text_limit=4000,
        )
        assert "response_truncated" not in format_limited_json_response(
            title="PPTX", payload=result
        )
        shape = result["shape"]
        digest = digest or shape["text_sha256"]
        assert shape["text_sha256"] == digest
        assert shape["excerpt_char_range"][0] == offset
        chunks.append(shape["text_excerpt"])
        if shape["next_text_offset"] is None:
            break
        offset = shape["next_text_offset"]
    text = "".join(chunks)
    assert len(text) == shape["text_length"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == digest
    return json.loads(text)


def test_read_edit_old_evidence_writeback_and_archive(managed):
    service, asset, source = managed
    original = source.read_bytes()
    discovery = _call(service, op="contract", for_op="update_pptx")
    assert "update_pptx" in discovery["formats"]["pptx"]
    assert asset["capabilities"]["edit_pptx"] is True
    listing = _call(service, op="read_pptx", asset_id=asset["asset_id"], limit=1)
    assert len(listing["shapes"]) == 1 and listing["next_offset"] == 1
    record = read_shape(service, asset, listing["shapes"][0]["locator"])
    reference = record["evidence"]
    assert reference == listing["shapes"][0]["evidence"]
    assert _call(service, op="verify", reference=reference)["valid"] is True
    tampered = dict(reference, value_sha256="0" * 64)
    assert _call(service, op="verify", reference=tampered)["valid"] is False
    edit = edit_run(record, "Managed update").model_dump()
    changed = _call(
        service,
        op="update_pptx",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pptx_edits=[edit],
    )
    assert changed["source_written"] is False and source.read_bytes() == original
    current = changed["asset"]
    assert current["revision"] != asset["revision"]
    old = _call(service, op="verify", reference=reference)
    assert old["valid"] and not old["is_current_managed_revision"]
    writeback = _call(
        service,
        op="writeback",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
        expected_source_sha256=asset["source"]["sha256"],
    )
    assert writeback["source_written"] is True
    assert "Managed update" in find_shape(source.read_bytes(), "Styled text")["xml"]
    _call(
        service,
        op="archive",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
    )
    assert _call(service, op="verify", reference=reference)["archived"] is True
    with pytest.raises(ValueError, match="Archived or stale"):
        _call(
            service,
            op="update_pptx",
            asset_id=asset["asset_id"],
            expected_revision=current["revision"],
            pptx_edits=[edit],
        )


def test_concurrent_revision_rejects_delayed_commit(managed, monkeypatch):
    service, asset, source = managed
    adapter = service.presentations
    original_edit = adapter.edit
    record = find_shape(source.read_bytes(), "Styled text")
    competing = None

    def interleave(data, edits):
        nonlocal competing
        candidate = original_edit(data, edits)
        other, report = original_edit(data, [edit_run(record, "Concurrent")])
        competing = service.repository.commit(
            asset["asset_id"], asset["revision"], other, report
        ).revision
        return candidate

    monkeypatch.setattr(adapter, "edit", interleave)
    with pytest.raises(ValueError, match="Stale"):
        _call(
            service,
            op="update_pptx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pptx_edits=[edit_run(record, "Delayed").model_dump()],
        )
    assert service.repository.load(asset["asset_id"]).revision == competing
    assert hashlib.sha256(source.read_bytes()).hexdigest() == asset["revision"]


@pytest.mark.parametrize(
    "text", ["\x00", "\ud800", "line\nbreak", "tab\tvalue", "\uffff"]
)
def test_text_edits_reject_xml_and_structural_characters(managed, text):
    _, _, source = managed
    request = edit_run(
        find_shape(source.read_bytes(), "Styled text"), "valid"
    ).model_dump()
    with pytest.raises(ValueError):
        NativePptxTextEdit.model_validate({**request, "text": text})


@pytest.mark.parametrize(
    "payload",
    [
        {"op": "create_pptx"},
        {"op": "read_pptx", "asset_id": "file_" + "a" * 32, "sheet": "S"},
        {
            "op": "update_pptx",
            "asset_id": "file_" + "a" * 32,
            "expected_revision": "a" * 64,
            "pptx_edits": [],
        },
        {"op": "read_pptx_shape", "asset_id": "file_" + "a" * 32},
    ],
)
def test_presentation_operations_reject_missing_or_unrelated_inputs(payload):
    with pytest.raises(ValueError):
        NativeDocumentRequest.model_validate(payload)


def test_native_creation_limits_and_independent_asset(managed):
    service, _, _ = managed
    created = _call(
        service,
        op="create_pptx",
        presentation={"name": "independent.pptx", "slides": [{}]},
    )
    assert created["asset"]["source"] is None
    assert created["asset"]["format"] == "pptx"
    for name in ("../escape.pptx", "wrong.docx"):
        with pytest.raises(ValueError):
            NativePresentationCreate.model_validate({"name": name, "slides": [{}]})
    with pytest.raises(ValueError, match="supplied together"):
        NativePptxTextEdit.model_validate(
            {
                "locator": {
                    "slide_id": "256",
                    "part": "ppt/slides/slide1.xml",
                    "shape_id": "2",
                    "row": 0,
                    "paragraph": 0,
                    "run": 0,
                },
                "expected_text_sha256": "a" * 64,
                "text": "Invalid",
            }
        )


def test_shape_pagination_does_not_materialize_unrequested_xml(managed, monkeypatch):
    from src.infrastructure import native_pptx

    service, asset, _ = managed
    original = native_pptx.shape_record
    seen = []

    def record(locator, shape, parents):
        seen.append(locator)
        assert len(seen) == 1, "Unrequested shape XML was materialized"
        return original(locator, shape, parents)

    monkeypatch.setattr(native_pptx, "shape_record", record)
    result = _call(
        service, op="read_pptx", asset_id=asset["asset_id"], offset=1, limit=1
    )
    assert len(result["shapes"]) == len(seen) == 1
    assert result["shape_count"] > 5
    assert result["next_offset"] == 2
