"""Real SDK2 merge/split, source backup, immutable evidence and wiki preservation."""

import hashlib
import json
import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_picture_stdio import publish_and_writeback
from tests.integration.test_native_pptx_shape_stdio import native, read_complete
from tests.native_pptx_grid_helpers import grid_fixture, texts
from tests.unit.test_native_pptx_merges import merge


@pytest.mark.timeout(120)
async def test_merge_split_evidence_and_writeback_sdk2(tmp_path):
    data, ref, _ = grid_fixture(merge=None)
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
        assert "response_truncated" not in contract, contract
        if contract["contract_delivery"] == "paged":
            chunks, offset = [], 0
            while True:
                page = await native(
                    client, **contract["contract_request"], text_offset=offset
                )
                assert page["success"] and "response_truncated" not in page, page
                assert page["excerpt_char_range"][0] == offset
                assert page["text_sha256"] == contract["contract_sha256"]
                chunks.append(page["text_excerpt"])
                offset = page["next_text_offset"]
                if offset is None:
                    break
            text = "".join(chunks)
            assert (
                hashlib.sha256(text.encode()).hexdigest() == contract["contract_sha256"]
            )
            contract = json.loads(text)
        assert "content_policy" in contract["pptx_grid_policy"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        old = await read_complete(client, asset, ref["locator"])
        args = {
            "op": "update_pptx_table_grid",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "pptx_table_grid": {
                "reference": old["evidence"],
                "edits": [merge(content_policy="require_empty")],
            },
        }
        refused = await native(client, **args)
        assert not refused["success"]
        args["pptx_table_grid"]["edits"] = [merge()]
        result = await native(client, **args)
        assert (
            result["success"]
            and result["operation_result"]["changes"][0]["migrated_paragraphs"] == 3
        )
        merged = result["asset"]
        record = await read_complete(client, merged, ref["locator"])
        paras = record["table"]["rows"][1]["cells"][0]["paragraphs"]
        assert [p["items"][0]["text"] for p in paras] == ["A101", "007", "A102", "12"]
        assert not (
            await native(client, **{**args, "expected_revision": merged["revision"]})
        )["success"]
        split = await native(
            client,
            op="update_pptx_table_grid",
            asset_id=asset["asset_id"],
            expected_revision=merged["revision"],
            pptx_table_grid={
                "reference": record["evidence"],
                "edits": [{"op": "split", "row": 1, "column": 0}],
            },
        )
        assert split["success"]
        current = split["asset"]
        final = await read_complete(client, current, ref["locator"])
        assert not final["table"]["rows"][1]["cells"][0]["attributes"]
        assert len(final["table"]["rows"][1]["cells"][0]["paragraphs"]) == 4
        for previous in (old, record):
            proof = await native(client, op="verify", reference=previous["evidence"])
            assert proof["valid"] and not proof["is_current_managed_revision"]
        assert source.read_bytes() == data
        target = tmp_path / "published.pptx"
        await publish_and_writeback(client, current, asset, source, target)
    assert texts(target.read_bytes())[1:] == [
        ["A101\n007\nA102\n12", "", "-0.50\nmg/L"],
        ["", "", "=SUM(A1:A2)"],
    ]
