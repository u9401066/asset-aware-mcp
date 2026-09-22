"""Real SDK2 field CRUD retains full evidence, receipts, images and source bytes."""

import copy
import hashlib
import json
import os
import sys
from functools import partial
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_docx_stdio_e2e import _native
from tests.integration.test_native_pdf_annotations_stdio import actual_pages
from tests.integration.test_native_pdf_annotations_stdio import (
    complete as contract_read,
)
from tests.native_pdf_field_helpers import form_pdf


async def full(native, request):
    chunks, offset, sha = [], 0, None
    while True:
        result = await native(
            **request,
            text_offset=offset,
            text_limit=4000,
            **({"pdf_field_text_sha256": sha} if sha else {}),
        )
        assert result["success"] and "response_truncated" not in result, result
        sha = sha or result["text_sha256"]
        assert result["text_sha256"] == sha
        assert result["excerpt_char_range"][0] == offset
        chunks.append(result["text_excerpt"])
        offset = result["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert len(text) == result["text_length"]
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    return json.loads(text)


async def field(native, asset, catalog, name):
    entry = next(item for item in catalog["fields"] if item["qualified_name"] == name)
    response = await full(
        native,
        {
            "op": "read_pdf_field",
            "asset_id": asset["asset_id"],
            "revision": asset["revision"],
            "pdf_field_locator": entry["locator"],
        },
    )
    return response["field"]


@pytest.mark.parametrize("surface", ["balanced", "compact"])
@pytest.mark.timeout(420)
async def test_native_pdf_field_crud_over_real_sdk2_stdio(tmp_path, surface):
    source = tmp_path / "欄位.pdf"
    original = form_pdf()
    source.write_bytes(original)
    mtime = source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
            "ASSET_AWARE_MCP_TOOL_SURFACE": surface,
        },
    )
    async with Client(stdio_client(params)) as client:
        native = partial(_native, client)
        contract = await native(op="contract", for_op="update_pdf_fields")
        assert contract["pdf_fields_enabled"]
        details = await contract_read(native, contract["contract_request"])
        assert "pdf_field_text_sha256" in details["pdf_fields_policy"]
        schema = await contract_read(native, contract["schema_request"])
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        asset = (await native(op="register", source_path=str(source)))["asset"]
        initial = asset.copy()
        read_request = {
            "op": "read_pdf_fields",
            "asset_id": asset["asset_id"],
            "revision": asset["revision"],
        }
        before = await full(native, read_request)
        assert (
            before["catalog"]["field_count"] == 7 and before["operation_result"] is None
        )
        first = await native(**read_request, text_limit=79)
        assert not (
            await native(**read_request, text_offset=first["next_text_offset"])
        )["success"]
        assert not (
            await native(
                **read_request,
                text_offset=first["next_text_offset"],
                pdf_field_text_sha256="f" * 64,
            )
        )["success"]
        old = await field(native, asset, before["catalog"], "person.hidden")
        selected = (
            await native(
                op="read_selection",
                reference=old["evidence"],
                selection={"pointer": "/inherited_entries/~1V/text"},
            )
        )["evidence"]
        pages = await actual_pages(client, native, asset, original)
        wiki = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        old_root = Path(wiki["output_dir"])
        old_files = {p.name: p.read_bytes() for p in old_root.iterdir()}
        revisions = tmp_path / "data/native-assets" / asset["asset_id"] / "revisions"
        catalog = before["catalog"]

        def change_request(edits):
            request = {
                "op": "update_pdf_fields",
                "asset_id": asset["asset_id"],
                "expected_revision": asset["revision"],
                "pdf_fields_update": {
                    "expected_catalog_sha256": catalog["catalog_sha256"],
                    "edits": edits,
                },
            }
            validator.validate(request)
            return request

        hidden_edit = {
            "op": "update",
            "reference": old["evidence"],
            "value": {"kind": "text", "text": "007"},
            "appearance_policy": "no_widgets",
        }
        noop = await native(**change_request([hidden_edit]))
        assert noop["success"] and not noop["operation_result"]["committed"]
        assert noop["operation_result"]["full_result"]["changes"] == []
        foreign = copy.deepcopy(hidden_edit)
        foreign["reference"]["asset_id"] = "file_" + "b" * 32
        assert not (await native(**change_request([foreign])))["success"]

        async def change(edits):
            nonlocal asset, catalog
            request = change_request(edits)
            result = await native(**request)
            assert result["success"], result
            assert not result["source_written"]
            asset = result["asset"]
            response = await full(native, result["review_request"])
            catalog = response["catalog"]
            assert response["operation_result"]["changes"]
            return request, response

        hidden_edit["value"]["text"] = "008"
        stale, _ = await change([hidden_edit])
        assert not (await native(**stale))["success"]
        hidden = await field(native, asset, catalog, "person.hidden")
        assert hidden["inherited_entries"]["/V"]["text"] == "008"
        # Page references must be reacquired after any new native revision.
        updated_bytes = (revisions / asset["revision"]).read_bytes()
        pages = await actual_pages(client, native, asset, updated_bytes)
        _, created_response = await change(
            [
                {
                    "op": "create",
                    "new_groups": ["sdk"],
                    "field": {
                        "name": "value",
                        "kind": "text",
                        "value": {"kind": "text", "text": "中文 009 µg β"},
                        "widgets": [
                            {
                                "page_reference": pages[i]["evidence"],
                                "rect": [0.1, 0.6, 0.85, 0.75],
                                "style": {"font_size": 8, "border_width": 0},
                            }
                            for i in (0, 2)
                        ],
                    },
                }
            ]
        )
        created_asset = asset.copy()
        created = await field(native, asset, catalog, "sdk.value")
        assert created["inherited_entries"]["/V"]["text"] == "中文 009 µg β"
        assert len(created["widgets"]) == 2
        assert catalog["field_count"] == 9
        await actual_pages(
            client, native, asset, (revisions / asset["revision"]).read_bytes()
        )
        exported = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
            citation_contract={
                "name": "SDK fields",
                "inline_template": "欄位【{locator}】",
                "reference_template": "{title}: {locator}",
            },
        )
        root = Path(exported["output_dir"])
        manifest = json.loads((root / "manifest.json").read_text())
        assert manifest["field_count"] == 9
        assert (
            json.loads((root / manifest["operation_result_file"]).read_text())
            == created_response["operation_result"]
        )
        records = [
            json.loads(line)
            for line in (root / "fields.jsonl").read_text().splitlines()
        ]
        wiki_field = next(
            item for item in records if item["qualified_name"] == "sdk.value"
        )
        assert wiki_field["evidence"] == created["evidence"]
        assert [p["page_index"] for p in wiki_field["page_links"]] == [0, 2]
        assert "欄位【PDF field path" in wiki_field["citation_presentation"]["inline"]
        group = await field(native, asset, catalog, "sdk")
        _, deleted = await change(
            [
                {
                    "op": "delete",
                    "reference": group["evidence"],
                    "scope": "field_subtree_and_all_widgets",
                }
            ]
        )
        assert catalog["field_count"] == 7
        assert len(deleted["operation_result"]["changes"][0]["deleted_fields"]) == 2
        await actual_pages(
            client, native, asset, (revisions / asset["revision"]).read_bytes()
        )
        for reference in (
            old["evidence"],
            selected,
            created["evidence"],
            group["evidence"],
        ):
            checked = await native(op="verify", reference=reference)
            assert checked["valid"] and not checked["is_current_managed_revision"]
        historical = await field(
            native, created_asset, created_response["catalog"], "sdk.value"
        )
        assert historical == created
        assert await full(native, read_request) == before
        assert (
            await native(
                op="export_wiki",
                asset_id=initial["asset_id"],
                revision=initial["revision"],
                output_dir=str(tmp_path / "wiki"),
            )
        )["output_dir"] == str(old_root)
        assert old_files == {p.name: p.read_bytes() for p in old_root.iterdir()}
        assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
