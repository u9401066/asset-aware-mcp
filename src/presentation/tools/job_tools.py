"""
Job Tools - 非同步 ETL Job 管理 MCP 工具

包含：
- get_job_status: 查詢 Job 狀態
- list_jobs: 列出所有 Jobs
- cancel_job: 取消 Job
"""

from __future__ import annotations

from typing import Any

from src.application.document_readiness_service import (
    AI_READINESS_ARTIFACTS,
    DocumentReadinessService,
)
from src.domain.job import JobStatus
from src.presentation.dependencies import job_service, repository
from src.presentation.mcp_app import mcp
from src.presentation.response_limits import format_limited_text_response


def _normalize_op(op: str) -> str:
    return op.strip().lower().replace("-", "_")


def _unsupported_job_op(op: str, allowed: set[str]) -> str:
    allowed_ops = ", ".join(sorted(allowed))
    return f"Unsupported job op `{op}`. Supported operations: {allowed_ops}."


def _missing_job_param(name: str) -> str:
    return f"Missing required parameter: {name} is required."


def _format_artifact_lines(artifacts: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for name in _DOCUMENT_ARTIFACT_NAMES:
        path = artifacts.get(name)
        if path:
            lines.append(f"    - {name}: `{path}`")
    return lines


_DOCUMENT_ARTIFACT_NAMES: tuple[str, ...] = tuple(
    name for name, _template in AI_READINESS_ARTIFACTS
)


def _refresh_document_artifacts(doc_id: str, artifacts: Any) -> dict[str, str]:
    return DocumentReadinessService(repository).discover_artifacts(
        doc_id,
        artifacts=artifacts,
    )


def _format_document_next_lines(doc_id: str) -> list[str]:
    return [
        f'    - next: `document(op="prepare_ai", doc_id="{doc_id}")`',
        f'    - next: `document(op="inspect", doc_id="{doc_id}")`',
        f'    - next: `document(op="audit", doc_id="{doc_id}")`',
    ]


@mcp.tool()
async def get_job_status(job_id: str) -> str:
    """
    Get the status of an ETL job.

    Use this to check progress of document ingestion started with `ingest_documents`.

    Args:
        job_id: Job ID returned from `ingest_documents`

    Returns:
        Job status including progress, phase, and result (if completed)

    Example:
        get_job_status("job_20251226_143000_abc12345")
    """
    job = await job_service.get_job(job_id)

    if job is None:
        return f"❌ Job not found: `{job_id}`"

    status_emoji = {
        JobStatus.PENDING: "⏳",
        JobStatus.PROCESSING: "🔄",
        JobStatus.COMPLETED: "✅",
        JobStatus.FAILED: "❌",
        JobStatus.CANCELLED: "🚫",
    }

    lines = [
        f"# Job Status: {status_emoji.get(job.status, '❓')} {job.status.value.upper()}\n",
        f"**Job ID:** `{job.job_id}`",
        f"**Type:** {job.job_type.value}",
        f"**Created:** {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    if not job.is_terminal:
        progress = job.progress.percentage
        bar_filled = int(progress / 5)
        bar_empty = 20 - bar_filled
        progress_bar = f"[{'█' * bar_filled}{'░' * bar_empty}] {progress:.0f}%"
        lines.append(f"\n**Progress:** {progress_bar}")
        lines.append(f"**Phase:** {job.progress.current_phase}")
        lines.append(f"**Status:** {job.progress.message}")
    else:
        if job.duration_seconds:
            lines.append(f"**Duration:** {job.duration_seconds:.1f}s")

    lines.append(f"\n**Input Files:** {len(job.input_files)}")
    for file_path in job.input_files:
        lines.append(f"  - `{file_path}`")

    if job.result and isinstance(job.result.get("interrupted_job"), dict):
        interrupted = job.result["interrupted_job"]
        lines.append("\n**Interrupted Job Recovery:**")
        lines.append("- **reason:** MCP server restarted before completion")
        previous_phase = interrupted.get("previous_phase")
        if previous_phase:
            lines.append(f"- **last_phase:** {previous_phase}")
        previous_message = interrupted.get("previous_message")
        if previous_message:
            lines.append(f"- **last_message:** {previous_message}")
        previous_error = interrupted.get("previous_error")
        if previous_error:
            lines.append(f"- **last_error:** {previous_error}")

    result_documents = []
    if job.result and isinstance(job.result.get("documents"), list):
        result_documents = job.result["documents"]

    if result_documents:
        lines.append(f"**Output Documents:** {len(result_documents)}")
        for item in result_documents:
            doc_id = item.get("doc_id", "")
            backend = item.get("backend", "unknown")
            lines.append(f"  - `{doc_id}`")
            lines.append(f"    - backend: `{backend}`")
            if backend == "pymupdf_fallback":
                lines.append(
                    "    - degraded: Marker requested but PyMuPDF fallback was used"
                )
            artifacts = _refresh_document_artifacts(doc_id, item.get("artifacts"))
            if artifacts:
                lines.append("    - artifacts:")
                lines.extend(_format_artifact_lines(artifacts))
            warnings = item.get("warnings")
            if isinstance(warnings, list) and warnings:
                lines.append("    - warnings:")
                for warning in warnings:
                    lines.append(f"      - {warning}")
            if doc_id:
                lines.extend(_format_document_next_lines(doc_id))
    elif job.output_doc_ids:
        lines.append(f"**Output Documents:** {len(job.output_doc_ids)}")
        for doc_id in job.output_doc_ids:
            lines.append(f"  - `{doc_id}`")
            lines.extend(_format_document_next_lines(doc_id))

    if job.result and isinstance(job.result.get("conversion"), dict):
        conversion = job.result["conversion"]
        lines.append("\n**Conversion Result:**")
        lines.append(f"- **operation:** `{conversion.get('operation', 'conversion')}`")
        if conversion.get("source"):
            lines.append(f"- **source:** `{conversion.get('source')}`")
        if conversion.get("target_format"):
            lines.append(f"- **target_format:** `{conversion.get('target_format')}`")
        if conversion.get("mode"):
            lines.append(f"- **mode:** {conversion.get('mode')}")
        if conversion.get("output_path"):
            lines.append(f"- **output_path:** `{conversion.get('output_path')}`")
        if conversion.get("format"):
            lines.append(f"- **format:** {conversion.get('format')}")
        for key in (
            "figures_embedded",
            "tables_found",
            "slides_created",
            "figure_slides",
        ):
            if key in conversion:
                lines.append(f"- **{key}:** {conversion.get(key)}")

    if job.error:
        lines.append(f"\n**Error:** {job.error}")

    if job.result and job.result.get("failed_files"):
        lines.append("\n**Failed Files:**")
        for item in job.result["failed_files"]:
            lines.append(f"  - `{item.get('file', '')}`: {item.get('error', '')}")
            warnings = item.get("warnings")
            if isinstance(warnings, list) and warnings:
                for warning in warnings:
                    lines.append(f"    - warning: {warning}")

    if job.result and job.result.get("warnings"):
        lines.append("\n**Warnings:**")
        for warning in job.result["warnings"]:
            lines.append(f"  - {warning}")

    if job.status == JobStatus.COMPLETED and job.result:
        lines.append("\n---")
        lines.append("✅ **Job completed successfully!**")
        if job.result and isinstance(job.result.get("conversion"), dict):
            output_path = job.result["conversion"].get("output_path")
            if output_path:
                lines.append(f"Created converted artifact: `{output_path}`")
            else:
                lines.append("Conversion finished.")
        else:
            lines.append(f"Created {len(job.output_doc_ids)} document(s).")
        if result_documents:
            lines.append("Use the per-document `next` commands above to continue.")
        elif job.result and isinstance(job.result.get("conversion"), dict):
            lines.append("Open the converted artifact path above to review output.")
        else:
            lines.append(
                'Use `document(op="prepare_ai", doc_id=<doc_id>)` to view details.'
            )

    return format_limited_text_response(
        title=f"Job Status: {job_id}",
        text="\n".join(lines),
        language="markdown",
        guidance="inspect artifact paths directly for full outputs",
    )


@mcp.tool()
async def list_jobs(active_only: bool = False) -> str:
    """
    List ETL jobs.

    Args:
        active_only: If True, only show pending/processing jobs

    Returns:
        List of jobs with status and progress
    """
    if active_only:
        jobs = await job_service.list_active_jobs()
        title = "Active Jobs"
    else:
        jobs = await job_service.list_jobs(limit=20)
        title = "Recent Jobs"

    if not jobs:
        if active_only:
            return "No active jobs. All ETL tasks have completed."
        return "No jobs found. Use `ingest_documents` to process files."

    status_emoji = {
        JobStatus.PENDING: "⏳",
        JobStatus.PROCESSING: "🔄",
        JobStatus.COMPLETED: "✅",
        JobStatus.FAILED: "❌",
        JobStatus.CANCELLED: "🚫",
    }

    lines = [f"# {title} ({len(jobs)})\n"]

    for job in jobs:
        emoji = status_emoji.get(job.status, "❓")
        progress = (
            f"{job.progress_percentage:.0f}%"
            if job.progress_percentage < 100
            else "Done"
        )

        lines.append(f"## {emoji} `{job.job_id}`")
        lines.append(f"- **Type:** {job.job_type.value}")
        lines.append(f"- **Status:** {job.status.value} ({progress})")
        if job.current_phase:
            lines.append(f"- **Phase:** {job.current_phase}")
        if job.message:
            lines.append(f"- **Message:** {job.message}")
        if job.error:
            lines.append(f"- **Error:** {job.error}")
        lines.append(
            f"- **Files:** {job.input_file_count} → {job.output_doc_count} docs"
        )
        detail = await job_service.get_job(job.job_id)
        if detail is not None:
            if detail.input_files:
                lines.append("- **Input Files:**")
                for file_path in detail.input_files:
                    lines.append(f"  - `{file_path}`")
            if detail.output_doc_ids:
                lines.append("- **Partial/Output Documents:**")
                for doc_id in detail.output_doc_ids:
                    lines.append(f"  - `{doc_id}`")
            if detail.result and isinstance(detail.result.get("interrupted_job"), dict):
                interrupted = detail.result["interrupted_job"]
                previous_phase = interrupted.get("previous_phase")
                previous_message = interrupted.get("previous_message")
                previous_error = interrupted.get("previous_error")
                if previous_phase:
                    lines.append(f"- **Last Phase Before Restart:** {previous_phase}")
                if previous_message:
                    lines.append(
                        f"- **Last Message Before Restart:** {previous_message}"
                    )
                if previous_error:
                    lines.append(f"- **Last Error Before Restart:** {previous_error}")
        lines.append("")

    return format_limited_text_response(
        title="Job List",
        text="\n".join(lines),
        language="markdown",
        guidance="use get_job_status(job_id) for a focused job",
    )


@mcp.tool()
async def cancel_job(job_id: str) -> str:
    """
    Cancel a running ETL job.

    Args:
        job_id: Job ID to cancel

    Returns:
        Confirmation message
    """
    success = await job_service.cancel_job(job_id)

    if success:
        return f"🚫 Job `{job_id}` has been cancelled."
    else:
        return (
            f"❌ Could not cancel job `{job_id}`. "
            "It may have already completed or doesn't exist."
        )


@mcp.tool()
async def job(
    op: str,
    job_id: str | None = None,
    active_only: bool = False,
) -> Any:
    """
    Consolidated job entrypoint over get/list/cancel.

    Existing job tools stay registered for backwards compatibility.
    """
    operation = _normalize_op(op)
    if operation in {"get", "status"}:
        if not job_id:
            return _missing_job_param("job_id")
        return await get_job_status(job_id)
    if operation == "list":
        return await list_jobs(active_only=active_only)
    if operation == "cancel":
        if not job_id:
            return _missing_job_param("job_id")
        return await cancel_job(job_id)
    return _unsupported_job_op(op, {"cancel", "get", "list"})
