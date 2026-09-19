"""Actual PDF ingestion, immutable extraction snapshots and mixed CSL over SDK2."""

import asyncio
import base64
import hashlib
import io
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

import pymupdf
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image, ImageChops

from src.infrastructure.file_storage import FileStorage
from tests.integration.test_csl_citations_stdio import complete_csl
from tests.integration.test_native_pdf_regions_stdio import native, unwrap
from tests.integration.test_pdf_asset_stdio_e2e import _build_pdf, _unwrap
from tests.unit.test_csl_processor import document


def preview(response):
    """Read image metadata from TextContent, independent of SDK structured wrapping."""
    assert not response.is_error
    metadata = unwrap(response)
    images = [block for block in response.content if block.type == "image"]
    assert len(images) == 1
    png = base64.b64decode(images[0].data, validate=True)
    assert hashlib.sha256(png).hexdigest() == metadata["image_sha256"]
    return metadata, png


@pytest.mark.timeout(180)
async def test_etl_capture_mixed_csl_and_historical_png_over_sdk2(tmp_path):
    if not shutil.which("node"):
        pytest.skip("CSL integration requires optional Node.js")
    source = tmp_path / "source.pdf"
    _build_pdf(source)
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    data_dir = tmp_path / "data"
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env={
            **os.environ,
            "DATA_DIR": str(data_dir),
            "ENABLE_LIGHTRAG": "false",
            "ASSET_AWARE_DISABLE_DOTENV": "true",
            "ETL_ENGINE": "pymupdf",
            "ASSET_AWARE_MCP_TOOL_SURFACE": "balanced",
        },
    )
    async with Client(stdio_client(params)) as client:
        contract, _, _ = await complete_csl(client, op="csl_contract")
        assert contract["etl_sources"]["configured"]
        assert (
            contract["etl_sources"]["reference_schema"]["additionalProperties"] is False
        )
        assert "inspect_etl_source" in contract["etl_sources"]["operations"]
        ingested = _unwrap(
            await client.call_tool(
                "document",
                {
                    "op": "ingest",
                    "file_paths": [str(source)],
                    "extract_figures": True,
                    "index_knowledge_graph": False,
                    "async_mode": False,
                },
                read_timeout_seconds=120,
            )
        )
        job = re.search(r"job_\d{8}_\d{6}_[a-f0-9]+", str(ingested))
        assert job, ingested
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            ingested = _unwrap(
                await client.call_tool("get_job_status", {"job_id": job.group(0)})
            )
            if re.search(r"(?m)^# Job Status:.*\bCOMPLETED\b", str(ingested)):
                break
            assert not re.search(
                r"(?m)^# Job Status:.*\b(?:FAILED|CANCELLED)\b", str(ingested)
            ), ingested
            await asyncio.sleep(0.1)
        else:
            pytest.fail(f"Ingestion did not finish: {ingested}")
        match = re.search(r"doc_[a-z0-9_]+", str(ingested))
        assert match, ingested
        doc_id = match.group(0)
        storage = FileStorage(data_dir)
        manifest = storage.load_manifest(doc_id)
        assert (
            manifest is not None and manifest.assets.tables and manifest.assets.figures
        )
        found = _unwrap(
            await client.call_tool(
                "evidence",
                {
                    "op": "find",
                    "doc_id": doc_id,
                    "query": "production image",
                    "limit": 1,
                },
            )
        )
        spans = [
            json.loads(m.group(1))
            for m in re.finditer(r"```json\s*(.*?)```", str(found), re.DOTALL)
        ]
        assert len(spans) == 1 and spans[0]["source_type"] == "span"
        selectors = {
            "span": {
                "doc_id": doc_id,
                "source_type": "span",
                "source_id": spans[0]["span_id"],
            },
            "table": {
                "doc_id": doc_id,
                "source_type": "table",
                "source_id": manifest.assets.tables[0].id,
            },
            "figure": {
                "doc_id": doc_id,
                "source_type": "figure",
                "source_id": manifest.assets.figures[0].id,
            },
        }
        references, captured_results, images = {}, {}, {}
        for kind, selector in selectors.items():
            inspected, _, _ = await complete_csl(
                client, op="inspect_etl_source", ref=selector
            )
            raw_ref = inspected["asset_ref"]
            denied = _unwrap(
                await client.call_tool(
                    "evidence",
                    {
                        "op": "capture_etl_source",
                        "ref": raw_ref,
                        "expected_text_sha256": "0" * 64,
                    },
                )
            )
            assert not denied["success"]
            existing = (
                set((data_dir / "citation-sources").glob("*"))
                if (data_dir / "citation-sources").exists()
                else set()
            )
            assert len(existing) == len(references)
            captured, _, _ = await complete_csl(
                client, op="capture_etl_source", ref=raw_ref
            )
            reference = captured["reference"]
            assert reference["source_type"] == kind
            assert captured["record"] == inspected["record"]
            references[kind], captured_results[kind] = reference, captured
            read, _, _ = await complete_csl(client, op="read_etl_source", ref=reference)
            assert read == captured
            response = await client.call_tool(
                "evidence",
                {"op": "view_etl_source", "ref": reference, "render_size": 640},
            )
            metadata, png = preview(response)
            assert metadata["reference"] == reference and metadata["source_page"] == 1
            with pymupdf.open(source) as pdf:
                page = pdf[0]
                scale = 640 / max(page.rect.width, page.rect.height)
                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(scale, scale), alpha=False, annots=True
                )
            expected = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            actual = Image.open(io.BytesIO(png)).convert("RGB")
            assert (
                actual.size == expected.size
                and ImageChops.difference(actual, expected).getbbox() is None
            )
            images[kind] = png
        workbook = (
            await native(
                client,
                op="create",
                workbook={
                    "name": "Result.xlsx",
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
        raw = document().model_dump()
        raw["sources"] = {**references, "native": cell}
        for i, kind in enumerate(selectors):
            raw["clusters"][i]["cites"][0]["source_keys"] = [kind]
        raw["clusters"][2]["cites"][0]["source_keys"].append("native")
        result, sha, _ = await complete_csl(
            client, op="render_citations", citation_document=raw
        )
        published, pub_sha, publication = await complete_csl(
            client,
            op="render_citations",
            citation_document=raw,
            wiki_root=str(tmp_path / "wiki"),
        )
        assert published == result and pub_sha == sha and publication["success"]
        wiki = Path(publication["output_dir"])
        for kind, reference in references.items():
            snapshot = (
                data_dir / "citation-sources" / ("native-" + reference["snapshot_id"])
            )
            source_record = result["sources"][kind]
            for name, artifact in source_record["snapshot_artifacts"].items():
                assert (wiki / artifact["name"]).read_bytes() == (
                    snapshot / name
                ).read_bytes()
            assert (wiki / source_record["attachment"]["name"]).read_bytes() == original
        files_before = {p.name: p.read_bytes() for p in wiki.iterdir()}
        deleted = _unwrap(
            await client.call_tool("document", {"op": "delete", "doc_id": doc_id})
        )
        assert not (data_dir / doc_id).exists(), deleted
        for kind, reference in references.items():
            historical, _, _ = await complete_csl(
                client, op="read_etl_source", ref=reference
            )
            assert historical == captured_results[kind]
            response = await client.call_tool(
                "evidence",
                {"op": "view_etl_source", "ref": reference, "render_size": 640},
            )
            metadata, png = preview(response)
            assert metadata["reference"] == reference and metadata["source_page"] == 1
            assert png == images[kind]
        historical, old_sha, reused = await complete_csl(
            client,
            op="render_citations",
            citation_document=raw,
            wiki_root=str(tmp_path / "wiki"),
        )
        assert historical == result and old_sha == sha and reused["reused"]
        assert files_before == {p.name: p.read_bytes() for p in wiki.iterdir()}
        snapshot = (
            data_dir
            / "citation-sources"
            / ("native-" + references["span"]["snapshot_id"])
        )
        (snapshot / "canonical.md").write_text("tampered", encoding="utf-8")
        rejected = _unwrap(
            await client.call_tool(
                "evidence",
                {
                    "op": "render_citations",
                    "citation_document": raw,
                    "wiki_root": str(tmp_path / "must-not-publish"),
                },
            )
        )
        assert not rejected["success"] and not (tmp_path / "must-not-publish").exists()
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
