"""Actual SDK2 PNG transport and per-cell scan provenance with historical evidence."""

import base64
import hashlib
import io
import json
import os
import sys
from pathlib import Path

import pymupdf
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image, ImageChops, ImageStat

from tests.codex_pdf.fixtures import build_pdf
from tests.integration.test_native_derivation_stdio import ledger_read
from tests.native_pdf_helpers import page_reference


def unwrap(response):
    result = json.loads("".join(c.text for c in response.content if c.type == "text"))
    return result.get("result", result)


async def native(client, **request):
    return unwrap(
        await client.call_tool("document", {"op": "native", "native_request": request})
    )


@pytest.mark.timeout(120)
async def test_scanned_regions_to_structured_cells_over_sdk2(tmp_path):
    source = tmp_path / "scan.pdf"
    build_pdf(source, "scanned")
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
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
        asset = (await native(client, op="register", source_path=str(source)))["asset"]
        parent = page_reference(original, 0, asset["asset_id"]).model_dump(mode="json")
        rect = [145 / 612, 185 / 792, 225 / 612, 230 / 792]
        response = await client.call_tool(
            "document",
            {
                "op": "native",
                "native_request": {
                    "op": "read_pdf_region",
                    "reference": parent,
                    "pdf_region": {"rect": rect},
                    "render_size": 160,
                },
            },
        )
        result = unwrap(response)
        assert result["success"] and "response_truncated" not in result
        images = [c for c in response.content if c.type == "image"]
        assert len(images) == 1
        png = base64.b64decode(images[0].data, validate=True)
        assert hashlib.sha256(png).hexdigest() == result["image_sha256"]
        with pymupdf.open(source) as pdf:
            assert pdf[0].get_text() == ""
            pix = pdf[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
        expected = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).crop(
            (290, 370, 450, 460)
        )
        actual = Image.open(io.BytesIO(png))
        assert actual.size == expected.size
        difference = ImageChops.difference(actual, expected)
        # MuPDF may resample clipped embedded scans differently by 1-2 levels.
        # Keep exact pixel geometry and a strict independent error bound.
        assert (
            max(high for _, high in difference.getextrema()) <= 2
            and max(ImageStat.Stat(difference).mean) < 0.1
        ), (
            difference.getbbox(),
            difference.getextrema(),
            result["rendering"],
        )
        reference = result["region"]["evidence"]
        assert (await native(client, op="verify", reference=reference))["valid"]
        workbook = (
            await native(
                client,
                op="create",
                workbook={
                    "name": "counts.xlsx",
                    "edits": [{"sheet": "Sheet1", "cell": "A1", "value": "007"}],
                },
            )
        )["asset"]
        cell = (
            await native(
                client,
                op="read_cell",
                asset_id=workbook["asset_id"],
                sheet="Sheet1",
                cell="A1",
            )
        )["cell"]["evidence"]
        _, sha = await ledger_read(client, workbook["asset_id"])
        recorded = await native(
            client,
            op="record_derivation",
            asset_id=workbook["asset_id"],
            expected_derivations_sha256=sha,
            derivation={
                "target": cell,
                "sources": [reference],
                "agent": "SDK2 test fixture",
                "activity": "Transcribe explicit scanned Count region",
                "review": {
                    "semantic_accuracy": "not_checked",
                    "notes": "Transport fixture with known value; not a live semantic review",
                },
            },
        )
        assert recorded["success"]
        wiki = await native(
            client,
            op="export_wiki",
            asset_id=workbook["asset_id"],
            output_dir=str(tmp_path / "wiki"),
        )
        root = Path(wiki["output_dir"])
        manifest = json.loads((root / "manifest.json").read_text())
        region = next(iter(manifest["derivations"]["region_records"].values()))
        assert (
            json.loads((root / region["record_file"]).read_text())["evidence"]
            == reference
        )
        changed = await native(
            client,
            op="update_pdf",
            asset_id=asset["asset_id"],
            expected_revision=asset["revision"],
            pdf_edits=[{"reference": parent, "rotation": 90}],
        )
        assert changed["success"]
        proof = await native(client, op="verify", reference=reference)
        assert proof["valid"] and not proof["is_current_managed_revision"]
        historical = await native(
            client, op="read_pdf_region", reference=reference, render_size=160
        )
        assert historical["image_sha256"] == result["image_sha256"]
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
