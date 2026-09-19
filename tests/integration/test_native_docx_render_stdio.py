"""Optional Writer/SDK2 preview: page identity, real pixels and historical sources."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
from functools import partial

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.integration.test_native_docx_stdio_e2e import _native, _read_complete_dfm
from tests.native_docx_render_helpers import paged_docx


@pytest.mark.skipif(
    os.environ.get("NATIVE_DOCX_RENDER_TEST") != "1",
    reason="Set NATIVE_DOCX_RENDER_TEST=1 with LibreOffice Writer installed",
)
@pytest.mark.timeout(150)
async def test_writer_pages_and_history_over_sdk2_stdio(tmp_path):
    source = tmp_path / "source.docx"
    original = paged_docx()
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
        native = partial(_native, client)
        asset = (await native(op="register", source_path=str(source)))["asset"]
        contract = await native(op="contract", for_op="render_docx_page")
        assert contract["docx_rendering"]["configured"]

        async def preview(revision, index, color):
            result = await client.call_tool(
                "document",
                {
                    "op": "native",
                    "native_request": {
                        "op": "render_docx_page",
                        "asset_id": asset["asset_id"],
                        "revision": revision,
                        "docx_page_index": index,
                        "render_size": 640,
                    },
                },
            )
            metadata = json.loads(
                "".join(item.text for item in result.content if item.type == "text")
            )
            metadata = metadata.get("result", metadata)
            assert metadata["success"], metadata
            images = [item for item in result.content if item.type == "image"]
            assert len(images) == 1
            png = base64.b64decode(images[0].data)
            assert hashlib.sha256(png).hexdigest() == metadata["image_sha256"]
            with Image.open(io.BytesIO(png)) as image:
                assert max(image.size) == 640
                pixels = image.convert("RGB")
                counts = pixels.getcolors(pixels.width * pixels.height)
                assert sum(n for n, value in counts if value == color) > 20
            assert metadata["inspected_revision"] == revision
            assert metadata["page_index"] == index and metadata["page_count"] == 2
            assert metadata["next_page_index"] == (1 if index == 0 else None)
            assert metadata["page_geometry"]["media_box"] == [0, 0, 612, 792]
            assert metadata["renderer"]["name"] == "LibreOffice Writer"
            return png

        first = await preview(asset["revision"], 0, (255, 0, 0))
        await preview(asset["revision"], 1, (0, 0, 255))
        dfm = await _read_complete_dfm(native, asset)
        changed = await native(
            op="update_docx",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_edit={"dfm_text": dfm.replace("WORD PAGE 1", "CHANGED WORD PAGE 1")},
        )
        assert changed["success"], changed
        current = changed["asset"]
        assert await preview(current["revision"], 0, (255, 0, 0)) != first
        assert await preview(asset["revision"], 0, (255, 0, 0)) == first
        invalid = await native(
            op="render_docx_page",
            asset_id=asset["asset_id"],
            revision=current["revision"],
            docx_page_index=2,
        )
        assert not invalid["success"] and "page count" in invalid["error"]
        assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
