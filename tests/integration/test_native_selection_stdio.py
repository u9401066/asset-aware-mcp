"""SDK2 scan-page to exact native table text evidence, preserving source/history."""

import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.codex_pdf.fixtures import build_pdf
from tests.integration.test_native_derivation_stdio import build_endpoints, ledger_read
from tests.integration.test_native_pptx_shape_stdio import native
from tests.native_pptx_helpers import build_presentation


async def selected(client, reference, selection=None):
    chunks, offset, sha = [], 0, None
    while True:
        extra = {"selection": selection} if selection is not None else {}
        result = await native(
            client,
            op="read_selection",
            reference=reference,
            text_offset=offset,
            text_limit=350,
            **extra,
        )
        assert result["success"]
        sha = sha or result["text_sha256"]
        assert sha == result["text_sha256"]
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode("utf-8")).hexdigest() == sha
    return json.loads(text)


@pytest.mark.timeout(120)
async def test_scan_to_selected_pptx_cell_over_sdk2(tmp_path):
    source, target = tmp_path / "scan.pdf", tmp_path / "target.pptx"
    build_pdf(source, "scanned")
    original = source.read_bytes()
    deck_bytes = build_presentation()
    target.write_bytes(deck_bytes)
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
        deck, claim = await build_endpoints(client, source, target, deck_bytes)
        record = await selected(
            client,
            claim["target"],
            {
                "pointer": "/table/rows/1/cells/1/paragraphs/0/items/0/text",
                "char_range": {"start": 0, "end": 3},
            },
        )
        assert record["value"] == "007"
        assert record["text_context"]["utf8_byte_range"] == [0, 3]
        ref = record["evidence"]
        assert (await native(client, op="verify", reference=ref))["valid"]
        bad = deepcopy(ref)
        bad["selector"]["char_range"]["end"] = 2
        assert not (await native(client, op="verify", reference=bad))["valid"]
        _, sha = await ledger_read(client, deck["asset_id"])
        claim["target"] = ref
        result = await native(
            client,
            op="record_derivation",
            asset_id=deck["asset_id"],
            expected_derivations_sha256=sha,
            derivation=claim,
        )
        assert result["success"]
        wiki = await native(
            client,
            op="export_wiki",
            asset_id=deck["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        root = Path(wiki["output_dir"])
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        info = next(iter(manifest["derivations"]["selection_records"].values()))
        assert (
            json.loads((root / info["record_file"]).read_text(encoding="utf-8"))
            == record
        )
        changed = await native(
            client,
            op="update_pptx",
            asset_id=deck["asset_id"],
            expected_revision=deck["revision"],
            pptx_edits=[
                {
                    "locator": {
                        **ref["parent"]["locator"],
                        "row": 1,
                        "column": 1,
                        "paragraph": 0,
                        "run": 0,
                    },
                    "expected_text_sha256": hashlib.sha256(b"007").hexdigest(),
                    "text": "008",
                }
            ],
        )
        assert changed["success"]
        assert (await selected(client, ref))["value"] == "007"
        proof = await native(client, op="verify", reference=ref)
        assert proof["valid"] and not proof["is_current_managed_revision"]
    assert source.read_bytes() == original and target.read_bytes() == deck_bytes
