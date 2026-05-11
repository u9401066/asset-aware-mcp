"""Integration-style assertions for MCP tool registration and job tools."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

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
