"""SDK2 drives totals remove/reuse/keep with complete pinned historical readback."""

import io
import os
import sys

import openpyxl
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_shape_stdio import native
from tests.integration.test_native_workbook_stdio import read_workbook
from tests.native_grid_helpers import table_workbook


@pytest.mark.timeout(120)
async def test_totals_lifecycle_preserves_historical_evidence_over_sdk2(tmp_path):
    source = tmp_path / "source.xlsx"
    original = table_workbook(totals=True)
    source.write_bytes(original)
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
        assert contract["table_totals_lifecycle_enabled"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        baseline = await read_workbook(client, asset)
        old = (
            await native(
                client,
                op="read_cell",
                asset_id=asset["asset_id"],
                revision=asset["revision"],
                sheet="Data",
                cell="B6",
            )
        )["cell"]["evidence"]
        current, current_read = asset, baseline
        for intent, ref in [
            ({"action": "remove", "cells": "clear"}, "A2:C5"),
            ({"action": "add", "cell_styles": "last_data_row"}, "A2:C6"),
            ({"action": "remove", "cells": "keep_cells"}, "A2:C5"),
        ]:
            selected = current_read["tables"][0]
            result = await native(
                client,
                op="update_workbook_table",
                asset_id=asset["asset_id"],
                expected_revision=current["revision"],
                table_update={
                    "worksheet": baseline["worksheets"][0]["key"],
                    "part": selected["part"],
                    "expected_ref": selected["attributes"]["ref"],
                    "totals_row": intent,
                },
            )
            assert result["success"] and not result["source_written"]
            current = result["asset"]
            current_read = await read_workbook(client, current)
            assert current_read["tables"][0]["attributes"]["ref"] == ref
            change = current_read["operation_result"]["changes"][0]
            assert change["totals_transition"]["action"] == intent["action"]
            assert not change["totals_transition"]["worksheet_rows_moved"]
        assert current["revision_count"] == 4
        proof = await native(client, op="verify", reference=old)
        assert proof["valid"] and not proof["is_current_managed_revision"]
        assert await read_workbook(client, asset) == baseline
        stale = await native(
            client,
            op="update_workbook_table",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            table_update={
                "worksheet": baseline["worksheets"][0]["key"],
                "part": baseline["tables"][0]["part"],
                "expected_ref": "A2:C6",
                "totals_row": {"action": "remove", "cells": "clear"},
            },
        )
        assert not stale["success"]
        path = tmp_path / "verified.xlsx"
        published = await native(
            client,
            op="publish",
            asset_id=asset["asset_id"],
            expected_revision=current["revision"],
            output_path=str(path),
        )
        assert published["success"]
    assert source.read_bytes() == original
    book = openpyxl.load_workbook(io.BytesIO(path.read_bytes()))
    try:
        assert book["Data"].tables["Table1"].ref == "A2:C5"
        assert book["Data"]["B6"].value == "=SUBTOTAL(109,'Data'!$B$3:$B$5)"
        assert book["Data"]["C6"].value == "Total"
        assert book["Data"]["B6"].style_id == book["Data"]["B5"].style_id
    finally:
        book.close()
