"""Managed form transactions retain original evidence and complete operation reads."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest
from jsonschema import Draft202012Validator

from src.application.native_document_service import NativeDocumentService
from src.application.native_schema import request_schema
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_pdf import NativePdf
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from src.presentation.response_limits import format_limited_json_response
from tests.native_pdf_field_helpers import form_pdf
from tests.native_pdf_helpers import page_reference
from tests.native_workbook_helpers import _call


@pytest.fixture
def managed_fields(tmp_path):
    source = tmp_path / "form.pdf"
    source.write_bytes(form_pdf())
    repository = FileNativeAssetRepository(tmp_path / "store")
    service = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher((tmp_path / "store",)),
        pdfs=NativePdf(),
    )
    asset = _call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def complete(service, **request):
    chunks, offset, sha = [], 0, None
    while True:
        result = _call(
            service,
            **request,
            text_offset=offset,
            text_limit=4000,
            **({"pdf_field_text_sha256": sha} if sha else {}),
        )
        sha = sha or result["text_sha256"]
        assert result["text_sha256"] == sha
        assert result["excerpt_char_range"][0] == offset
        assert "response_truncated" not in format_limited_json_response(
            title="Native", payload=result
        )
        chunks.append(result["text_excerpt"])
        offset = result["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert len(text) == result["text_length"]
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
    return json.loads(text)


def catalog(service, asset):
    return complete(
        service,
        op="read_pdf_fields",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
    )["catalog"]


def read(service, asset, name, occurrence=0):
    fields = [
        f for f in catalog(service, asset)["fields"] if f["qualified_name"] == name
    ]
    return complete(
        service,
        op="read_pdf_field",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        pdf_field_locator=fields[occurrence]["locator"],
    )["field"]


def update(service, asset, edits):
    return _call(
        service,
        op="update_pdf_fields",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pdf_fields_update={
            "expected_catalog_sha256": catalog(service, asset)["catalog_sha256"],
            "edits": edits,
        },
    )


def hidden_edit(record, value):
    return {
        "op": "update",
        "reference": record["evidence"],
        "value": {"kind": "text", "text": value},
        "appearance_policy": "no_widgets",
    }


def create_edit(source, asset, parent=None):
    return {
        "op": "create",
        **({"parent_reference": parent["evidence"]} if parent else {}),
        "new_groups": ["created-group"],
        "field": {
            "name": "value",
            "kind": "text",
            "value": {"kind": "text", "text": "新增 009 µg β"},
            "widgets": [
                {
                    "page_reference": page_reference(
                        source.read_bytes(), index, asset["asset_id"]
                    ).model_dump(),
                    "rect": [0.1, 0.6, 0.85, 0.75],
                    "style": {"font_size": 10, "border_width": 0},
                }
                for index in (0, 2)
            ],
        },
    }


def test_native_field_contract_selects_complete_schemas(managed_fields):
    service, asset, _ = managed_fields
    assert asset["capabilities"]["read_pdf_fields"]
    assert asset["capabilities"]["edit_pdf_fields"]
    result = _call(service, op="contract", for_op="update_pdf_fields")
    assert result["pdf_fields_enabled"]
    assert {"read_pdf_fields", "read_pdf_field", "update_pdf_fields"} <= set(
        result["formats"]["pdf"]
    )
    for op in ("read_pdf_fields", "read_pdf_field", "update_pdf_fields"):
        schema = request_schema(op)
        Draft202012Validator.check_schema(schema)
        assert schema["properties"]["op"]["const"] == op
    schema = request_schema("update_pdf_fields")
    assert set(schema["properties"]) == {
        "op",
        "asset_id",
        "expected_revision",
        "pdf_fields_update",
    }
    assert "PdfFieldCreate" in schema["$defs"]


def test_hidden_update_history_selection_and_complete_noop_result(managed_fields):
    service, asset, source = managed_fields
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    old = read(service, asset, "person.hidden")
    ref = old["evidence"]
    selected = _call(
        service,
        op="read_selection",
        reference=ref,
        selection={"pointer": "/inherited_entries/~1V/text"},
    )["evidence"]
    result = update(service, asset, [hidden_edit(old, "008")])
    current = result["asset"]
    complete_result = complete(service, **result["review_request"])
    assert complete_result["operation_result"]["changes"][0]["before"] == {
        k: v for k, v in old.items() if k != "evidence"
    }
    new = read(service, current, "person.hidden")
    assert new["inherited_entries"]["/V"]["text"] == "008"
    assert _call(service, op="verify", reference=ref)["checks"][
        "field_representation_hash"
    ]
    assert _call(service, op="verify", reference=selected)["valid"]
    assert read(service, asset, "person.hidden") == old
    noop = update(service, current, [hidden_edit(new, "008")])
    assert noop["asset"]["revision"] == current["revision"]
    assert not noop["operation_result"]["committed"]
    assert noop["operation_result"]["full_result_in"] == "operation_result.full_result"
    full = noop["operation_result"]["full_result"]
    assert full["changes"] == []
    assert "unchanged_native_graph_no_serialization" in full["checks"]
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    assert complete(service, **noop["review_request"]) == complete_result
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (original, mtime)


def test_duplicate_names_and_all_widgets_keep_separate_evidence(managed_fields):
    service, asset, source = managed_fields
    first = read(service, asset, "duplicate", 0)
    second = read(service, asset, "duplicate", 1)
    assert first["evidence"]["locator"] != second["evidence"]["locator"]
    shared = read(service, asset, "across")
    assert len(shared["widgets"]) == 2
    result = update(
        service,
        asset,
        [
            {
                "op": "update",
                "reference": shared["evidence"],
                "value": {"kind": "text", "text": "中文 007 µg α"},
                "appearance_policy": "replace_all_widget_appearances",
                "widget_styles": [
                    {
                        "widget_path": w["tree_path"],
                        "style": {"font_size": 8, "border_width": 0},
                    }
                    for w in shared["widgets"]
                ],
            }
        ],
    )
    new = read(service, result["asset"], "across")
    assert new["inherited_entries"]["/V"]["text"] == "中文 007 µg α"
    assert len(new["widgets"]) == 2
    receipt = complete(service, **result["review_request"])["operation_result"]
    assert receipt["changes"][0]["after"] == {
        k: v for k, v in new.items() if k != "evidence"
    }
    assert receipt["changes"][-1]["affected_pages"] == [0, 2]
    for index, before in enumerate((first, second)):
        after = read(service, result["asset"], "duplicate", index)
        after_value = after["inherited_entries"]["/V"]
        before_value = before["inherited_entries"]["/V"]
        assert after_value["native_graph"] == before_value["native_graph"]
        assert after_value["text"] == before_value["text"]
        assert after_value["source"]["field"] == after["locator"]
        assert _call(service, op="verify", reference=before["evidence"])["valid"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == asset["revision"]


def test_create_nested_group_and_delete_retains_every_removed_record(managed_fields):
    service, asset, source = managed_fields
    result = update(service, asset, [create_edit(source, asset)])
    created = result["asset"]
    group = read(service, created, "created-group")
    leaf = read(service, created, "created-group.value")
    assert len(leaf["widgets"]) == 2
    removed = update(
        service,
        created,
        [
            {
                "op": "delete",
                "reference": group["evidence"],
                "scope": "field_subtree_and_all_widgets",
            }
        ],
    )
    full = complete(service, **removed["review_request"])
    assert full["catalog"]["field_count"] == catalog(service, asset)["field_count"]
    records = full["operation_result"]["changes"][0]["deleted_fields"]
    assert {r["qualified_name"] for r in records} == {
        "created-group",
        "created-group.value",
    }
    for record in (group, leaf):
        assert _call(service, op="verify", reference=record["evidence"])["valid"]
        assert read(service, created, record["qualified_name"]) == record
    assert len(service.repository.load(asset["asset_id"]).history) == 3


@pytest.mark.parametrize(
    "target", ["update", "delete", "parent", "first_widget", "last_widget"]
)
@pytest.mark.parametrize(
    "member,replacement", [("asset_id", "file_" + "b" * 32), ("revision", "f" * 64)]
)
def test_every_reference_is_checked_before_adapter_or_commit(
    managed_fields, monkeypatch, target, member, replacement
):
    service, asset, source = managed_fields
    parent = read(service, asset, "person")
    hidden = read(service, asset, "person.hidden")
    if target == "update":
        edit = hidden_edit(hidden, "008")
        ref = edit["reference"]
    elif target == "delete":
        edit = {
            "op": "delete",
            "reference": hidden["evidence"],
            "scope": "field_subtree_and_all_widgets",
        }
        ref = edit["reference"]
    else:
        edit = create_edit(source, asset, parent)
        ref = (
            edit["parent_reference"]
            if target == "parent"
            else edit["field"]["widgets"][0 if target == "first_widget" else 1][
                "page_reference"
            ]
        )
    ref[member] = replacement
    monkeypatch.setattr(
        service.pdfs,
        "edit_fields",
        lambda *_: pytest.fail("Invalid reference reached native mutation"),
    )
    with pytest.raises(ValueError, match="different asset or revision"):
        update(service, asset, [edit])
    assert len(service.repository.load(asset["asset_id"]).history) == 1
    assert hashlib.sha256(source.read_bytes()).hexdigest() == asset["revision"]


def test_text_continuations_require_the_same_complete_response(managed_fields):
    service, asset, _ = managed_fields
    request = {
        "op": "read_pdf_fields",
        "asset_id": asset["asset_id"],
        "revision": asset["revision"],
        "text_limit": 79,
    }
    first = _call(service, **request)
    offset = first["next_text_offset"]
    assert offset is not None
    with pytest.raises(ValueError, match="requires pdf_field_text_sha256"):
        _call(service, **request, text_offset=offset)
    with pytest.raises(ValueError, match="changed"):
        _call(service, **request, text_offset=offset, pdf_field_text_sha256="0" * 64)
    second = _call(
        service,
        **request,
        text_offset=offset,
        pdf_field_text_sha256=first["text_sha256"],
    )
    assert second["excerpt_char_range"][0] == offset
    assert second["text_sha256"] == first["text_sha256"]


def test_stale_or_tampered_field_batch_never_creates_history(managed_fields):
    service, asset, _ = managed_fields
    hidden = read(service, asset, "person.hidden")
    edit = hidden_edit(hidden, "008")
    tampered = copy.deepcopy(edit)
    tampered["reference"]["value_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="Stale"):
        update(service, asset, [tampered])
    first = update(service, asset, [edit])
    with pytest.raises(ValueError, match="stale"):
        update(service, asset, [edit])
    assert (
        service.repository.load(asset["asset_id"]).revision
        == first["asset"]["revision"]
    )
    assert len(service.repository.load(asset["asset_id"]).history) == 2
