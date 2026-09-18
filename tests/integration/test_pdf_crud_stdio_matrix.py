"""Real SDK2 PDF/data CRUD matrix; Codex perception is a separate opt-in run."""

from __future__ import annotations

import base64
import io
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image

from tests.codex_pdf.audit import (
    validate_bundle,
    validate_citations,
    validate_excel,
    validate_rows,
    validate_scan_pixels,
)
from tests.codex_pdf.fixtures import (
    build_pdf,
    expected_rows,
    server_environment,
    sha256,
)
from tests.codex_pdf.sdk import call, exercise_tables, ingest


async def _check_preflight(client: Client, source: Path, mode: str) -> None:
    result = await call(client, "document", op="preflight", pdf_path=str(source))
    assert result["source"]["sha256"] == sha256(source)
    assert result["page_count"] == 3
    expected = (
        ["native"] * 3
        if mode == "digital"
        else ["scanned"] * 3
        if mode == "scanned"
        else ["native", "scanned", "scanned"]
    )
    assert [page["classification"] for page in result["pages"]] == expected
    assert result["pages"][2]["locator"]["rotation_degrees"] == 90
    assert result["pages"][2]["locator"]["page_bbox"] == [0, 0, 572, 732]


async def _check_images(
    client: Client, manifest: dict, source: Path, mode: str
) -> None:
    for figure in manifest["assets"]["figures"]:
        result = await client.call_tool(
            "document_asset",
            {
                "op": "get",
                "doc_id": manifest["doc_id"],
                "asset_type": "figure",
                "asset_id": figure["id"],
                "max_size": 0,
            },
        )
        assert not result.is_error
        images = [block for block in result.content if block.type == "image"]
        assert len(images) == 1, result
        with Image.open(io.BytesIO(base64.b64decode(images[0].data))) as image:
            assert image.size == (figure["width"], figure["height"])
        texts = "\n".join(
            block.text for block in result.content if block.type == "text"
        )
        assert f"**Page:** {figure['page']}" in texts
    validate_scan_pixels(source, manifest, mode)


async def _workflow(client: Client, directory: Path, source: Path, mode: str) -> None:
    await _check_preflight(client, source, mode)
    doc_id = await ingest(client, source)
    manifest_path = directory / doc_id / f"{doc_id}_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["source_engine"] == "pymupdf"
    assert manifest["source_pdf_sha256"] == sha256(source)
    await _check_images(client, manifest, source, mode)
    table = await exercise_tables(client, directory, manifest)
    validate_rows(table["rows"], expected_rows())
    validate_citations(table, manifest)
    validate_excel(directory / "tables", expected_rows())
    exported = await call(client, "document", op="export_assets", doc_id=doc_id)
    assert exported["success"] is True
    bundle = Path(exported["output_dir"])
    validate_bundle(bundle, sha256(source))
    first = {p.relative_to(bundle): sha256(p) for p in bundle.rglob("*") if p.is_file()}
    await call(client, "document", op="export_assets", doc_id=doc_id)
    assert first == {
        p.relative_to(bundle): sha256(p) for p in bundle.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("mode", ["digital", "scanned", "mixed"])
@pytest.mark.timeout(240)
async def test_pdf_crud_matrix_over_real_stdio(tmp_path: Path, mode: str) -> None:
    source = tmp_path / "source.pdf"
    directory = tmp_path / "data"
    build_pdf(source, mode)
    before = (sha256(source), source.stat().st_mtime_ns)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={**os.environ, **server_environment(directory)},
    )
    with (tmp_path / "server.stderr.log").open("w", encoding="utf-8") as errors:
        async with Client(stdio_client(params, errlog=errors)) as client:
            await _workflow(client, directory, source, mode)
    assert (sha256(source), source.stat().st_mtime_ns) == before
