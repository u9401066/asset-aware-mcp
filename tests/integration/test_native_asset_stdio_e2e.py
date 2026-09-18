"""A workbook created without PDF/Markdown survives real MCP native operations."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.infrastructure.native_spreadsheet import NativeSpreadsheet


def _unwrap(result: Any) -> dict[str, Any]:
    assert not result.is_error, result.content
    payload = result.structured_content
    if isinstance(payload, dict) and set(payload) == {"result"}:
        payload = payload["result"]
    if payload is None:
        payload = json.loads("".join(item.text for item in result.content))
    assert isinstance(payload, dict), payload
    return payload


@pytest.mark.timeout(60)
async def test_native_workbook_creation_and_edit_over_sdk2_stdio(
    tmp_path: Path,
) -> None:
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
        tools = (await client.list_tools()).tools
        document = next(tool for tool in tools if tool.name == "document")
        assert "native_request" in document.input_schema["properties"]
        assert "ctx" not in document.input_schema["properties"]

        async def native(**request: Any) -> dict[str, Any]:
            return _unwrap(
                await client.call_tool(
                    "document", {"op": "native", "native_request": request}
                )
            )

        contract = await native(op="contract")
        assert contract["success"]
        assert "export_wiki" in contract["schema"]["properties"]["op"]["enum"]
        created = await native(
            op="create",
            workbook={
                "name": "budget.xlsx",
                "sheets": ["Budget"],
                "edits": [
                    {"sheet": "Budget", "cell": "A1", "value": "=literal"},
                    {"sheet": "Budget", "cell": "B1", "kind": "number", "value": 2},
                ],
            },
        )
        assert created["success"]
        asset = created["asset"]
        changed = await native(
            op="update",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            edits=[{"sheet": "Budget", "cell": "B1", "kind": "number", "value": 7}],
        )
        assert changed["success"]
        assert not changed["source_written"]
        current = changed["asset"]
        inspected = await native(op="inspect", asset_id=current["asset_id"])
        cells = inspected["content"]["cells"]
        assert cells[0]["kind"] == "string"
        assert cells[0]["value"] == "=literal"
        assert cells[1]["value"] == 7
        assert cells[1]["evidence"]["revision"] == current["revision"]
        excerpt = await native(
            op="read_cell",
            asset_id=current["asset_id"],
            sheet="Budget",
            cell="A1",
            text_limit=3,
        )
        assert excerpt["cell"]["value_excerpt"] == "=li"
        assert excerpt["cell"]["next_text_offset"] == 3
        assert excerpt["cell"]["evidence"] == cells[0]["evidence"]
        verified = await native(op="verify", reference=excerpt["cell"]["evidence"])
        assert verified["valid"] is True
        assert verified["is_current_managed_revision"] is True
        tampered = dict(excerpt["cell"]["evidence"], value_sha256="f" * 64)
        assert (await native(op="verify", reference=tampered))["valid"] is False
        exported = await native(
            op="export_wiki",
            asset_id=current["asset_id"],
            output_dir=str(tmp_path / "wiki"),
            citation_contract={"preset": "author-year"},
            citation_metadata={"authors": "Lin", "year": "2026"},
        )
        assert exported["success"], exported
        wiki = Path(exported["output_dir"])
        records = [
            json.loads(line)
            for line in (wiki / "records.jsonl").read_text().splitlines()
        ]
        assert records[0]["evidence"] == cells[0]["evidence"]
        assert "Lin, 2026" in records[0]["citation_presentation"]["inline"]
        assert (await native(op="verify", reference=records[1]["evidence"]))["valid"]
        (wiki / exported["index_note"]).write_text("Human edit", encoding="utf-8")
        conflict = await native(
            op="export_wiki",
            asset_id=current["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert conflict["success"] is False
        assert (wiki / exported["index_note"]).read_text() == "Human edit"
        rejected = await native(
            op="update",
            asset_id=current["asset_id"],
            expected_revision=asset["revision"],
            edits=[{"sheet": "Budget", "cell": "B1", "kind": "number", "value": 9}],
        )
        assert rejected["success"] is False
        target = tmp_path / "budget.xlsx"
        published = await native(
            op="publish",
            asset_id=current["asset_id"],
            expected_revision=current["revision"],
            output_path=str(target),
        )
        assert published["success"]
        assert hashlib.sha256(target.read_bytes()).hexdigest() == current["revision"]
        assert (
            NativeSpreadsheet(target.read_bytes()).inspect()["cells"][1]["value"] == 7
        )
        assert (
            len((await native(op="history", asset_id=current["asset_id"]))["history"])
            == 2
        )
        assert len((await native(op="list"))["assets"]) == 1
        assert (
            await native(
                op="archive",
                asset_id=current["asset_id"],
                expected_revision=current["revision"],
            )
        )["success"]
        assert target.exists()
