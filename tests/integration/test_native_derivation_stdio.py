"""SDK2 scanned-page evidence to editable table with correction/retraction and wiki."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.codex_pdf.fixtures import build_pdf
from tests.integration.test_native_pdf_stdio import read_page, verify_image
from tests.integration.test_native_pptx_shape_stdio import native, read_complete
from tests.native_pptx_helpers import build_presentation
from tests.native_pptx_table_helpers import table_addition


async def ledger_read(client, asset_id):
    chunks, offset, digest = [], 0, None
    while True:
        pin = {"derivations_sha256": digest} if digest else {}
        result = await native(
            client,
            op="read_derivations",
            asset_id=asset_id,
            text_offset=offset,
            text_limit=400,
            **pin,
        )
        digest = digest or result["derivations_sha256"]
        assert result["derivations_sha256"] == digest
        chunks.append(result["text_excerpt"])
        if result["next_text_offset"] is None:
            break
        offset = result["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text), digest


async def build_endpoints(client, source, target, deck_bytes):
    pdf = (await native(client, op="register", source_path=str(source)))["asset"]
    overview = await native(client, op="read_pdf", asset_id=pdf["asset_id"])
    locator = overview["pages"][0]["locator"]
    await verify_image(client, pdf, locator)
    page = await read_page(client, pdf, locator)
    deck = (await native(client, op="register", source_path=str(target)))["asset"]
    inserted = await native(
        client,
        op="add_pptx_tables",
        asset_id=deck["asset_id"],
        expected_revision=deck["revision"],
        pptx_tables=[table_addition(deck_bytes).model_dump()],
    )
    deck = inserted["asset"]
    shape = await read_complete(
        client, deck, inserted["operation_result"]["changes"][0]["locator"]
    )
    return deck, {
        "target": shape["evidence"],
        "sources": [page["evidence"]],
        "agent": "SDK2 regression",
        "activity": "Candidate table fixture; not an OCR accuracy assertion",
        "review": {
            "semantic_accuracy": "not_checked",
            "rendered_layout": "not_checked",
        },
    }


async def record_and_correct(client, deck, claim):
    _, initial = await ledger_read(client, deck["asset_id"])
    first = await native(
        client,
        op="record_derivation",
        asset_id=deck["asset_id"],
        expected_derivations_sha256=initial,
        derivation=claim,
    )
    assert first["success"] and not first["native_file_written"]
    stale = await native(
        client,
        op="record_derivation",
        asset_id=deck["asset_id"],
        expected_derivations_sha256=initial,
        derivation={**claim, "activity": "Stale writer"},
    )
    assert not stale["success"]
    _, current = await ledger_read(client, deck["asset_id"])
    fixed = {
        **claim,
        "supersedes": first["derivation_id"],
        "review": {
            "semantic_accuracy": "failed",
            "notes": "Fixture does not assert visual transcription",
        },
    }
    second = await native(
        client,
        op="record_derivation",
        asset_id=deck["asset_id"],
        expected_derivations_sha256=current,
        derivation=fixed,
    )
    proof = await native(
        client,
        op="verify_derivation",
        asset_id=deck["asset_id"],
        derivation_id=first["derivation_id"],
    )
    assert not proof["active"] and proof["references_valid"]
    return second


async def exercise_ledger(client, deck, claim, tmp_path, source_bytes):
    second = await record_and_correct(client, deck, claim)
    result = await native(
        client,
        op="export_wiki",
        asset_id=deck["asset_id"],
        output_dir=str(tmp_path / "wiki"),
        derivations_sha256=second["derivations_sha256"],
    )
    root = Path(result["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text())
    assert manifest["derivations"]["active_ids_for_revision"] == [
        second["derivation_id"]
    ]
    attachment = next(iter(manifest["derivations"]["source_attachments"].values()))
    assert Path(attachment["attachment"]).suffix == ".pdf"
    assert (root / attachment["attachment"]).read_bytes() == source_bytes
    portable = (
        await native(
            client, op="register", source_path=str(root / attachment["attachment"])
        )
    )["asset"]
    assert (
        portable["format"] == "pdf"
        and portable["revision"] == claim["sources"][0]["revision"]
    )
    assert (
        await native(
            client,
            op="retract_derivation",
            asset_id=deck["asset_id"],
            expected_derivations_sha256=second["derivations_sha256"],
            retraction={
                "derivation_id": second["derivation_id"],
                "agent": "SDK2 regression",
                "reason": "Withdraw test interpretation",
            },
        )
    )["success"]
    history, _ = await ledger_read(client, deck["asset_id"])
    assert [e["kind"] for e in history["events"]] == ["record", "record", "retract"]
    old = json.loads((root / "derivations.json").read_text())
    assert len(old["events"]) == 2


@pytest.mark.timeout(120)
async def test_native_derivation_crud_over_sdk2(tmp_path):
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
        contract = await native(client, op="contract", for_op="record_derivation")
        assert contract["derivations_enabled"]
        deck, claim = await build_endpoints(client, source, target, deck_bytes)
        await exercise_ledger(client, deck, claim, tmp_path, original)
    assert source.read_bytes() == original
    assert target.read_bytes() == deck_bytes
