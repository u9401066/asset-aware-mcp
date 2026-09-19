"""Real SDK2 grid edits retain native objects, paged receipts and historical evidence."""

import io
import os
import sys

import openpyxl
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_shape_stdio import native
from tests.integration.test_native_workbook_stdio import read_workbook
from tests.native_workbook_helpers import _parts, build_workbook


@pytest.mark.timeout(120)
async def test_native_grid_over_sdk2(tmp_path):
    source = tmp_path / "original.xlsx"
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
        contract = await native(client, op="contract", for_op="update_worksheet_grid")
        assert contract["workbook_grid_enabled"]
        assert "update_worksheet_grid" in contract["formats"]["xlsx"]
        first = asset = (await native(client, op="register", source_path=str(source)))[
            "asset"
        ]
        evidence = (
            await native(
                client,
                op="read_cell",
                asset_id=asset["asset_id"],
                sheet="Data",
                cell="A1",
            )
        )["cell"]["evidence"]
        initial = await read_workbook(client, asset)
        key = initial["worksheets"][0]["key"]
        result = await native(
            client,
            op="update_worksheet_grid",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            worksheet_grid={
                "worksheet": key,
                "edits": [
                    {"axis": "row", "operation": "insert", "at": 1},
                    {"axis": "column", "operation": "insert", "at": 2},
                ],
            },
        )
        assert result["success"] and not result["source_written"]
        asset = result["asset"]
        reviewed = await read_workbook(client, asset)
        changes = reviewed["operation_result"]["changes"][0]
        assert (
            changes["operation"] == "update_worksheet_grid"
            and len(changes["edits"]) == 2
        )
        assert changes["edits"][0]["objects"]["comments"][0]["after_cell"] == "A2"
        stale = await native(
            client,
            op="update_worksheet_grid",
            asset_id=asset["asset_id"],
            expected_revision=first["revision"],
            worksheet_grid={
                "worksheet": key,
                "edits": [{"axis": "row", "operation": "delete", "at": 2}],
            },
        )
        assert stale["success"] is False
        assert await read_workbook(client, first) == initial
        verified = await native(client, op="verify", reference=evidence)
        assert verified["valid"] and not verified["is_current_managed_revision"]
        output = tmp_path / "grid-edited.xlsx"
        assert (
            await native(
                client,
                op="publish",
                asset_id=asset["asset_id"],
                expected_revision=asset["revision"],
                output_path=str(output),
            )
        )["success"]
    book = openpyxl.load_workbook(io.BytesIO(output.read_bytes()))
    sheet = book["Data"]
    assert (
        sheet["A2"].value == "Original"
        and sheet["A2"].comment.text == "Keep this comment"
    )
    assert sheet["C3"].value == "=A3*2"
    assert sheet.tables["Table1"].ref == "A9:C11"
    assert sheet["B9"].value == "Column2"
    assert str(sheet.merged_cells) == "A6:E7"
    assert sheet["D4"].hyperlink.target == "https://example.com"
    assert book["Other"]["B1"].value == "=Data!A3"
    for part in ("xl/styles.xml", "xl/theme/theme1.xml", "customXml/item1.xml"):
        assert _parts(output.read_bytes())[part] == _parts(original)[part]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
