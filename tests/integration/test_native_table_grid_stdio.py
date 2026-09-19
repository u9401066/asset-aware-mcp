"""Actual SDK2 native/A2T structural correspondence and typed column defaults."""

import io
import os
import sys

import openpyxl
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_shape_stdio import native
from tests.integration.test_native_table_stdio import read_workspace
from tests.integration.test_native_workbook_stdio import read_workbook
from tests.native_workbook_helpers import build_workbook


async def table_call(client, tool, **arguments):
    result = await client.call_tool(tool, arguments)
    text = "".join(block.text for block in result.content)
    assert not result.is_error and "❌" not in text, text
    return text


@pytest.mark.timeout(120)
async def test_structural_a2t_grid_roundtrip_over_sdk2(tmp_path):
    source = tmp_path / "source.xlsx"
    before = build_workbook()
    source.write_bytes(before)
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
        contract = await native(client, op="contract", for_op="apply_table_workspace")
        assert contract["table_grid_apply_enabled"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        original = await read_workbook(client, asset)
        projected = await native(
            client,
            op="project_workbook_table",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            table_projection={
                "worksheet": original["worksheets"][0]["key"],
                "start_cell": "A1",
                "end_cell": "E3",
            },
        )
        table_id = projected["table_id"]
        initial, old_hash = await read_workspace(client, table_id)
        await table_call(
            client,
            "table_data",
            operation="delete_row",
            table_id=table_id,
            row_id=initial["table"]["row_ids"][0],
        )
        await table_call(
            client,
            "table_manage",
            operation="remove_column",
            table_id=table_id,
            column_name="C",
        )
        await table_call(
            client,
            "table_manage",
            operation="add_column",
            table_id=table_id,
            column_name="Review",
            column_type="native",
            default_value={"kind": "string", "value": "checked"},
        )
        await table_call(
            client,
            "table_data",
            operation="add_rows",
            table_id=table_id,
            rows=[
                {
                    "A": {"kind": "number", "value": 30},
                    "Review": {"kind": "string", "value": "new"},
                }
            ],
        )
        current, digest = await read_workspace(client, table_id)
        assert digest != old_hash
        args = {
            "op": "apply_table_workspace",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "table_id": table_id,
            "worksheet_grid": current["structural_plan"]["worksheet_grid"],
        }
        assert not (await native(client, **args, expected_table_sha256=old_hash))[
            "success"
        ]
        result = await native(client, **args, expected_table_sha256=digest)
        assert result["success"] and not result["source_written"]
        record = await read_workbook(client, result["asset"])
        assert (
            record["operation_result"]["changes"][-1]["workspace_reference"]
            == result["workspace_reference"]
        )
        assert await read_workspace(
            client, table_id, workspace_reference=result["workspace_reference"]
        ) == (current, digest)
        assert (
            await native(
                client,
                op="verify",
                reference=initial["source_cells"][0]["source"]["evidence"],
            )
        )["valid"]
        assert not (await native(client, **args, expected_table_sha256=digest))[
            "success"
        ]
        assert (
            await native(
                client,
                op="publish",
                asset_id=asset["asset_id"],
                expected_revision=result["asset"]["revision"],
                output_path=str(tmp_path / "result.xlsx"),
            )
        )["success"]
    book = openpyxl.load_workbook(
        io.BytesIO((tmp_path / "result.xlsx").read_bytes()), rich_text=True
    )
    assert book["Data"]["A1"].value == 10 and book["Data"]["A3"].value == 30
    assert book["Data"]["B1"].value == "=A1*2"
    assert type(book["Data"]["C1"].value).__name__ == "CellRichText"
    assert book["Data"]["A1"].number_format == "$0.00"
    assert [book["Data"][f"E{row}"].value for row in range(1, 4)] == [
        "checked",
        "checked",
        "new",
    ]
    assert source.read_bytes() == before and source.stat().st_mtime_ns == mtime
