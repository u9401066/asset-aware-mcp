"""SDK2 definition CRUD isolates the middle section while preserving its successors."""

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
from tests.native_docx_stories_helpers import HEADER_PART
from tests.native_docx_story_lifecycle_helpers import (
    NEW_HEADER,
    OBSOLETE,
    assert_native_stages,
    inspect_pages,
    source_document,
    structure_edits,
    text_edit,
)


async def complete(native, fields):
    key = "story_structure" if fields["op"] == "read_docx_story_structure" else "story"
    chunks, offset, digest = [], 0, None
    while True:
        result = await native(**fields, text_offset=offset, text_limit=4000)
        assert result["success"], result
        page = result[key]
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
async def test_story_definition_lifecycle_over_sdk2(tmp_path, render):
    if render and not os.environ.get("NATIVE_DOCX_FONT_FIXTURE"):
        pytest.skip("Set NATIVE_DOCX_FONT_FIXTURE with optional Writer")
    source = tmp_path / "source.docx"
    original = source_document()
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
        contract = await native(op="contract", for_op="update_docx_story_structure")
        assert contract["success"] and "response_truncated" not in contract, contract
        assert contract["docx_story_structure_enabled"]
        chunks, offset = [], 0
        while True:
            page = await native(
                **contract["contract_request"], text_offset=offset, text_limit=4000
            )
            assert page["success"] and "response_truncated" not in page, page
            chunks.append(page["text_excerpt"])
            assert page["contract_sha256"] == contract["contract_sha256"]
            offset = page["next_text_offset"]
            if offset is None:
                break
        text = "".join(chunks)
        assert hashlib.sha256(text.encode()).hexdigest() == contract["contract_sha256"]
        assert "bind part:null" in json.loads(text)["docx_story_structure_policy"]
        asset = (await native(op="register", source_path=str(source)))["asset"]
        initial = asset.copy()

        async def read(part):
            return await complete(
                native,
                {
                    "op": "read_docx_story",
                    "asset_id": asset["asset_id"],
                    "revision": asset["revision"],
                    "docx_story_part": part,
                },
            )

        before = await complete(
            native,
            {
                "op": "read_docx_story_structure",
                "asset_id": asset["asset_id"],
                "revision": asset["revision"],
            },
        )
        header, obsolete = await read(HEADER_PART), await read(OBSOLETE)
        old_ref = obsolete["evidence"]
        first_wiki = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert first_wiki["story_count"] == 4
        old_root = Path(first_wiki["output_dir"])
        old_files = {
            p.relative_to(old_root): p.read_bytes()
            for p in old_root.rglob("*")
            if p.is_file()
        }
        footer = next(
            x["locator"]["part"]
            for x in before["catalog"]["stories"]
            if x["locator"]["story_kind"] == "footer"
        )
        fields = {
            "op": "update_docx_story_structure",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "docx_story_structure": {
                "expected_catalog_sha256": before["catalog_sha256"],
                "scope": "sections_and_following_inheritors",
                "edits": structure_edits(header, obsolete, footer),
            },
        }
        changed = await native(**fields)
        assert changed["success"], changed
        structure = await complete(native, changed["review_request"])
        assert len(structure["operation_result"]["changes"]) == 7
        asset = changed["asset"]
        revisions = tmp_path / "data/native-assets" / asset["asset_id"] / "revisions"
        intermediate = (revisions / asset["revision"]).read_bytes()
        stale = await native(**fields)
        assert not stale["success"] and "stale" in stale["error"]
        new_header = await read(NEW_HEADER)
        changed = await native(
            op="update_docx_story",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_story_reference=new_header["evidence"],
            docx_story_update=text_edit(new_header),
        )
        assert changed["success"], changed
        await complete(native, changed["review_request"])
        asset = changed["asset"]
        for entry in structure["catalog"]["stories"]:
            await read(entry["locator"]["part"])
        assert (await native(op="verify", reference=old_ref))["valid"]
        historical = await complete(
            native,
            {
                "op": "read_docx_story",
                "asset_id": initial["asset_id"],
                "revision": initial["revision"],
                "docx_story_part": OBSOLETE,
            },
        )
        assert historical == obsolete
        selection = await native(
            op="read_selection", reference=old_ref, selection={"pointer": "/text"}
        )
        assert (await native(op="verify", reference=selection["evidence"]))["valid"]
        final = (revisions / asset["revision"]).read_bytes()
        assert_native_stages(original, intermediate, final)
        last_wiki = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert last_wiki["story_count"] == 5
        assert old_files == {
            p.relative_to(old_root): p.read_bytes()
            for p in old_root.rglob("*")
            if p.is_file()
        }
        destination = tmp_path / "verified.docx"
        assert (
            await native(
                op="publish",
                asset_id=asset["asset_id"],
                expected_revision=asset["revision"],
                output_path=str(destination),
            )
        )["success"]
        assert destination.read_bytes() == final
        assert (
            len((await native(op="history", asset_id=asset["asset_id"]))["history"])
            == 3
        )
        if render:
            with environment(snapshot(Path(os.environ["NATIVE_DOCX_FONT_FIXTURE"]))):
                seen = {}
                for revision, data, stage in [
                    (initial["revision"], original, 0),
                    (asset["revision"], final, 2),
                ]:
                    inspect_pages(data, stage)
                    for index in range(4):
                        response = await client.call_tool(
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
                                c.text for c in response.content if c.type == "text"
                            )
                        )
                        metadata = metadata.get("result", metadata)
                        assert metadata["success"], metadata
                        images = [c for c in response.content if c.type == "image"]
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
                        assert count == metadata["page_count"] == 4
                        seen[stage, index] = pixels
                assert all(seen[0, i] == seen[2, i] for i in [0, 1, 3])
                assert seen[0, 2] != seen[2, 2]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
