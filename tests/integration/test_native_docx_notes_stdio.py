"""SDK2 note CRUD keeps full evidence and renders automatic numbering separately."""

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
from tests.native_docx_note_lifecycle_helpers import (
    assert_native_stages,
    edits,
    inspect_pages,
    text_edit,
)
from tests.native_docx_notes_helpers import locator, source_document


async def complete(native, fields):
    chunks, offset, digest = [], 0, None
    while True:
        value = await native(**fields, text_offset=offset, text_limit=4000)
        assert value["success"] and "response_truncated" not in value, value
        page = value if fields["op"] == "contract_details" else value["note"]
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
async def test_note_lifecycle_over_sdk2(tmp_path, render):
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
        contract = await native(op="contract", for_op="update_docx_notes")
        assert contract["success"] and contract["docx_notes_enabled"]
        details = await complete(native, contract["contract_request"])
        assert "literal_body_text:preserve" in details["docx_notes_policy"]
        asset = (await native(op="register", source_path=str(source)))["asset"]
        initial = asset.copy()

        async def read(loc):
            return await complete(
                native,
                {
                    "op": "read_docx_note",
                    "asset_id": asset["asset_id"],
                    "revision": asset["revision"],
                    "docx_note_locator": loc,
                },
            )

        listing = await complete(
            native,
            {
                "op": "read_docx_notes",
                "asset_id": asset["asset_id"],
                "revision": asset["revision"],
            },
        )
        for entry in listing["catalog"]["notes"]:
            await read(entry["locator"])
        old = await read(locator(identity=8))
        first = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert first["note_count"] == 7
        old_root = Path(first["output_dir"])
        old_files = {
            p.relative_to(old_root): p.read_bytes()
            for p in old_root.rglob("*")
            if p.is_file()
        }
        fields = {
            "op": "update_docx_notes",
            "asset_id": asset["asset_id"],
            "expected_revision": asset["revision"],
            "docx_notes_update": {
                "scope": "definitions_and_native_body_references",
                "expected_catalog_sha256": listing["catalog_sha256"],
                "edits": edits(listing["catalog"], old),
            },
        }
        changed = await native(**fields)
        assert changed["success"], changed
        middle = await complete(native, changed["review_request"])
        assert len(middle["operation_result"]["changes"]) == 3
        asset = changed["asset"]
        revisions = tmp_path / "data/native-assets" / asset["asset_id"] / "revisions"
        intermediate = (revisions / asset["revision"]).read_bytes()
        assert not (await native(**fields))["success"]
        note = await read(locator())
        changed = await native(
            op="update_docx_note",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_note_reference=note["evidence"],
            docx_note_update=text_edit(note),
        )
        assert changed["success"], changed
        await complete(native, changed["review_request"])
        asset = changed["asset"]
        listing = await complete(
            native,
            {
                "op": "read_docx_notes",
                "asset_id": asset["asset_id"],
                "revision": asset["revision"],
            },
        )
        for entry in listing["catalog"]["notes"]:
            await read(entry["locator"])
        assert (await native(op="verify", reference=old["evidence"]))["valid"]
        historical = await complete(
            native,
            {
                "op": "read_docx_note",
                "asset_id": initial["asset_id"],
                "revision": initial["revision"],
                "docx_note_locator": locator(identity=8),
            },
        )
        assert historical == old
        selection = await native(
            op="read_selection",
            reference=old["evidence"],
            selection={"pointer": "/text"},
        )
        assert (await native(op="verify", reference=selection["evidence"]))["valid"]
        final = (revisions / asset["revision"]).read_bytes()
        assert_native_stages(original, intermediate, final)
        second = await native(
            op="export_wiki",
            asset_id=asset["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        assert second["note_count"] == 8
        assert old_files == {
            p.relative_to(old_root): p.read_bytes()
            for p in old_root.rglob("*")
            if p.is_file()
        }
        if render:
            with environment(snapshot(Path(os.environ["NATIVE_DOCX_FONT_FIXTURE"]))):
                for revision, data, is_final in [
                    (initial["revision"], original, False),
                    (asset["revision"], final, True),
                ]:
                    inspect_pages(data, final=is_final)
                    for index in range(3):
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
                                b.text for b in response.content if b.type == "text"
                            )
                        )
                        metadata = metadata.get("result", metadata)
                        assert metadata["success"], metadata
                        assert metadata["page_count"] == 3
                        png = base64.b64decode(
                            next(b.data for b in response.content if b.type == "image")
                        )
                        _, width, height, pixels = replay(data, index, 900)
                        with Image.open(io.BytesIO(png)) as actual:
                            assert (
                                actual.size == (width, height)
                                and actual.convert("RGB").tobytes() == pixels
                            )
        target = tmp_path / "verified.docx"
        published = await native(
            op="publish",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            output_path=str(target),
        )
        assert published["success"] and target.read_bytes() == final
        assert (
            len((await native(op="history", asset_id=asset["asset_id"]))["history"])
            == 3
        )
        assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
