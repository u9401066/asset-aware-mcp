"""Actual SDK2 correction of clipped rows, repeated headers and complete page review."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import sys
from functools import partial
from pathlib import Path

import pymupdf
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.codex_docx_structure.fonts import environment, snapshot
from tests.integration.test_native_docx_grid_stdio import complete
from tests.integration.test_native_docx_stdio_e2e import _native
from tests.native_docx_layout_helpers import ROWS, clipped_document, inspect_pages


@pytest.mark.parametrize("render", [False, True])
@pytest.mark.timeout(180)
async def test_table_layout_correction_over_sdk2(tmp_path, render):
    if render and not os.environ.get("NATIVE_DOCX_FONT_FIXTURE"):
        pytest.skip("Set NATIVE_DOCX_FONT_FIXTURE with optional Writer")
    original = clipped_document()
    source = tmp_path / "clipped.docx"
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
        assert params.env is not None
        params.env["FONTCONFIG_FILE"] = str(
            Path(os.environ["NATIVE_DOCX_FONT_FIXTURE"]) / "with-cjk.conf"
        )
    async with Client(stdio_client(params)) as client:
        native = partial(_native, client)
        contract = await native(op="contract", for_op="update_docx_table_grid")
        assert contract["docx_table_layout_enabled"]
        asset = (await native(op="register", source_path=str(source)))["asset"]
        listed = await native(
            op="read_docx",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            limit=100,
        )
        reference = next(
            b["evidence"] for b in listed["blocks"] if b["type"] == "table"
        )
        read = {
            "op": "read_docx_table",
            "asset_id": asset["asset_id"],
            "revision": asset["revision"],
            "docx_table_reference": reference,
        }
        before = await complete(native, read)
        assert before["repeat_header_prefix_length"] == 0
        assert before["row_layout"][2]["heights"] == [
            {"value_twips": 260, "rule": "exact"}
        ]
        edits = [
            {"op": "set_header_rows", "count": 2},
            {
                "op": "set_row_layout",
                "index": 2,
                "count": ROWS,
                "height": {"rule": "auto"},
                "split": "prevent",
            },
        ]
        invalid = await native(
            op="update_docx_table_grid",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_table_grid={
                "reference": reference,
                "edits": [edits[0], {**edits[1], "count": ROWS + 1}],
            },
        )
        assert not invalid["success"] and "exceeds" in invalid["error"]
        result = await native(
            op="update_docx_table_grid",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            docx_table_grid={"reference": reference, "edits": edits},
        )
        assert result["success"], result
        after = await complete(native, result["review_request"])
        assert after["repeat_header_prefix_length"] == 2
        assert all(
            r["split"] == "prevent"
            and r["heights"] == [{"value_twips": 0, "rule": "auto"}]
            for r in after["row_layout"][2:]
        )
        assert after["regions"] == before["regions"]
        receipt = after["operation_result"]["changes"][0]["edits"]
        assert receipt[0]["before"] == [] and receipt[0]["after"] == [0, 1]
        assert receipt[1]["before"][0]["heights"][0]["rule"] == "exact"
        assert receipt[1]["after"][0]["heights"][0]["rule"] == "auto"
        assert await complete(native, read) == before
        noop = await native(
            op="update_docx_table_grid",
            asset_id=asset["asset_id"],
            expected_revision=result["asset"]["revision"],
            docx_table_grid={"reference": after["evidence"], "edits": edits},
        )
        assert noop["success"] and not noop["operation_result"]["committed"]
        history = await native(op="history", asset_id=asset["asset_id"])
        assert len(history["history"]) == 2
        verified = await native(op="verify", reference=reference)
        assert verified["valid"] and not verified["is_current_managed_revision"]
        destination = tmp_path / "corrected.docx"
        published = await native(
            op="publish",
            asset_id=asset["asset_id"],
            expected_revision=result["asset"]["revision"],
            output_path=str(destination),
        )
        assert published["success"], published
        if render:
            fonts = snapshot(Path(os.environ["NATIVE_DOCX_FONT_FIXTURE"]))
            with environment(fonts):
                for revision, data, corrected in [
                    (asset["revision"], original, False),
                    (result["asset"]["revision"], destination.read_bytes(), True),
                ]:
                    pdf_bytes, texts = inspect_pages(data, corrected)
                    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
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
                            images = [b for b in wire.content if b.type == "image"]
                            assert len(images) == 1
                            png = base64.b64decode(images[0].data, validate=True)
                            assert (
                                hashlib.sha256(png).hexdigest()
                                == metadata["image_sha256"]
                            )
                            page = pdf[index]
                            scale = 900 / max(page.rect.width, page.rect.height)
                            pixels = page.get_pixmap(
                                matrix=pymupdf.Matrix(scale, scale), alpha=False
                            )
                            with Image.open(io.BytesIO(png)) as image:
                                assert image.size == (pixels.width, pixels.height)
                                assert image.convert("RGB").tobytes() == bytes(
                                    pixels.samples
                                )
                            assert metadata["page_count"] == len(texts)
                            assert metadata["next_page_index"] == (
                                index + 1 if index + 1 < len(texts) else None
                            )
        assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
