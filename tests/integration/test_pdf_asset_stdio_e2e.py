"""Real stdio regression for PDF -> reusable agent/Foam assets."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

import pymupdf as fitz
import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from PIL import Image


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _text(result: Any) -> str:
    return "\n".join(
        str(block.text)
        for block in result.content
        if getattr(block, "text", None) is not None
    )


def _unwrap(result: Any) -> Any:
    assert not result.is_error, _text(result)
    structured = result.structured_content
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return structured["result"]
    if structured is not None:
        return structured
    text = _text(result)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _build_pdf(path: Path) -> None:
    """Create text, grid-table, and a PNG larger than a typical IPC pipe."""
    pixels = hashlib.shake_256(b"asset-aware-mcp-ipc-regression").digest(640 * 640 * 3)
    image = Image.frombytes("RGB", (640, 640), pixels)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    assert len(buffer.getvalue()) > 512 * 1024

    document = fitz.open()
    page = document.new_page(width=612, height=792)
    page.insert_text(
        (54, 60),
        "Asset-Aware MCP production image worker regression",
        fontsize=14,
    )
    page.insert_textbox(
        fitz.Rect(54, 80, 558, 145),
        "This document exercises real MCP SDK 2 stdio preflight, background "
        "ingestion, citation artifacts, a table, a large raster figure, and "
        "deterministic reusable Foam asset export.",
        fontsize=10,
    )

    table_rect = fitz.Rect(54, 160, 558, 250)
    rows = 3
    columns = 3
    for row in range(rows + 1):
        y = table_rect.y0 + (table_rect.height * row / rows)
        page.draw_line((table_rect.x0, y), (table_rect.x1, y))
    for column in range(columns + 1):
        x = table_rect.x0 + (table_rect.width * column / columns)
        page.draw_line((x, table_rect.y0), (x, table_rect.y1))
    cells = (
        ("Asset", "Page", "Verified"),
        ("Text", "1", "yes"),
        ("Figure", "1", "yes"),
    )
    for row, values in enumerate(cells):
        for column, value in enumerate(values):
            x0 = table_rect.x0 + (table_rect.width * column / columns)
            y0 = table_rect.y0 + (table_rect.height * row / rows)
            page.insert_text((x0 + 5, y0 + 19), value, fontsize=9)

    page.insert_image(fitz.Rect(100, 280, 512, 692), stream=buffer.getvalue())
    page.insert_text(
        (100, 716), "Figure 1: deterministic high-entropy raster fixture.", fontsize=10
    )
    document.save(path)
    document.close()


def _tree_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _assert_bundle_integrity(
    bundle_root: Path,
    bundle_manifest: dict[str, Any],
    source_sha256: str,
) -> None:
    """Verify the exported records, locators, citations, media, and inventory."""
    records = [
        json.loads(line)
        for line in (bundle_root / "assets.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line
    ]
    assert len(records) == bundle_manifest["asset_count"]
    assert {record["asset_key"] for record in records} == {
        asset["asset_key"] for asset in bundle_manifest["assets"]
    }
    assert any(
        record["citation"]["status"] == "citation_ready" for record in records
    ), "the bundle must retain at least one citation-ready text span"

    for artifact in bundle_manifest["artifacts"]:
        artifact_path = bundle_root / artifact["path"]
        assert artifact_path.is_file()
        assert artifact_path.stat().st_size == artifact["size_bytes"]
        assert _sha256(artifact_path) == artifact["sha256"]

    for record in records:
        assert record["source_identity"]["source_sha256"] == source_sha256
        locator = record["locator"]
        assert isinstance(locator["page"], int) and locator["page"] >= 1
        assert locator["locator_version"]
        if locator["source_revision_id"]:
            assert (
                locator["source_revision_id"]
                == record["source_identity"]["canonical_markdown_sha256"]
            )
            assert (
                locator["locator_source_sha256"]
                == record["source_identity"]["locator_source_sha256"]
            )
        else:
            assert locator["locator_version"] == "asset-manifest-v1"
            assert record["asset_type"] in {"table", "figure"}

        expected_record = dict(record)
        record_sha256 = expected_record.pop("record_sha256")
        assert (
            hashlib.sha256(_canonical_json(expected_record).encode("utf-8")).hexdigest()
            == record_sha256
        )

        note_path = bundle_root / record["foam"]["path"]
        note_text = note_path.read_text(encoding="utf-8")
        assert record["foam"]["anchor"] in note_text
        assert record_sha256 in note_text

        citation = record["citation"]
        assert citation["status"] in {
            "citation_ready",
            "asset_locator_only",
            "unavailable",
        }
        if citation["status"] == "citation_ready":
            assert citation["evidence_refs"]
            for evidence in citation["evidence_refs"]:
                assert evidence["doc_id"] == record["doc_id"]
                assert (
                    evidence["source_revision_id"]
                    == record["source_identity"]["canonical_markdown_sha256"]
                )
                assert (
                    hashlib.sha256(evidence["quote"].encode("utf-8")).hexdigest()
                    == evidence["quote_sha256"]
                )

        content = record["content"]
        if record["asset_type"] == "text":
            assert (
                hashlib.sha256(content["text"].encode("utf-8")).hexdigest()
                == record["content_sha256"]
            )
        elif record["asset_type"] == "table":
            table_text = content["markdown"] or content["preview"] or content["caption"]
            assert (
                hashlib.sha256(table_text.encode("utf-8")).hexdigest()
                == record["content_sha256"]
            )
        else:
            assert content["media_available"] is True
            media_path = bundle_root / content["media_path"]
            assert media_path.is_file()
            assert _sha256(media_path) == content["media_sha256"]
            assert content["media_sha256"] == record["content_sha256"]

    media_sizes = [
        (bundle_root / record["content"]["media_path"]).stat().st_size
        for record in records
        if record["asset_type"] == "figure" and record["content"]["media_available"]
    ]
    assert media_sizes and max(media_sizes) > 512 * 1024, (
        "the large-raster regression must cross the former IPC pipe threshold"
    )

    hash_payload = dict(bundle_manifest)
    bundle_sha256 = hash_payload.pop("bundle_sha256")
    assert (
        hashlib.sha256(_canonical_json(hash_payload).encode("utf-8")).hexdigest()
        == bundle_sha256
    )


@pytest.mark.timeout(180)
async def test_production_default_stdio_exports_text_table_figure_and_foam(
    tmp_path: Path,
) -> None:
    """The isolated default must drain large worker results without a bypass."""
    source = tmp_path / "source.pdf"
    data_dir = tmp_path / "data"
    stderr_path = tmp_path / "server.stderr.log"
    _build_pdf(source)
    before_sha256 = _sha256(source)
    before_mtime_ns = source.stat().st_mtime_ns

    env = {
        **os.environ,
        "DATA_DIR": str(data_dir),
        "ENABLE_LIGHTRAG": "false",
        "ETL_ENGINE": "pymupdf",
        "ASSET_AWARE_MCP_TOOL_SURFACE": "balanced",
        "ASSET_AWARE_DISABLE_DOTENV": "true",
        "PYMUPDF_TEXT_DOCUMENT_TIMEOUT_SECONDS": "30",
        "PYMUPDF_IMAGE_DOCUMENT_TIMEOUT_SECONDS": "25",
        "PYMUPDF_FAST_IMAGE_DOCUMENT_TIMEOUT_SECONDS": "90",
        "PYMUPDF_TABLE_DOCUMENT_TIMEOUT_SECONDS": "25",
        "PYMUPDF_CAPTION_DOCUMENT_TIMEOUT_SECONDS": "20",
        "PYMUPDF_SAFETY_AUDIT_DOCUMENT_TIMEOUT_SECONDS": "20",
        "PYMUPDF_NATIVE_STRUCTURE_DOCUMENT_TIMEOUT_SECONDS": "10",
        "PYMUPDF_TABLE_TIMEOUT_SECONDS": "4",
        "PYMUPDF_IMAGE_TIMEOUT_SECONDS": "3",
        "PYMUPDF_WORKER_RESULT_MAX_MIB": "512",
        "PYMUPDF_ENABLE_VECTOR_IMAGES": "true",
        "PYMUPDF_ENABLE_REGION_IMAGES": "true",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONWARNINGS": "always",
    }
    # Explicit positive production values override any caller environment: this
    # regression must never pass by silently selecting the direct bypass path.
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env=env,
    )

    with stderr_path.open("w+", encoding="utf-8") as errlog:
        async with Client(stdio_client(params, errlog=errlog)) as client:
            tools = (await client.list_tools()).tools
            assert len(tools) == 30
            assert not [
                tool.name
                for tool in tools
                if "ctx" in (tool.input_schema.get("properties") or {})
            ]

            preflight = _unwrap(
                await client.call_tool(
                    "document",
                    {"op": "preflight", "pdf_path": str(source)},
                    read_timeout_seconds=30,
                )
            )
            assert preflight["status"] == "ok"
            assert preflight["source"]["sha256"] == before_sha256
            assert preflight["page_count"] == 1

            accepted = str(
                _unwrap(
                    await client.call_tool(
                        "document",
                        {
                            "op": "ingest",
                            "file_paths": [str(source)],
                            "extract_figures": True,
                            "index_knowledge_graph": False,
                        },
                        read_timeout_seconds=30,
                    )
                )
            )
            job_match = re.search(r"job_\d{8}_\d{6}_[a-f0-9]+", accepted)
            assert job_match, accepted

            deadline = time.monotonic() + 45
            status = ""
            while time.monotonic() < deadline:
                status = str(
                    _unwrap(
                        await client.call_tool(
                            "get_job_status",
                            {"job_id": job_match.group(0)},
                            read_timeout_seconds=15,
                        )
                    )
                )
                if re.search(r"(?m)^# Job Status:.*\bCOMPLETED\b", status):
                    break
                assert not re.search(
                    r"(?m)^# Job Status:.*\b(?:FAILED|CANCELLED)\b",
                    status,
                ), status
                await asyncio.sleep(0.1)
            else:
                raise AssertionError(f"ingest did not complete: {status}")

            doc_match = re.search(r"(?m)^  - `(doc_[A-Za-z0-9_.-]+)`\s*$", status)
            assert doc_match, status
            doc_id = doc_match.group(1)
            manifest_path = data_dir / doc_id / f"{doc_id}_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["source_pdf_sha256"] == before_sha256
            assert manifest["source_engine"] == "pymupdf"
            assert len(manifest["assets"]["tables"]) >= 1
            assert len(manifest["assets"]["figures"]) >= 1

            exported = _unwrap(
                await client.call_tool(
                    "document",
                    {
                        "op": "export_assets",
                        "doc_id": doc_id,
                        "output_dir": "agent-assets",
                    },
                    read_timeout_seconds=60,
                )
            )
            assert exported["success"] is True
            assert exported["bundle_version"] == "agent-asset-bundle-v1"
            assert exported["counts"]["text"] >= 1
            assert exported["counts"]["table"] >= 1
            assert exported["counts"]["figure"] >= 1

            bundle_root = Path(exported["output_dir"])
            bundle_manifest = json.loads(
                (bundle_root / "manifest.json").read_text(encoding="utf-8")
            )
            assert bundle_manifest["source_identity"]["source_sha256"] == before_sha256
            assert (
                len(list((bundle_root / "notes").glob("*.md")))
                == exported["asset_count"]
            )
            assert list((bundle_root / "media").iterdir())
            _assert_bundle_integrity(bundle_root, bundle_manifest, before_sha256)

            first_hashes = _tree_hashes(bundle_root)
            repeated = _unwrap(
                await client.call_tool(
                    "document",
                    {
                        "op": "export_assets",
                        "doc_id": doc_id,
                        "output_dir": "agent-assets",
                    },
                    read_timeout_seconds=60,
                )
            )
            assert repeated["success"] is True
            assert _tree_hashes(bundle_root) == first_hashes

        errlog.flush()
        errlog.seek(0)
        stderr = errlog.read()

    assert "image extraction timed out" not in stderr
    assert "skipping images" not in stderr
    assert "image extraction worker produced no result" not in stderr
    assert "image extraction worker failed" not in stderr
    assert "using isolated page-crop fallback" not in stderr
    assert "fast image fallback" not in stderr
    assert "MCPDeprecationWarning" not in stderr
    assert "Traceback (most recent call last)" not in stderr
    assert " | ERROR " not in stderr
    assert _sha256(source) == before_sha256
    assert source.stat().st_mtime_ns == before_mtime_ns
