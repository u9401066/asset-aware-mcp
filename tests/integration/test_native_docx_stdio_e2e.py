"""Real SDK 2 DOCX read/edit/writeback without leaking private DFM sessions."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from functools import partial
from pathlib import Path
from typing import Any

import pytest
from docx import Document
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.native_docx_helpers import build_docx


async def _native(client: Client, **request: Any) -> dict[str, Any]:
    result = await client.call_tool(
        "document", {"op": "native", "native_request": request}
    )
    assert not result.is_error, result.content
    payload = result.structured_content
    if isinstance(payload, dict) and set(payload) == {"result"}:
        payload = payload["result"]
    if payload is None:
        payload = json.loads("".join(item.text for item in result.content))
    assert isinstance(payload, dict), payload
    return payload


@pytest.mark.timeout(90)
async def test_native_docx_edit_and_writeback_over_sdk2_stdio(tmp_path: Path) -> None:
    source = tmp_path / "研究.docx"
    source.write_bytes(build_docx())
    original = source.read_bytes()
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
        native = partial(_native, client)

        registered = await native(op="register", source_path=str(source))
        assert registered["success"], registered
        asset = registered["asset"]
        inspection = await native(op="inspect", asset_id=asset["asset_id"])
        assert inspection["content"]["native_editor"] == "dfm_bridge"
        reference = await _verify_wiki_blocks(native, asset, tmp_path)
        text = await _read_complete_dfm(native, asset)
        changed = await native(
            op="update_docx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_edit={"dfm_text": text.replace("原始段落", "經核對段落")},
        )
        assert changed["success"], changed
        assert changed["source_written"] is False and source.read_bytes() == original
        current = changed["asset"]
        assert current["revision"] != asset["revision"]
        stale = await native(
            op="update_docx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_edit={"dfm_text": text},
        )
        assert stale["success"] is False and "stale" in stale["error"]
        await _writeback_and_check(native, source, asset, current, original)
        assert await _read_complete_dfm(native, asset) == text
        old = await native(op="verify", reference=reference)
        assert old["valid"] and not old["is_current_managed_revision"]
        assert not list((tmp_path / "data").glob("docx_*"))


async def _verify_wiki_blocks(native: Any, asset: dict, tmp_path: Path) -> dict:
    result = await native(op="read_docx", asset_id=asset["asset_id"], limit=2)
    reference = result["blocks"][0]["evidence"]
    block = await native(
        op="read_docx_block",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        block_id=reference["locator"]["block_id"],
        text_limit=5,
    )
    assert block["success"] and block["block"]["evidence"] == reference
    assert len(block["block"]["text_excerpt"]) <= 5
    exported = await native(
        op="export_wiki", asset_id=asset["asset_id"], output_dir=str(tmp_path / "wiki")
    )
    assert exported["success"] and exported["block_count"] > 0
    root = Path(exported["output_dir"])
    records = [
        json.loads(line)
        for line in (root / "records.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert reference in [r["evidence"] for r in records]
    for record in records:
        assert (await native(op="verify", reference=record["evidence"]))["valid"]
    return reference


async def _read_complete_dfm(native: Any, asset: dict[str, Any]) -> str:
    pieces = []
    offset = 0
    expected_hash = None
    while True:
        result = await native(
            op="read_docx",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            text_offset=offset,
            text_limit=1400,
            limit=2,
        )
        assert result["success"], result
        dfm = result["dfm"]
        expected_hash = expected_hash or dfm["text_sha256"]
        assert dfm["text_sha256"] == expected_hash
        pieces.append(dfm["text_excerpt"])
        offset = dfm["next_text_offset"]
        if offset is None:
            text = "".join(pieces)
            assert hashlib.sha256(text.encode()).hexdigest() == expected_hash
            return text


async def _writeback_and_check(
    native: Any,
    source: Path,
    asset: dict[str, Any],
    current: dict[str, Any],
    original: bytes,
) -> None:
    result = await native(
        op="writeback",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
        expected_source_sha256=asset["source"]["sha256"],
    )
    assert result["success"], result
    assert result["source_written"] is True
    assert Path(result["backup_path"]).read_bytes() == original
    assert Document(source).paragraphs[1].text == "經核對段落 with italic context"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == current["revision"]
    old_source = await native(
        op="writeback",
        asset_id=asset["asset_id"],
        expected_revision=current["revision"],
        expected_source_sha256=asset["source"]["sha256"],
    )
    assert old_source["success"] is False
