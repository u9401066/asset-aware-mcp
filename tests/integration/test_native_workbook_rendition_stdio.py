"""Optional real Calc/SDK2: frozen pages, formulas, pixels and portable provenance."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
from pathlib import Path

import openpyxl
import pymupdf
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.integration.test_native_pptx_shape_stdio import native
from tests.native_workbook_render_helpers import rendered_workbook


async def read_receipt(client, asset):
    chunks, offset, digest = [], 0, None
    while True:
        result = await native(
            client,
            op="read_rendition",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            text_offset=offset,
            text_limit=700,
        )
        assert result["success"], result
        digest = digest or result["text_sha256"]
        assert digest == result["text_sha256"]
        assert result["excerpt_char_range"][0] == offset
        chunks.append(result["text_excerpt"])
        offset = result["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


async def render_page(client, asset, locator):
    result = await client.call_tool(
        "document",
        {
            "op": "native",
            "native_request": {
                "op": "render_pdf_page",
                "asset_id": asset["asset_id"],
                "revision": asset["revision"],
                "pdf_locator": locator,
                "render_size": 640,
            },
        },
    )
    assert not result.is_error
    meta = json.loads(
        "".join(item.text for item in result.content if item.type == "text")
    )
    meta = meta.get("result", meta)
    assert meta["success"], meta
    images = [item for item in result.content if item.type == "image"]
    assert len(images) == 1
    png = base64.b64decode(images[0].data)
    assert hashlib.sha256(png).hexdigest() == meta["image_sha256"]
    return png


@pytest.mark.skipif(
    os.environ.get("NATIVE_WORKBOOK_RENDER_TEST") != "1",
    reason="Set NATIVE_WORKBOOK_RENDER_TEST=1 with LibreOffice Calc installed",
)
@pytest.mark.timeout(180)
async def test_real_workbook_renditions_over_sdk2(tmp_path):
    source = tmp_path / "source.xlsx"
    original = rendered_workbook()
    source.write_bytes(original)
    mtime = source.stat().st_mtime_ns
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
        },
    )
    async with Client(stdio_client(params)) as client:
        contract = await native(
            client, op="contract", for_op="create_workbook_rendition"
        )
        assert contract["workbook_rendering"]["configured"]
        assert "create_workbook_rendition" in contract["formats"]["xlsx"]
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        changed = await native(
            client,
            op="update",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            edits=[{"sheet": "First", "cell": "A1", "value": "NEW WORKBOOK CONTENT"}],
        )
        assert changed["success"]
        saved = []
        for mode in ("print", "whole_sheet"):
            for calculation in ("prefer_cache", "recalculate"):
                created = await native(
                    client,
                    op="create_workbook_rendition",
                    asset_id=asset["asset_id"],
                    revision=asset["revision"],
                    workbook_rendition={"mode": mode, "calculation": calculation},
                )
                assert created["success"], created
                pdf_asset = created["asset"]
                receipt = await read_receipt(client, pdf_asset)
                record = receipt["changes"][0]
                assert record["source_reference"] == asset["file_reference"]
                rendering = record["rendering"]
                assert rendering["renderer"]["name"] == "LibreOffice Calc"
                assert rendering["mode"] == mode
                assert rendering["calculation_requested"] == calculation
                assert rendering["source_copy_unchanged"]
                path = tmp_path / f"{mode}-{calculation}.pdf"
                result = await native(
                    client,
                    op="publish",
                    asset_id=pdf_asset["asset_id"],
                    expected_revision=pdf_asset["revision"],
                    output_path=str(path),
                )
                assert result["success"]
                pdf_bytes = path.read_bytes()
                assert hashlib.sha256(pdf_bytes).hexdigest() == pdf_asset["revision"]
                with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
                    text = [page.get_text() for page in pdf]
                    assert len(pdf) == (2 if mode == "print" else 4)
                    assert ("999" if calculation == "prefer_cache" else "3") in text[
                        0
                    ].splitlines()
                    assert "FIRST PRINT" in text[0] and "NEW WORKBOOK" not in text[0]
                    if mode == "whole_sheet":
                        assert "OUTSIDE PRINT RANGE" in text[0]
                        assert not text[1] and "HIDDEN" in text[2]
                        assert [
                            item["page_index"]
                            for item in rendering["sheet_page_mapping"]
                        ] == [0, 1, 2, 3]
                        assert list(pdf[1].rect) == [0, 0, 1, 1]
                    else:
                        assert "OUTSIDE PRINT RANGE" not in "".join(text)
                        assert "HIDDEN" not in "".join(text)
                        assert rendering["sheet_page_mapping"] is None
                pages = (await native(client, **created["pages_request"]))["pages"]
                assert [item["locator"] for item in pages] == [
                    item["locator"] for item in rendering["pages"]
                ]
                pngs = [
                    await render_page(client, pdf_asset, item["locator"])
                    for item in pages
                ]
                for png, color in ((pngs[0], (255, 0, 0)), (pngs[-1], (0, 0, 255))):
                    with Image.open(io.BytesIO(png)) as image:
                        assert max(image.size) == 640
                        counts = image.convert("RGB").getcolors(
                            image.width * image.height
                        )
                        assert sum(n for n, value in counts if value == color) > 20
                assert (
                    await render_page(client, pdf_asset, pages[0]["locator"]) == pngs[0]
                )
                verified = await native(
                    client, op="verify", reference=pdf_asset["file_reference"]
                )
                assert verified["success"]
                saved.append((pdf_asset, receipt))
        wiki = await native(
            client,
            op="export_wiki",
            asset_id=saved[-1][0]["asset_id"],
            revision=saved[-1][0]["revision"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert wiki["success"], wiki
        folder = Path(wiki["output_dir"])
        manifest = json.loads((folder / "manifest.json").read_text())
        assert json.loads((folder / "rendition.json").read_text()) == saved[-1][1]
        assert (
            folder / manifest["rendition"]["source_attachment"]
        ).read_bytes() == original
        assert (await native(client, op="history", asset_id=asset["asset_id"]))[
            "asset"
        ]["revision_count"] == 2
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
    book = openpyxl.load_workbook(io.BytesIO(original), data_only=True)
    try:
        assert book["First"]["B2"].value == 999
    finally:
        book.close()
