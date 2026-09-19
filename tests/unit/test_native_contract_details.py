"""All enabled capabilities remain discoverable beyond one response's prose budget."""

import hashlib
import inspect
import json

import pytest

from src.application.native_document_contract import native_document_contract
from src.domain.native_assets import NativeDocumentRequest
from src.presentation.response_limits import format_limited_json_response

FLAGS = {
    name: True
    for name in inspect.signature(native_document_contract).parameters
    if name != "request"
}


def test_complete_capabilities_and_policies_survive_bounded_delivery():
    contract = native_document_contract(
        NativeDocumentRequest(for_op="update_docx_story_structure"), **FLAGS
    )
    assert contract["contract_delivery"] == "paged"
    assert contract["docx_story_structure_enabled"]
    assert "update_docx_story_structure" in contract["formats"]["docx"]
    assert "response_truncated" not in format_limited_json_response(
        title="Native", payload=contract
    )
    chunks, offset = [], 0
    while True:
        request = NativeDocumentRequest.model_validate(
            {**contract["contract_request"], "text_offset": offset, "text_limit": 377}
        )
        page = native_document_contract(request, **FLAGS)
        assert page["excerpt_char_range"][0] == offset
        assert "response_truncated" not in format_limited_json_response(
            title="Native", payload=page
        )
        assert page["contract_sha256"] == contract["contract_sha256"]
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == contract["contract_sha256"]
    full = json.loads(text)
    assert full["operations"] == contract["operations"]
    assert full["formats"] == contract["formats"]
    assert full["schema_request"] == contract["schema_request"]
    assert "bind part:null resumes inheritance" in full["docx_story_structure_policy"]
    assert full["docx_rendering"]["policy"]
    assert full["verification"] == contract["verification"]


@pytest.mark.parametrize("fault", ["hash", "scope", "capabilities"])
def test_changed_contract_or_scope_requires_rediscovery(fault):
    contract = native_document_contract(
        NativeDocumentRequest(for_op="update_docx_story_structure"), **FLAGS
    )
    fields = dict(contract["contract_request"])
    flags = dict(FLAGS)
    if fault == "hash":
        fields["contract_sha256"] = "0" * 64
    if fault == "scope":
        fields["for_op"] = "read_docx_story"
    if fault == "capabilities":
        flags["docx_stories_enabled"] = False
    with pytest.raises(ValueError, match="changed or scope"):
        native_document_contract(NativeDocumentRequest.model_validate(fields), **flags)
