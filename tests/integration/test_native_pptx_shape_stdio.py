"""Real SDK2 transport: add, read, edit, delete, historical proof and publish."""

from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from pptx import Presentation

from tests.integration.test_native_asset_stdio_e2e import _unwrap
from tests.native_pptx_helpers import build_presentation, edit_run
from tests.native_pptx_shape_helpers import addition


async def native(client, **request):
    result = _unwrap(
        await client.call_tool("document", {"op": "native", "native_request": request})
    )
    assert "response_truncated" not in result
    return result


async def read_complete(client, asset, locator):
    offset, chunks, digest = 0, [], None
    while True:
        result = await native(
            client,
            op="read_pptx_shape",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            pptx_locator=locator,
            text_offset=offset,
            text_limit=1000,
        )
        shape = result["shape"]
        digest = digest or shape["text_sha256"]
        assert shape["text_sha256"] == digest
        chunks.append(shape["text_excerpt"])
        if shape["next_text_offset"] is None:
            break
        offset = shape["next_text_offset"]
    text = "".join(chunks)
    assert len(chunks) > 1
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


async def exercise_shapes(client, asset, data):
    added = await native(
        client,
        op="add_pptx_shapes",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        pptx_shapes=[addition(data).model_dump()],
    )
    assert added["success"] and not added["source_written"]
    locator = added["operation_result"]["changes"][0]["locator"]
    record = await read_complete(client, added["asset"], locator)
    changed = await native(
        client,
        op="update_pptx",
        asset_id=asset["asset_id"],
        expected_revision=added["asset"]["revision"],
        pptx_edits=[edit_run(record, "SDK2 新增後修改 µ").model_dump()],
    )
    current = await read_complete(client, changed["asset"], locator)
    assert "SDK2 新增後修改 µ" in current["xml"]
    stale = await native(
        client,
        op="delete_pptx_shapes",
        asset_id=asset["asset_id"],
        expected_revision=changed["asset"]["revision"],
        pptx_shape_refs=[record["evidence"]],
    )
    assert not stale["success"]
    deleted = await native(
        client,
        op="delete_pptx_shapes",
        asset_id=asset["asset_id"],
        expected_revision=changed["asset"]["revision"],
        pptx_shape_refs=[current["evidence"]],
    )
    assert deleted["success"] and not deleted["source_written"]
    remaining = await native(client, **deleted["review_request"])
    assert not any(s["locator"] == locator for s in remaining["shapes"])
    proof = await native(client, op="verify", reference=current["evidence"])
    assert proof["valid"] and not proof["is_current_managed_revision"]
    return deleted["asset"]


@pytest.mark.timeout(60)
async def test_native_shape_crud_sdk2(tmp_path):
    data = build_presentation()
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
        contract = await native(client, op="contract", for_op="add_pptx_shapes")
        assert "add_pptx_shapes" in contract["formats"]["pptx"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        current = await exercise_shapes(client, asset, data)
        assert source.read_bytes() == data
        target = tmp_path / "published.pptx"
        assert (
            await native(
                client,
                op="publish",
                asset_id=asset["asset_id"],
                expected_revision=current["revision"],
                output_path=str(target),
            )
        )["success"]
        assert hashlib.sha256(target.read_bytes()).hexdigest() == current["revision"]
        assert len(Presentation(target).slides) == 2
        assert (
            await native(
                client,
                op="writeback",
                asset_id=asset["asset_id"],
                expected_revision=current["revision"],
                expected_source_sha256=asset["source"]["sha256"],
            )
        )["source_written"]
        assert source.read_bytes() == target.read_bytes()
