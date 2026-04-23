"""
Job Tools - 非同步 ETL Job 管理 MCP 工具

包含：
- get_job_status: 查詢 Job 狀態
- list_jobs: 列出所有 Jobs
- cancel_job: 取消 Job
"""

from __future__ import annotations

from src.domain.job import JobStatus
from src.presentation.dependencies import job_service
from src.presentation.mcp_app import mcp


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
    if job.output_doc_ids:
        lines.append(f"**Output Documents:** {len(job.output_doc_ids)}")
        for doc_id in job.output_doc_ids:
            lines.append(f"  - `{doc_id}`")

    if job.error:
        lines.append(f"\n**Error:** {job.error}")

    if job.result and job.result.get("failed_files"):
        lines.append("\n**Failed Files:**")
        for item in job.result["failed_files"]:
            lines.append(f"  - `{item.get('file', '')}`: {item.get('error', '')}")

    if job.status == JobStatus.COMPLETED and job.result:
        lines.append("\n---")
        lines.append("✅ **Job completed successfully!**")
        lines.append(f"Created {len(job.output_doc_ids)} document(s).")
        lines.append("Use `inspect_document_manifest(<doc_id>)` to view details.")

    return "\n".join(lines)


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
        lines.append("")

    return "\n".join(lines)


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
