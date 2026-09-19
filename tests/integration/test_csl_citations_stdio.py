"""SDK2 transports complete CSL documents, native sources and immutable Wiki output."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pdf_regions_stdio import native, unwrap
from tests.unit.test_csl_processor import document


async def complete_csl(client, **request):
    parts, offset, sha, publication = [], 0, None, None
    while True:
        response = unwrap(
            await client.call_tool(
                "evidence",
                {
                    **request,
                    "text_offset": offset,
                    "text_limit": 1800,
                    "expected_text_sha256": sha,
                },
            )
        )
        assert response["success"] and "response_truncated" not in response, response
        sha = sha or response["text_sha256"]
        assert (
            response["text_sha256"] == sha
            and response["excerpt_char_range"][0] == offset
        )
        parts.append(response["text_excerpt"])
        publication = response.get("publication")
        if response["next_text_offset"] is None:
            break
        offset = response["next_text_offset"]
    text = "".join(parts)
    assert hashlib.sha256(text.encode()).hexdigest() == sha
    return json.loads(text), sha, publication


@pytest.mark.timeout(120)
async def test_csl_full_context_and_portable_native_evidence_over_sdk2(tmp_path):
    if not shutil.which("node"):
        pytest.skip("CSL integration requires optional Node.js >=20")
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
        tool = next(
            t for t in (await client.list_tools()).tools if t.name == "evidence"
        )
        assert tool.input_schema["properties"]["text_limit"]["maximum"] == 8000
        assert tool.input_schema["properties"]["text_offset"]["minimum"] == 0
        contract, _, _ = await complete_csl(client, op="csl_contract")
        assert (
            contract["configured"]
            and contract["document_schema"]["additionalProperties"] is False
        )
        created = await native(
            client,
            op="create",
            workbook={
                "name": "Source.xlsx",
                "sheets": ["Data"],
                "edits": [{"sheet": "Data", "cell": "A1", "value": "007"}],
            },
        )
        assert created["success"], created
        asset = created["asset"]
        record = await native(
            client,
            op="read_cell",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            sheet="Data",
            cell="A1",
        )
        reference = record["cell"]["evidence"]
        raw = document().model_dump(mode="json")
        raw["sources"] = {"measurement": reference}
        raw["clusters"][0]["cites"][0]["source_keys"] = ["measurement"]
        result, sha, _ = await complete_csl(
            client, op="render_citations", citation_document=raw
        )
        assert [c["text"] for c in result["citations"]] == [
            "(Doe, 2020b)",
            "(Doe, 2020a)",
            "(Doe, 2020b)",
        ]
        assert result["sources"]["measurement"]["reference"] == reference
        exported, export_sha, publication = await complete_csl(
            client,
            op="render_citations",
            citation_document=raw,
            wiki_root=str(tmp_path / "wiki"),
        )
        assert exported == result and sha == export_sha and publication["success"]
        root = Path(publication["output_dir"])
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        for name, entry in manifest["files"].items():
            assert (
                hashlib.sha256((root / name).read_bytes()).hexdigest()
                == entry["sha256"]
            )
        source = root / exported["sources"]["measurement"]["attachment"]["name"]
        assert hashlib.sha256(source.read_bytes()).hexdigest() == asset["revision"]
        changed = await native(
            client,
            op="update",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            edits=[{"sheet": "Data", "cell": "A1", "value": "Changed"}],
        )
        assert changed["success"], changed
        historical, historical_sha, reused = await complete_csl(
            client,
            op="render_citations",
            citation_document=raw,
            wiki_root=str(tmp_path / "wiki"),
        )
        assert historical == result and historical_sha == sha and reused["reused"]
        verified = await native(client, op="verify", reference=reference)
        assert verified["valid"] and not verified["is_current_managed_revision"]
        stale_root = tmp_path / "must-not-exist"
        denied = unwrap(
            await client.call_tool(
                "evidence",
                {
                    "op": "render_citations",
                    "citation_document": raw,
                    "wiki_root": str(stale_root),
                    "expected_text_sha256": "0" * 64,
                },
            )
        )
        assert not denied["success"] and not stale_root.exists()
