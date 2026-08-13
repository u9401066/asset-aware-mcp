"""Helpers for returning conversion background-job responses."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server.mcpserver import Context  # noqa: TC002 - runtime injection marker

from src.application.job_service import JobProgressReporter
from src.presentation.mcp_context import log_message, report_progress

ConversionHandler = Callable[[JobProgressReporter], Awaitable[dict[str, Any]]]


async def create_conversion_job_response(
    job_service: Any,
    *,
    operation: str,
    source: str,
    target_format: str,
    parameters: dict[str, Any],
    handler: ConversionHandler,
    input_files: list[str] | None = None,
    ctx: Context | None = None,
) -> str:
    """Create a conversion job and return a MCP-friendly Markdown response."""
    await report_progress(ctx, 5, message=f"Queueing {operation} conversion")
    try:
        job = await job_service.create_conversion_job(
            operation=operation,
            input_files=input_files or [],
            parameters=parameters,
            handler=handler,
        )
    except (RuntimeError, ValueError) as e:
        await log_message(ctx, "error", f"conversion job rejected: {e}")
        return (
            "# ❌ Could Not Create Conversion Job\n\n"
            f"{e!s}\n\n"
            "Use `list_jobs(active_only=True)` to inspect running work, then retry."
        )

    await report_progress(ctx, 100, message=f"Queued conversion job {job.job_id}")
    await log_message(ctx, "info", f"conversion job created: {job.job_id}")
    estimate = job.estimated_duration_seconds or "unknown"
    return "\n".join(
        [
            "# Conversion Job Created",
            "",
            "✅ Conversion is running in the background worker.",
            f"- **job_id:** `{job.job_id}`",
            f"- **operation:** `{operation}`",
            f"- **source:** `{source}`",
            f"- **target_format:** `{target_format}`",
            f"- **estimated_duration_seconds:** {estimate}",
            "",
            f'Check progress with `get_job_status("{job.job_id}")`.',
        ]
    )


def conversion_result_payload(
    result: dict[str, Any],
    *,
    operation: str,
    source: str,
    target_format: str,
) -> dict[str, Any]:
    """Normalize conversion service output for persisted job results."""
    payload = dict(result)
    payload.setdefault("operation", operation)
    payload.setdefault("source", source)
    payload.setdefault("target_format", target_format)
    return payload
