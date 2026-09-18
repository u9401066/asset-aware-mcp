"""Actual SDK2 PDF images, page CRUD, composition, evidence and writeback."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys

import pymupdf
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_asset_stdio_e2e import _unwrap
from tests.native_pdf_helpers import build_pdf


async def native(client, **request):
    result = await client.call_tool(
        "document", {"op": "native", "native_request": request}
    )
    payload = _unwrap(result)
    assert "response_truncated" not in payload
    return payload


async def read_page(client, asset, locator):
    chunks, offset, digest = [], 0, None
    while True:
        page = (
            await native(
                client,
                op="read_pdf_page",
                asset_id=asset["asset_id"],
                revision=asset["revision"],
                pdf_locator=locator,
                text_offset=offset,
                text_limit=4000,
            )
        )["page"]
        digest = digest or page["text_sha256"]
        assert page["text_sha256"] == digest
        chunks.append(page["text_excerpt"])
        if page["next_text_offset"] is None:
            break
        offset = page["next_text_offset"]
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


async def all_refs(client, asset):
    listing = await native(
        client, op="read_pdf", asset_id=asset["asset_id"], revision=asset["revision"]
    )
    return [
        (await read_page(client, asset, page["locator"]))["evidence"]
        for page in listing["pages"]
    ]


async def structural_edits(client, original):
    added = await native(
        client,
        op="add_pdf_pages",
        asset_id=original["asset_id"],
        expected_revision=original["revision"],
        pdf_insert={"position": 1, "pages": [{"blank": {"width": 300, "height": 400}}]},
    )
    assert added["success"] and not added["source_written"]
    current = added["asset"]
    refs = await all_refs(client, current)
    updated = await native(
        client,
        op="update_pdf",
        asset_id=current["asset_id"],
        expected_revision=current["revision"],
        pdf_edits=[{"reference": refs[0], "rotation": 90}],
    )
    current = updated["asset"]
    rejected = await native(
        client,
        op="delete_pdf_pages",
        asset_id=current["asset_id"],
        expected_revision=current["revision"],
        pdf_page_refs=[refs[1]],
    )
    assert not rejected["success"]
    blank = (await read_page(client, current, refs[1]["locator"]))["evidence"]
    deleted = await native(
        client,
        op="delete_pdf_pages",
        asset_id=current["asset_id"],
        expected_revision=current["revision"],
        pdf_page_refs=[blank],
    )
    assert deleted["success"]
    current = deleted["asset"]
    refs = await all_refs(client, current)
    reordered = await native(
        client,
        op="reorder_pdf_pages",
        asset_id=current["asset_id"],
        expected_revision=current["revision"],
        pdf_order=list(reversed(refs)),
    )
    assert reordered["success"]
    return reordered["asset"], refs[0]


async def verify_image(client, asset, locator):
    result = await client.call_tool(
        "document",
        {
            "op": "native",
            "native_request": {
                "op": "render_pdf_page",
                "asset_id": asset["asset_id"],
                "revision": asset["revision"],
                "pdf_locator": locator,
                "render_size": 512,
            },
        },
    )
    images = [block for block in result.content if block.type == "image"]
    assert len(images) == 1
    image = images[0]
    assert image.mime_type == "image/png"
    png = base64.b64decode(image.data, validate=True)
    metadata = json.loads(
        "".join(block.text for block in result.content if block.type == "text")
    )
    assert hashlib.sha256(png).hexdigest() == metadata["image_sha256"]
    assert png.startswith(b"\x89PNG")


async def publish_and_writeback(client, current, original, source, target):
    result = await native(
        client,
        op="publish",
        asset_id=current["asset_id"],
        expected_revision=current["revision"],
        output_path=str(target),
    )
    assert result["success"]
    with pymupdf.open(target) as pdf:
        assert pdf.page_count == 3
        assert pdf[2].rotation == 90
        assert next(pdf[2].widgets()).field_value == "preserved value"
        assert pdf.embfile_get("original.txt") == b"exact attachment\n"
    result = await native(
        client,
        op="writeback",
        asset_id=current["asset_id"],
        expected_revision=current["revision"],
        expected_source_sha256=original["source"]["sha256"],
    )
    assert result["source_written"] and source.read_bytes() == target.read_bytes()


@pytest.mark.timeout(120)
async def test_native_pdf_actual_sdk2(tmp_path):
    source = tmp_path / "source.pdf"
    data = build_pdf(links=True, forms=True, labels=True)
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
        contract = await native(client, op="contract", for_op="create_pdf")
        assert "render_pdf_page" in contract["formats"]["pdf"]
        original = (await native(client, op="register", source_path=str(source)))[
            "asset"
        ]
        listing = await native(client, op="read_pdf", asset_id=original["asset_id"])
        await verify_image(client, original, listing["pages"][0]["locator"])
        current, reference = await structural_edits(client, original)
        assert source.read_bytes() == data
        proof = await native(client, op="verify", reference=reference)
        assert proof["valid"] and not proof["is_current_managed_revision"]
        refs = await all_refs(client, current)
        created = await native(
            client,
            op="create_pdf",
            pdf_create={"name": "copy.pdf", "pages": [{"reference": r} for r in refs]},
        )
        assert created["success"] and created["asset"]["source"] is None
        wiki = await native(
            client,
            op="export_wiki",
            asset_id=current["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert wiki["success"] and wiki["page_count"] == 3
        await publish_and_writeback(
            client, current, original, source, tmp_path / "published.pdf"
        )
