"""SDK2 transport covers typed table edits and immutable native/A2T lineage."""

import hashlib
import io
import json
import os
import sys

import openpyxl
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_shape_stdio import native
from tests.integration.test_native_workbook_stdio import read_workbook
from tests.native_workbook_helpers import _parts, build_workbook


async def read_workspace(client, table_id, **kwargs):
    chunks, offset, digest, text_hash = [], 0, None, None
    while True:
        result = await native(
            client,
            op="read_table_workspace",
            table_id=table_id,
            text_offset=offset,
            text_limit=1300,
            table_sha256=digest,
            **kwargs,
        )
        assert result["success"]
        digest = digest or result["table_sha256"]
        text_hash = text_hash or result["text_sha256"]
        assert result["table_sha256"] == digest and result["text_sha256"] == text_hash
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    data = "".join(chunks).encode("utf-8")
    assert hashlib.sha256(data).hexdigest() == text_hash
    return json.loads(data), digest


@pytest.mark.timeout(120)
async def test_native_table_roundtrip_over_sdk2(tmp_path):
    source = tmp_path / "rich.xlsx"
    original = build_workbook()
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
            "ASSET_AWARE_MCP_TOOL_SURFACE": "balanced",
        },
    )
    async with Client(stdio_client(params)) as client:
        contract = await native(client, op="contract", for_op="project_workbook_table")
        assert contract["table_workspaces_enabled"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        key = (await read_workbook(client, asset))["worksheets"][0]["key"]
        projected = await native(
            client,
            op="project_workbook_table",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            table_projection={"worksheet": key, "start_cell": "A1", "end_cell": "E3"},
        )
        table_id = projected["table_id"]
        initial, initial_hash = await read_workspace(client, table_id)
        assert len(initial["source_cells"]) == 15
        edited = await client.call_tool(
            "table_data",
            {
                "operation": "update_cell",
                "table_id": table_id,
                "row_id": initial["table"]["row_ids"][0],
                "column_name": "E",
                "value": {"kind": "string", "value": "007"},
            },
        )
        assert not edited.is_error
        assert "Cell updated" in "".join(block.text for block in edited.content)
        current, digest = await read_workspace(client, table_id)
        assert (
            digest != initial_hash
            and current["table"]["rows"][0]["E"]["value"] == "007"
        )
        args = {
            "op": "apply_table_workspace",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "table_id": table_id,
        }
        stale = await native(client, **args, expected_table_sha256=initial_hash)
        assert not stale["success"]
        applied = await native(client, **args, expected_table_sha256=digest)
        assert (
            applied["success"] and applied["changed"] and not applied["source_written"]
        )
        record = await read_workbook(client, applied["asset"])
        event = record["operation_result"]["changes"][-1]
        assert event["workspace_reference"] == applied["workspace_reference"]
        assert (
            await native(client, op="verify", reference=event["workspace_reference"])
        )["valid"]
        made = await native(
            client,
            op="create_workbook_from_table",
            table_id=table_id,
            expected_table_sha256=digest,
            workspace_reference=event["workspace_reference"],
            table_workbook={"name": "independent.xlsx"},
        )
        assert made["success"]
        # Mutate the live table; a pinned snapshot must still return the applied input.
        await client.call_tool(
            "table_data",
            {
                "operation": "update_cell",
                "table_id": table_id,
                "row_index": 0,
                "column_name": "E",
                "value": {"kind": "string", "value": "008"},
            },
        )
        assert await read_workspace(
            client, table_id, workspace_reference=event["workspace_reference"]
        ) == (current, digest)
        for name, item in (("applied.xlsx", applied), ("independent.xlsx", made)):
            published = await native(
                client,
                op="publish",
                asset_id=item["asset"]["asset_id"],
                expected_revision=item["asset"]["revision"],
                output_path=str(tmp_path / name),
            )
            assert published["success"]
    final = (tmp_path / "applied.xlsx").read_bytes()
    assert openpyxl.load_workbook(io.BytesIO(final))["Data"]["E1"].value == "007"
    assert (
        openpyxl.load_workbook(tmp_path / "independent.xlsx")["Data"]["E1"].data_type
        == "s"
    )
    before, after = _parts(original), _parts(final)
    assert all(
        before[name] == after[name]
        for name in before
        if name not in {"xl/worksheets/sheet1.xml", "xl/workbook.xml"}
    )
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
