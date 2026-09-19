"""SDK2 agents can expand native tables from A2T with explicit generated values."""

import io
import os
import sys
from copy import deepcopy

import openpyxl
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_shape_stdio import native
from tests.integration.test_native_table_grid_stdio import table_call
from tests.integration.test_native_table_stdio import read_workspace
from tests.integration.test_native_workbook_stdio import read_workbook
from tests.native_grid_helpers import table_workbook


@pytest.mark.timeout(120)
async def test_native_table_membership_and_generation_over_sdk2(tmp_path):
    source = tmp_path / "source.xlsx"
    original = table_workbook(formula="=A3*2")
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
        contract = await native(client, op="contract", for_op="apply_table_workspace")
        assert (
            contract["table_expansion_enabled"] and contract["table_grid_apply_enabled"]
        )
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        before = await read_workbook(client, asset)
        projection = await native(
            client,
            op="project_workbook_table",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            table_projection={
                "worksheet": before["worksheets"][0]["key"],
                "start_cell": "A2",
                "end_cell": "C5",
            },
        )
        table_id = projection["table_id"]
        initial, initial_hash = await read_workspace(client, table_id)
        generated = {"kind": "native_generated", "value": None}
        await table_call(
            client,
            "table_data",
            operation="add_rows",
            table_id=table_id,
            rows=[{"A": {"kind": "number", "value": 40}, "B": generated}],
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
            operation="update_cell",
            table_id=table_id,
            row_id=initial["table"]["row_ids"][0],
            column_name="Review",
            value=generated,
        )
        current, digest = await read_workspace(client, table_id)
        grid = deepcopy(current["structural_plan"]["worksheet_grid"])
        for edit, ref in zip(grid["edits"], ["A2:C5", "A2:C6"], strict=True):
            edit["expand_tables"] = [
                {"part": "xl/tables/table1.xml", "expected_ref": ref}
            ]
        args = {
            "op": "apply_table_workspace",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "table_id": table_id,
            "worksheet_grid": grid,
        }
        assert not (await native(client, **args, expected_table_sha256=initial_hash))[
            "success"
        ]
        result = await native(client, **args, expected_table_sha256=digest)
        assert result["success"] and not result["source_written"]
        after = await read_workbook(client, result["asset"])
        grid_receipt = after["operation_result"]["changes"][0]
        assert grid_receipt["generated_table_cells"] == {
            "B6": "calculated",
            "D2": "header",
        }
        assert grid_receipt["edits"][-1]["tables"][0]["after"] == "A2:D6"
        assert (
            await native(
                client,
                op="verify",
                reference=initial["source_cells"][3]["source"]["evidence"],
            )
        )["valid"]
        assert await read_workspace(
            client, table_id, workspace_reference=result["workspace_reference"]
        ) == (current, digest)
        assert (
            await native(client, op="verify", reference=result["workspace_reference"])
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
    book = openpyxl.load_workbook(io.BytesIO((tmp_path / "result.xlsx").read_bytes()))
    table = book["Data"].tables["Table1"]
    assert table.ref == "A2:D6" and table.autoFilter.ref == "A2:D6"
    assert [col.id for col in table.tableColumns] == [1, 2, 3, 4]
    assert book["Data"]["B6"].value == "=A6*2" and book["Data"]["D2"].value == "Column4"
    assert book["Data"]["A6"].value == 40
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
