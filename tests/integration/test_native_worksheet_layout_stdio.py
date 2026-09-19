"""Optional real SDK2/Calc correction preserves the exact old workbook and PDF."""

import hashlib
import json
import os
import sys

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from tests.integration.test_native_pptx_shape_stdio import native
from tests.integration.test_native_workbook_rendition_stdio import (
    read_receipt,
    render_page,
)
from tests.native_workbook_layout_helpers import check_corrected_pdf
from tests.native_workbook_render_helpers import rendered_workbook


async def complete(client, **request):
    text, offset, digest = "", 0, None
    while True:
        result = await native(client, **request, text_offset=offset, text_limit=700)
        assert result["success"], result
        digest = digest or result["text_sha256"]
        assert result["text_sha256"] == digest
        assert result["excerpt_char_range"][0] == offset
        text += result["text_excerpt"]
        offset = result["next_text_offset"]
        if offset is None:
            break
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


@pytest.mark.skipif(
    os.environ.get("NATIVE_WORKBOOK_RENDER_TEST") != "1",
    reason="Set NATIVE_WORKBOOK_RENDER_TEST=1 with Calc installed",
)
@pytest.mark.timeout(180)
async def test_real_layout_correction_over_sdk2(tmp_path):
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
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        first = dict(asset)
        structure = await complete(
            client,
            op="read_workbook",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            workbook_view="references",
        )
        keys = {s["name"]: s["key"] for s in structure["worksheets"]}
        pdfs, images = [], []
        for name in ("before", "after"):
            if name == "after":
                for sheet, edit in (
                    ("First", {"axis": "row", "at": 1, "height_points": 36}),
                    ("Hidden", {"axis": "column", "at": 1, "width_ooxml": 30}),
                    ("Last", {"axis": "row", "at": 1, "height_points": 36}),
                ):
                    previous = await complete(
                        client,
                        op="read_worksheet_layout",
                        asset_id=asset["asset_id"],
                        revision=asset["revision"],
                        worksheet_key=keys[sheet],
                    )
                    changed = await native(
                        client,
                        op="update_worksheet_layout",
                        asset_id=asset["asset_id"],
                        expected_revision=asset["revision"],
                        worksheet_layout={"worksheet": keys[sheet], "edits": [edit]},
                    )
                    assert changed["success"], changed
                    current = await complete(client, **changed["review_request"])
                    assert (
                        current["operation_result"]["changes"][0]["before"]
                        == previous["layout"]
                    )
                    asset = changed["asset"]
            created = await native(
                client,
                op="create_workbook_rendition",
                asset_id=asset["asset_id"],
                revision=asset["revision"],
                workbook_rendition={
                    "name": name + ".pdf",
                    "mode": "whole_sheet",
                    "calculation": "recalculate",
                },
            )
            assert created["success"], created
            pdf = created["asset"]
            receipt = await read_receipt(client, pdf)
            assert (
                receipt["changes"][0]["source_reference"]["revision"]
                == asset["revision"]
            )
            inventory = await native(
                client,
                op="read_pdf",
                asset_id=pdf["asset_id"],
                revision=pdf["revision"],
            )
            rendered = [
                await render_page(client, pdf, page["locator"])
                for page in inventory["pages"]
            ]
            images.append(rendered)
            path = tmp_path / (name + ".pdf")
            assert (
                await native(
                    client,
                    op="publish",
                    asset_id=pdf["asset_id"],
                    expected_revision=pdf["revision"],
                    output_path=str(path),
                )
            )["success"]
            pdfs.append((pdf, path.read_bytes(), inventory))
        check_corrected_pdf(pdfs[0][1], pdfs[1][1])
        assert images[0][0] != images[1][0] and images[0][2] != images[1][2]
        historical = await render_page(
            client, pdfs[0][0], pdfs[0][2]["pages"][0]["locator"]
        )
        assert historical == images[0][0]
        old = await complete(
            client,
            op="read_worksheet_layout",
            asset_id=first["asset_id"],
            revision=first["revision"],
            worksheet_key=keys["First"],
        )
        assert "ht" not in old["layout"]["rows"][0]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
