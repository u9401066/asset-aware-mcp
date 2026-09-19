"""SDK2 discovers Table edits, preserves historical evidence and commits once."""

import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_shape_stdio import native
from tests.integration.test_native_workbook_stdio import read_workbook
from tests.native_grid_helpers import table_workbook
from tests.unit.test_native_grid_tables import read, table
from tests.unit.test_native_workbook_table_edit import column, request


@pytest.mark.timeout(120)
async def test_table_metadata_and_cells_over_sdk2(tmp_path):
    source = tmp_path / "source.xlsx"
    original = table_workbook(totals=True)
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
        contract = await native(client, op="contract", for_op="update_workbook_table")
        assert contract["workbook_table_edit_enabled"]
        assert "update_workbook_table" in contract["formats"]["xlsx"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        before = await read_workbook(client, asset)
        old = (
            await native(
                client,
                op="read_cell",
                asset_id=asset["asset_id"],
                revision=asset["revision"],
                sheet="Data",
                cell="A2",
            )
        )["cell"]["evidence"]
        assert not (
            await native(
                client,
                op="update",
                asset_id=asset["asset_id"],
                expected_revision=asset["revision"],
                edits=[
                    {"sheet": "Data", "cell": "A2", "kind": "string", "value": "Amount"}
                ],
            )
        )["success"]
        update = request(
            column(name="Amount"),
            column(
                2,
                "Calc",
                calculated={"formula": "=[@Amount]*3", "policy": "require_matching"},
                totals={"kind": "function", "value": "sum"},
            ),
            ref="A2:C6",
        ).model_dump()
        args = {
            "op": "update_workbook_table",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "table_update": update,
        }
        stale = {**update, "expected_ref": "A1:C6"}
        assert not (await native(client, **{**args, "table_update": stale}))["success"]
        result = await native(client, **args)
        assert result["success"] and not result["source_written"]
        assert result["asset"]["revision_count"] == 2
        current = await read_workbook(client, result["asset"])
        assert current["worksheets"] == before["worksheets"]
        receipt = current["operation_result"]["changes"][0]
        assert receipt["operation"] == "update_workbook_table"
        assert receipt["request"] == update
        assert receipt["cells"]["A2"]["before"]["value"] == "Input"
        assert receipt["cells"]["A2"]["after"]["value"] == "Amount"
        assert (await native(client, op="verify", reference=old))["valid"]
        assert not (await native(client, **args))["success"]
        target = tmp_path / "result.xlsx"
        assert (
            await native(
                client,
                op="publish",
                asset_id=asset["asset_id"],
                expected_revision=result["asset"]["revision"],
                output_path=str(target),
            )
        )["success"]
        historical = await read_workbook(client, asset)
        assert historical == before
    output = target.read_bytes()
    assert table(output).get("ref") == "A2:C6"
    assert read(output, "A2")["value"] == "Amount"
    assert read(output, "B4")["value"] == "=[@Amount]*3"
    assert read(output, "B6")["value"] == "=SUBTOTAL(109,[Calc])"
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
