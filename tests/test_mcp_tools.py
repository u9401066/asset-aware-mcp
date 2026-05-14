"""Integration-style assertions for MCP tool registration and job tools."""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.domain.job import Job, JobProgress, JobStatus, JobType
from src.presentation.dependencies import job_service
from src.presentation.server import mcp
from src.presentation.tools.document_tools import ingest_documents, list_documents
from src.presentation.tools.job_tools import cancel_job, get_job_status, list_jobs


def test_tool_registration() -> None:
    """Core MCP tools must be registered."""
    expected_tools = {
        "document",
        "document_asset",
        "docx",
        "docx_table",
        "convert_document",
        "evidence",
        "job",
        "etl_profile",
        "knowledge",
        "citation_bundle",
        "detect_etl_profile",
        "docx_table_edit_plan",
        "ingest_documents",
        "get_job_status",
        "list_jobs",
        "cancel_job",
        "list_documents",
        "inspect_document_manifest",
        "fetch_document_asset",
        "consult_knowledge_graph",
    }

    registered_tools = {tool.name for tool in mcp._tool_manager._tools.values()}

    assert expected_tools <= registered_tools


def test_cli_help_exits_without_starting_stdio_server() -> None:
    """The packaged console help path must be a bounded diagnostic command."""
    completed = subprocess.run(
        [sys.executable, "-m", "src.server", "--help"],
        check=True,
        capture_output=True,
        text=True,
        timeout=5,
    )

    output = completed.stdout + completed.stderr
    assert "Asset-Aware MCP stdio server and runtime diagnostics" in output
    assert "doctor" in output
    assert "list-tools" in output
    assert "Starting Asset-Aware MCP server" not in output


async def test_registered_mcp_tool_runs_list_documents() -> None:
    """Smoke the FastMCP registered tool path, not only direct function calls."""
    tool = mcp._tool_manager._tools["list_documents"]

    result = await tool.run({})

    assert isinstance(result, str)
    assert "Documents" in result or "No documents found" in result


async def test_stdio_server_lists_tools_and_calls_list_documents() -> None:
    """Smoke the real MCP stdio transport used by packaged clients."""
    env = {
        **os.environ,
        "ENABLE_LIGHTRAG": "false",
        "PYTHONIOENCODING": "utf-8",
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env=env,
    )

    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await asyncio.wait_for(session.initialize(), timeout=10)
        tools = await asyncio.wait_for(session.list_tools(), timeout=10)
        tool_names = {tool.name for tool in tools.tools}

        result = await asyncio.wait_for(
            session.call_tool("list_documents", {}),
            timeout=10,
        )

    assert {"list_documents", "consult_knowledge_graph"} <= tool_names
    assert not result.isError
    assert result.content


def test_stdio_smoke_script_exercises_real_mcp_transport() -> None:
    """The release smoke script must exercise the same MCP transport."""
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/smoke_mcp_stdio.py",
            "--timeout",
            "10",
            "--",
            sys.executable,
            "-m",
            "src.server",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    output = completed.stdout + completed.stderr
    assert '"status": "ok"' in output
    assert '"called_tool": "list_documents"' in output


async def test_get_job_status_reports_manifest_and_content_artifacts() -> None:
    """Completed ingest jobs should expose artifacts needed by follow-up tools."""
    job = Job(
        job_id="job_smoke_artifacts",
        job_type=JobType.INGEST_PDF,
        status=JobStatus.COMPLETED,
        input_files=["paper.pdf"],
        output_doc_ids=["doc_smoke"],
        progress=JobProgress(total_steps=1, current_step=1, percentage=100),
        result={
            "documents": [
                {
                    "doc_id": "doc_smoke",
                    "file": "paper.pdf",
                    "artifacts": {
                        "manifest": "data/doc_smoke/manifest.json",
                        "markdown": "data/doc_smoke/content.md",
                    },
                }
            ]
        },
    )
    await job_service.job_store.create(job)

    try:
        result = await get_job_status(job_id=job.job_id)
    finally:
        await job_service.job_store.delete(job.job_id)

    assert "data/doc_smoke/manifest.json" in result
    assert "data/doc_smoke/content.md" in result


async def test_async_job_tools_report_created_job(tmp_path: Path) -> None:
    """Async ingest should create an observable job even when processing later fails."""
    test_file = tmp_path / "dummy.pdf"
    test_file.write_bytes(b"%PDF-1.4 test")

    result = await ingest_documents(file_paths=[str(test_file)], async_mode=True)
    match = re.search(r"(job_\d{8}_\d{6}_[a-f0-9]+)", result)

    assert match is not None, result
    job_id = match.group(1)

    try:
        await asyncio.sleep(0.2)
        status = await get_job_status(job_id=job_id)
        jobs = await list_jobs(active_only=False)
        cancel_result = await cancel_job(job_id=job_id)
        documents = await list_documents()

        assert job_id in status
        assert job_id in jobs
        assert (
            "cancelled" in cancel_result.lower()
            or "could not cancel" in cancel_result.lower()
        )
        assert isinstance(documents, str)
    finally:
        await job_service.job_store.delete(job_id)
