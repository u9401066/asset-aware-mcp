"""Real SDK2 story references, shared edits and independent three-page previews."""

import base64
import hashlib
import io
import json
import os
import sys
from functools import partial
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.codex_docx_structure.fonts import environment, snapshot
from tests.codex_docx_structure.renders import replay
from tests.integration.test_native_docx_stdio_e2e import _native
from tests.native_docx_stories_helpers import (
    HEADER_PART,
    HEADER_TEXT,
    correction,
    inspect_story_pages,
    story_document,
)


async def complete(native, fields):
    chunks, offset, digest = [], 0, None
    while True:
        result = await native(**fields, text_offset=offset, text_limit=3000)
        assert result["success"], result
        page = result["story"]
        assert page["excerpt_char_range"][0] == offset
        assert digest is None or digest == page["text_sha256"]
        digest = page["text_sha256"]
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


@pytest.mark.parametrize("render", [False, True])
@pytest.mark.timeout(180)
async def test_shared_word_stories_over_sdk2(tmp_path, render):
    if render and not os.environ.get("NATIVE_DOCX_FONT_FIXTURE"):
        pytest.skip("Set NATIVE_DOCX_FONT_FIXTURE with optional Writer")
    source = tmp_path / "source.docx"
    original = story_document()
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
    if render:
        params.env["FONTCONFIG_FILE"] = str(
            Path(os.environ["NATIVE_DOCX_FONT_FIXTURE"]) / "with-cjk.conf"
        )
    async with Client(stdio_client(params)) as client:
        native = partial(_native, client)
        contract = await native(op="contract", for_op="update_docx_story")
        assert contract["docx_stories_enabled"]
        asset = (await native(op="register", source_path=str(source)))["asset"]
        initial = asset.copy()
        catalog = await complete(
            native,
            {
                "op": "read_docx_stories",
                "asset_id": asset["asset_id"],
                "revision": asset["revision"],
            },
        )
        assert {s["locator"]["part"] for s in catalog["stories"]} == {
            HEADER_PART,
            "word/header1.xml",
            "word/footer1.xml",
        }
        before = await complete(
            native,
            {
                "op": "read_docx_story",
                "asset_id": asset["asset_id"],
                "revision": asset["revision"],
                "docx_story_part": HEADER_PART,
            },
        )
        assert HEADER_TEXT in before["text"]
        old_ref = before["evidence"]
        first_wiki = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert first_wiki["story_count"] == 3
        for part in [HEADER_PART, "word/footer1.xml"]:
            record = await complete(
                native,
                {
                    "op": "read_docx_story",
                    "asset_id": asset["asset_id"],
                    "revision": asset["revision"],
                    "docx_story_part": part,
                },
            )
            fields = {
                "op": "update_docx_story",
                "asset_id": asset["asset_id"],
                "expected_revision": asset["revision"],
                "docx_story_reference": record["evidence"],
                "docx_story_update": correction(record),
            }
            result = await native(**fields)
            assert result["success"], result
            after = await complete(native, result["review_request"])
            assert after["operation_result"]["changed_parts"] == [part]
            assert after["bindings"] == record["bindings"]
            asset = result["asset"]
            stale = await native(**fields)
            assert not stale["success"] and "stale" in stale["error"]
        assert (await native(op="verify", reference=old_ref))["valid"]
        assert (
            await complete(
                native,
                {
                    "op": "read_docx_story",
                    "asset_id": initial["asset_id"],
                    "revision": initial["revision"],
                    "docx_story_part": HEADER_PART,
                },
            )
            == before
        )
        selection = await native(
            op="read_selection", reference=old_ref, selection={"pointer": "/text"}
        )
        assert (await native(op="verify", reference=selection["evidence"]))["valid"]
        destination = tmp_path / "verified.docx"
        assert (
            await native(
                op="publish",
                asset_id=asset["asset_id"],
                expected_revision=asset["revision"],
                output_path=str(destination),
            )
        )["success"]
        final_wiki = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert (
            final_wiki["story_count"] == 3
            and final_wiki["output_dir"] != first_wiki["output_dir"]
        )
        assert (
            len((await native(op="history", asset_id=asset["asset_id"]))["history"])
            == 3
        )
        if render:
            with environment(snapshot(Path(os.environ["NATIVE_DOCX_FONT_FIXTURE"]))):
                for revision, data, stage in [
                    (initial["revision"], original, 0),
                    (asset["revision"], destination.read_bytes(), 2),
                ]:
                    _, texts = inspect_story_pages(data, stage)
                    for index in range(len(texts)):
                        wire = await client.call_tool(
                            "document",
                            {
                                "op": "native",
                                "native_request": {
                                    "op": "render_docx_page",
                                    "asset_id": asset["asset_id"],
                                    "revision": revision,
                                    "docx_page_index": index,
                                    "render_size": 900,
                                },
                            },
                        )
                        metadata = json.loads(
                            "".join(
                                item.text
                                for item in wire.content
                                if item.type == "text"
                            )
                        )
                        metadata = metadata.get("result", metadata)
                        assert metadata["success"], metadata
                        images = [i for i in wire.content if i.type == "image"]
                        assert len(images) == 1
                        png = base64.b64decode(images[0].data, validate=True)
                        assert (
                            hashlib.sha256(png).hexdigest() == metadata["image_sha256"]
                        )
                        count, width, height, pixels = replay(data, index, 900)
                        with Image.open(io.BytesIO(png)) as image:
                            assert (
                                image.size == (width, height)
                                and image.convert("RGB").tobytes() == pixels
                            )
                        assert count == metadata["page_count"] == 3
                        assert metadata["next_page_index"] == (
                            index + 1 if index < 2 else None
                        )
        assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
