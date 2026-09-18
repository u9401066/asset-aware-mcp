"""Native discovery stays complete, scoped and bounded as formats grow."""

from __future__ import annotations

import hashlib
import json
from typing import get_args

import pytest
from jsonschema import Draft202012Validator

from src.application import native_schema
from src.application.native_document_contract import native_document_contract
from src.domain.native_assets import NativeDocumentRequest
from src.domain.native_operations import NATIVE_OPERATIONS, NativeOperation
from src.presentation.response_limits import format_limited_json_response


def _page(**request):
    result = native_schema.read_schema(
        NativeDocumentRequest.model_validate({"op": "schema", **request})
    )
    response = format_limited_json_response(title="Native schema", payload=result)
    assert "response_truncated" not in response
    return response


def _assemble(request):
    chunks = []
    offset = 0
    digest = request.get("schema_sha256")
    while True:
        page = _page(**{**request, "text_offset": offset})
        if digest is not None:
            assert page["schema_sha256"] == digest
        digest = page["schema_sha256"]
        assert page["excerpt_char_range"][0] == offset
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
        request = {**request, "schema_sha256": digest}
    text = "".join(chunks)
    assert len(text) == page["text_length"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == digest
    return json.loads(text)


def test_full_schema_round_trip_preserves_models_and_property_names(monkeypatch):
    monkeypatch.delenv("ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS", raising=False)
    contract = native_document_contract(docx_enabled=True)
    assert contract["contract_version"] == "native-contract-v2"
    assert contract["schema_delivery"] == "paged"
    assert "schema" not in contract
    schema = _assemble(contract["schema_request"])
    assert schema == native_schema.compact_schema(
        NativeDocumentRequest.model_json_schema()
    )
    assert set(schema["properties"]["op"]["enum"]) == set(get_args(NativeOperation))
    assert "title" in schema["$defs"]["CitationMetadata"]["properties"]
    assert "ctx" not in schema["properties"]
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("operation", get_args(NativeOperation))
def test_scoped_schema_declares_runtime_fields_and_fits_response(operation):
    assert set(NATIVE_OPERATIONS) == set(get_args(NativeOperation))
    fields = NATIVE_OPERATIONS[operation]
    contract = native_document_contract(NativeDocumentRequest(for_op=operation))
    response = format_limited_json_response(title="Native contract", payload=contract)
    assert "response_truncated" not in response
    schema = _assemble(contract["schema_request"])
    if contract["schema_delivery"] == "inline":
        assert schema == contract["schema"]
    assert set(schema["properties"]) == fields.required | fields.optional | {"op"}
    assert set(schema["required"]) == fields.required | {"op"}
    assert schema["properties"]["op"]["const"] == operation
    validator = Draft202012Validator(schema)
    Draft202012Validator.check_schema(schema)
    assert not validator.is_valid({"op": operation, "unrecognized": True})
    assert not validator.is_valid({"op": "different"})
    for name in fields.required:
        field_schema = {**schema["properties"][name], "$defs": schema.get("$defs", {})}
        assert not Draft202012Validator(field_schema).is_valid(None)


def test_scoped_update_has_nested_definitions_and_nonempty_edits():
    schema = native_schema.request_schema("update")
    validator = Draft202012Validator(schema)
    request = {
        "op": "update",
        "asset_id": "file_" + "a" * 32,
        "expected_revision": "b" * 64,
        "edits": [{"sheet": "Data", "cell": "B2", "kind": "number", "value": 4}],
    }
    validator.validate(request)
    NativeDocumentRequest.model_validate(request)
    for edits in ([], None, [{"sheet": "Data", "cell": "B2", "kind": "wrong"}]):
        assert not validator.is_valid({**request, "edits": edits})
    wiki = native_schema.request_schema("export_wiki")
    assert "CitationMetadata" in wiki["$defs"]
    assert "NativeDocxEdit" not in wiki["$defs"]
    verify = native_schema.request_schema("verify")
    assert "NativeDocxBlockLocator" in verify["$defs"]
    assert "NativeCellLocator" in verify["$defs"]


@pytest.mark.parametrize(
    "payload",
    [
        {"op": "schema", "text_offset": 1},
        {"op": "schema", "text_offset": 1, "schema_sha256": None},
        {"op": "schema", "text_offset": -1},
        {"op": "schema", "text_limit": 4001},
        {"op": "schema", "schema_sha256": "invalid"},
        {"op": "contract", "for_op": "missing"},
        {"op": "schema", "asset_id": "file_" + "a" * 32},
        {"op": "list", "for_op": "register"},
    ],
)
def test_invalid_discovery_and_cross_operation_fields_are_rejected(payload):
    with pytest.raises(ValueError):
        NativeDocumentRequest.model_validate(payload)
    schema = native_schema.request_schema(payload["op"])
    assert not Draft202012Validator(schema).is_valid(payload)


def test_schema_continuation_rejects_wrong_hash_scope_and_server_change(monkeypatch):
    first = _page(for_op="register", text_limit=10)
    with pytest.raises(ValueError, match="changed or scope differs"):
        _page(for_op="create", text_offset=10, schema_sha256=first["schema_sha256"])
    with pytest.raises(ValueError, match="changed or scope differs"):
        _page(for_op="register", schema_sha256="0" * 64)
    changed = native_schema.request_schema("register")
    changed["properties"]["source_path"]["maxLength"] = 2000
    monkeypatch.setattr(native_schema, "request_schema", lambda _: changed)
    with pytest.raises(ValueError, match="changed or scope differs"):
        _page(for_op="register", text_offset=10, schema_sha256=first["schema_sha256"])


def test_small_schema_and_end_of_stream_have_unambiguous_ranges():
    first = _page(for_op="register", text_limit=4000)
    assert first["representation_complete"] is True
    assert first["next_text_offset"] is None
    end = _page(
        for_op="register", text_offset=10000, schema_sha256=first["schema_sha256"]
    )
    assert end["text_excerpt"] == ""
    assert end["excerpt_char_range"] == [first["text_length"]] * 2
    assert end["representation_complete"] is False
    assert end["next_text_offset"] is None


def test_future_large_unicode_schema_is_complete_without_raising_response_cap(
    monkeypatch,
):
    schema = native_schema.request_schema()
    schema["$defs"]["FutureFormat"] = {
        "type": "string",
        "enum": ["簡報📄\x00" * 9000],
        "pattern": "^never-silently-omit-validation$",
    }
    monkeypatch.setattr(native_schema, "request_schema", lambda _: schema)
    monkeypatch.delenv("ASSET_AWARE_MCP_TEXT_RESPONSE_CHARS", raising=False)
    contract = native_document_contract()
    response = format_limited_json_response(title="Native contract", payload=contract)
    assert "response_truncated" not in response
    assert contract["schema_delivery"] == "paged"
    assert _assemble({**contract["schema_request"], "text_limit": 4000}) == schema
