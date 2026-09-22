"""Actual SDK2 ODS discovery, native cell CRUD, complete receipts and restart."""

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pdf_regions_stdio import native
from tests.native_ods_helpers import fixture, locator
from tests.unit.test_native_ods_dependencies import source as dependency_source


async def complete(client, **request):
    chunks, sha, offset = [], None, 0
    while True:
        page = await native(
            client,
            **request,
            text_offset=offset,
            text_limit=4000,
            **({"ods_text_sha256": sha} if sha else {}),
        )
        assert page["success"] and "response_truncated" not in page, page
        sha = sha or page["text_sha256"]
        assert page["text_sha256"] == sha and page["excerpt_char_range"][0] == offset
        chunks.append(page["text_excerpt"])
        if page["next_text_offset"] is None:
            break
        offset = page["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    return json.loads(text)


async def cell(client, asset, row=0, column=0, name="Sheet1"):
    return (
        await complete(
            client,
            op="read_ods_cell",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            ods_locator=locator(row, column, name).model_dump(),
        )
    )["cell"]


@pytest.mark.timeout(120)
async def test_native_ods_rename_discovery_dependencies_and_history_over_sdk2(tmp_path):
    source = tmp_path / "source.ods"
    source.write_bytes(dependency_source().package.original)
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
            "ASSET_AWARE_MCP_TOOL_SURFACE": "balanced",
        },
    )
    async with Client(stdio_client(params)) as client:
        contract = await native(client, op="contract", for_op="rename_ods_table")
        assert contract["ods_table_rename_enabled"]
        assert {"read_ods_dependencies", "rename_ods_table"} <= set(
            contract["formats"]["ods"]
        )
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        old = await cell(client, asset)
        dependencies_request = {
            "op": "read_ods_dependencies",
            "asset_id": asset["asset_id"],
            "revision": asset["revision"],
        }
        inventory = await complete(client, **dependencies_request)
        changed = await native(
            client,
            op="rename_ods_table",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            ods_table_rename={
                "table_index": 0,
                "table_name": "Sheet1",
                "new_name": "New 中文 O'Brien",
                "dependencies_sha256": inventory["inventory_sha256"],
            },
        )
        assert changed["success"] and changed["new_revision_created"], changed
        receipt = await complete(client, **changed["review_request"])
        assert (
            receipt["operation_result"]["changes"][0]["operation"] == "rename_ods_table"
        )
        current = await cell(client, changed["asset"], name="New 中文 O'Brien")
        assert 'LEN("[Sheet1.A1]")' in current["formula"]["expression"]
        fresh = await complete(client, **changed["dependencies_request"])
        assert fresh["sheets"] == ["New 中文 O'Brien"]
        assert fresh["inventory_sha256"] != inventory["inventory_sha256"]
    async with Client(stdio_client(params)) as client:
        assert await complete(client, **dependencies_request) == inventory
        assert await complete(client, **changed["review_request"]) == receipt
        assert await complete(client, **changed["dependencies_request"]) == fresh
        historical = await native(client, op="verify", reference=old["evidence"])
        assert historical["valid"] and not historical["is_current_managed_revision"]
        assert (await native(client, op="verify", reference=current["evidence"]))[
            "valid"
        ]
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (original, mtime)


@pytest.mark.timeout(120)
async def test_native_ods_operations_evidence_and_snapshot_survive_sdk2_restart(
    tmp_path,
):
    source = tmp_path / "source.ods"
    source.write_bytes(
        fixture(
            '<table:table-row><table:table-cell office:value-type="float" office:value="2"><text:p>2</text:p></table:table-cell><table:table-cell table:formula="of:=[.A1]*2" office:value-type="float" office:value="4"><text:p>4</text:p></table:table-cell></table:table-row>',
            extras={"styles.xml": b"<styles/>"},
        )
    )
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
            "ASSET_AWARE_MCP_TOOL_SURFACE": "balanced",
        },
    )
    async with Client(stdio_client(params)) as client:
        contract = await native(client, op="contract", for_op="update_ods")
        assert contract["success"] and contract["ods_enabled"]
        assert "response_truncated" not in contract
        assert "update_ods" in contract["formats"]["ods"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        old = await cell(client, asset)
        changed = await native(
            client,
            op="update_ods",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            ods_update={
                "cells": [
                    {
                        "reference": old["evidence"],
                        "value": {"kind": "float", "value": "3"},
                        "display_policy": "replace_paragraphs_preserve_cell_style",
                    }
                ]
            },
        )
        assert changed["success"], changed
        current = changed["asset"]
        full = await complete(client, **changed["review_request"], limit=1)
        assert full["next_offset"] == 1 and full["total_physical_records"] == 2
        assert (
            full["operation_result"]["changes"][1]["operation"]
            == "invalidate_typed_formula_cache"
        )
        assert (await complete(client, **changed["review_request"], offset=1, limit=1))[
            "next_offset"
        ] is None
        formula = await cell(client, current, column=1)
        assert formula["formula"]["expression"] == "=[.A1]*2"
        assert formula["value_type"] is None and not formula["cached_value_verified"]
        assert formula["display_paragraphs"] == [
            "4"
        ]  # Explicitly stale stored display.
        historical = await native(client, op="verify", reference=old["evidence"])
        assert historical["valid"] and not historical["is_current_managed_revision"]
        invalid = await native(
            client,
            op="update_ods",
            asset_id=asset["asset_id"],
            expected_revision=current["revision"],
            ods_update={
                "cells": [
                    {
                        "reference": old["evidence"],
                        "value": {"value": "stale"},
                        "display_policy": "replace_paragraphs_preserve_cell_style",
                    }
                ]
            },
        )
        assert not invalid["success"]
        wiki_request = {
            "op": "export_wiki",
            "asset_id": asset["asset_id"],
            "revision": current["revision"],
            "output_dir": str(tmp_path / "wiki"),
        }
        wiki = await native(client, **wiki_request)
        assert wiki["success"], wiki
        root = Path(wiki["output_dir"])
        wiki_bytes = {p.name: p.read_bytes() for p in root.iterdir()}
        assert (
            json.loads(wiki_bytes["operation-result.json"]) == full["operation_result"]
        )
        created = await native(
            client, op="create_ods", ods_create={"name": "獨立.ods", "tables": ["數據"]}
        )
        assert created["success"], created
        new = created["asset"]
        blank = await cell(client, new, 4, 3, "數據")
        authored = await native(
            client,
            op="update_ods",
            asset_id=new["asset_id"],
            expected_revision=new["revision"],
            ods_update={
                "cells": [
                    {
                        "reference": blank["evidence"],
                        "value": {"value": "=007"},
                        "display_policy": "replace_paragraphs_preserve_cell_style",
                    }
                ]
            },
        )
        assert authored["success"], authored
        authored_cell = await cell(client, authored["asset"], 4, 3, "數據")
        assert (
            authored_cell["formula"] is None
            and authored_cell["value_attributes"]["string-value"] == "=007"
        )
        output = tmp_path / "published.ods"
        assert (
            await native(
                client,
                op="publish",
                asset_id=asset["asset_id"],
                expected_revision=current["revision"],
                output_path=str(output),
            )
        )["success"]
        assert hashlib.sha256(output.read_bytes()).hexdigest() == current["revision"]
    async with Client(stdio_client(params)) as client:
        assert await complete(client, **changed["review_request"], limit=1) == full
        assert (await native(client, op="verify", reference=old["evidence"]))["valid"]
        assert (await native(client, op="verify", reference=authored_cell["evidence"]))[
            "valid"
        ]
        assert (await native(client, **wiki_request))["reused"]
        assert {p.name: p.read_bytes() for p in root.iterdir()} == wiki_bytes
    assert (source.read_bytes(), source.stat().st_mtime_ns) == (original, mtime)
