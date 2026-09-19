"""SDK2 transport: sequential table-grid edits, stale refs, wiki and source backup."""

import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_picture_stdio import publish_and_writeback
from tests.integration.test_native_pptx_shape_stdio import native, read_complete
from tests.native_pptx_grid_helpers import grid_fixture, texts


@pytest.mark.timeout(120)
async def test_table_grid_crud_over_real_sdk2(tmp_path):
    data, ref, _ = grid_fixture(merge="rectangle")
    source = tmp_path / "source.pptx"
    source.write_bytes(data)
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
        contract = await native(client, op="contract", for_op="update_pptx_table_grid")
        assert "update_pptx_table_grid" in contract["formats"]["pptx"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        old = await read_complete(client, asset, ref["locator"])
        args = {
            "op": "update_pptx_table_grid",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "pptx_table_grid": {
                "reference": old["evidence"],
                "edits": [
                    {"op": "insert", "axis": "column", "index": 1, "sizes": [300000]},
                    {"op": "delete", "axis": "row", "index": 0, "count": 1},
                    {"op": "resize", "axis": "row", "index": 0, "sizes": [900000]},
                ],
            },
        }
        result = await native(client, **args)
        assert result["success"] and not result["source_written"]
        current = result["asset"]
        record = await read_complete(client, current, ref["locator"])
        assert len(record["table"]["rows"]) == 2
        assert len(record["table"]["rows"][0]["cells"]) == 4
        assert record["table"]["rows"][0]["attributes"]["h"] == "900000"
        assert record["table"]["rows"][0]["cells"][0]["attributes"]["gridSpan"] == "3"
        stale = await native(
            client, **{**args, "expected_revision": current["revision"]}
        )
        assert not stale["success"]
        proof = await native(client, op="verify", reference=old["evidence"])
        assert proof["valid"] and not proof["is_current_managed_revision"]
        assert source.read_bytes() == data
        target = tmp_path / "published.pptx"
        await publish_and_writeback(client, current, asset, source, target)
    assert texts(target.read_bytes()) == [
        ["樣本 & 結果", "", "", "-0.50\nmg/L"],
        ["A102", "", "12", "=SUM(A1:A2)"],
    ]
