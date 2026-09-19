"""Optional real Impress and SDK2 images: hidden slides, order and old revisions."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.integration.test_native_pptx_shape_stdio import native
from tests.native_pptx_render_helpers import colored_deck


@pytest.mark.skipif(
    os.environ.get("NATIVE_PPTX_RENDER_TEST") != "1",
    reason="Set NATIVE_PPTX_RENDER_TEST=1 with LibreOffice Impress installed",
)
@pytest.mark.asyncio
async def test_impress_images_follow_revision_hidden_and_reordered_slides(tmp_path):
    source = tmp_path / "source.pptx"
    original = colored_deck()
    source.write_bytes(original)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.presentation.server"],
        env={
            **os.environ,
            "DATA_DIR": str(tmp_path / "data"),
            "ENABLE_LIGHTRAG": "false",
        },
    )
    async with Client(stdio_client(params)) as client:
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        listing = await native(client, op="read_pptx", asset_id=asset["asset_id"])
        keys = [
            {k: slide[k] for k in ("slide_id", "part")} for slide in listing["slides"]
        ]

        async def preview(revision, key, index, color, hidden=False):
            response = await client.call_tool(
                "document",
                {
                    "op": "native",
                    "native_request": {
                        "op": "render_pptx_slide",
                        "asset_id": asset["asset_id"],
                        "revision": revision,
                        "pptx_slide_key": key,
                        "render_size": 640,
                    },
                },
            )
            metadata = json.loads(
                "".join(item.text for item in response.content if item.type == "text")
            )
            metadata = metadata.get("result", metadata)
            assert metadata["success"], metadata
            images = [item for item in response.content if item.type == "image"]
            assert len(images) == 1
            png = base64.b64decode(images[0].data)
            assert hashlib.sha256(png).hexdigest() == metadata["image_sha256"]
            with Image.open(io.BytesIO(png)) as image:
                assert max(image.size) == 640 and image.getpixel((4, 4)) == color
            assert metadata["slide_index"] == index and metadata["hidden"] == hidden
            assert metadata["inspected_revision"] == revision
            assert metadata["pptx_slide_key"] == key
            assert metadata["renderer"]["name"] == "LibreOffice Impress"
            return png

        hidden = await preview(asset["revision"], keys[1], 1, (0, 255, 0), True)
        changed = (
            await native(
                client,
                op="reorder_pptx_slides",
                asset_id=asset["asset_id"],
                expected_revision=asset["revision"],
                pptx_slide_order=list(reversed(keys)),
            )
        )["asset"]
        await preview(changed["revision"], keys[2], 0, (0, 0, 255))
        assert await preview(asset["revision"], keys[1], 1, (0, 255, 0), True) == hidden
        assert source.read_bytes() == original
