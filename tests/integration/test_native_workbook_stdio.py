"""Real SDK2 worksheet lifecycle, full JSON reads and historical evidence."""

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
from tests.integration.test_native_selection_stdio import selected
from tests.native_workbook_helpers import _parts, build_workbook


async def read_workbook(client, asset, view="references"):
    chunks, offset, sha = [], 0, None
    while True:
        result = await native(
            client,
            op="read_workbook",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            workbook_view=view,
            text_offset=offset,
            text_limit=1000,
        )
        assert result["success"]
        sha = sha or result["text_sha256"]
        assert result["text_sha256"] == sha
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
    return json.loads(text)


@pytest.mark.timeout(120)
async def test_native_workbook_structure_over_sdk2(tmp_path):
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
        contract = await native(client, op="contract", for_op="rename_worksheet")
        assert contract["workbook_structure_enabled"]
        assert "delete_worksheets" in contract["formats"]["xlsx"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        first = dict(asset)
        parent = (
            await native(
                client,
                op="read_cell",
                asset_id=asset["asset_id"],
                sheet="Data",
                cell="A1",
            )
        )["cell"]["evidence"]
        evidence = (await selected(client, parent, {"pointer": "/value"}))["evidence"]
        for op in (
            "add_worksheets",
            "rename_worksheet",
            "reorder_worksheets",
            "delete_worksheets",
        ):
            record = await read_workbook(client, asset)
            sheets = record["worksheets"]
            if op == "add_worksheets":
                args = {"worksheet_insert": {"index": 0, "names": ["Temporary"]}}
            elif op == "rename_worksheet":
                args = {
                    "worksheet_rename": {
                        "key": next(s["key"] for s in sheets if s["name"] == "Data"),
                        "name": "研究 O'Brien",
                    }
                }
            elif op == "reorder_worksheets":
                args = {"worksheet_order": [s["key"] for s in reversed(sheets)]}
            else:
                args = {
                    "worksheet_keys": [
                        s["key"] for s in sheets if s["name"] == "Temporary"
                    ]
                }
            result = await native(
                client,
                op=op,
                asset_id=asset["asset_id"],
                expected_revision=asset["revision"],
                **args,
            )
            assert result["success"] and not result["source_written"]
            asset = result["asset"]
        final = await read_workbook(client, asset)
        assert [s["name"] for s in final["worksheets"]] == ["Other", "研究 O'Brien"]
        assert final["operation_result"]["changes"][0]["secure_erasure"] is False
        assert [
            s["name"] for s in (await read_workbook(client, first))["worksheets"]
        ] == ["Data", "Other"]
        proof = await native(client, op="verify", reference=evidence)
        assert proof["valid"] and not proof["is_current_managed_revision"]
        assert (await selected(client, evidence))["value"] == "Original"
        output = tmp_path / "published.xlsx"
        result = await native(
            client,
            op="publish",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            output_path=str(output),
        )
        assert result["success"]
    independent = openpyxl.load_workbook(io.BytesIO(output.read_bytes()))
    assert independent.sheetnames == ["Other", "研究 O'Brien"]
    assert independent["Other"]["B1"].value == "='研究 O''Brien'!A2"
    assert (
        _parts(output.read_bytes())["xl/worksheets/sheet1.xml"]
        == _parts(original)["xl/worksheets/sheet1.xml"]
    )
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
