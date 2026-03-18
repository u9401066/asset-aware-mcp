from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from mcp.server.fastmcp import Context
else:
    Context = Any

logger = logging.getLogger(__name__)

ToolProgressCallback = Callable[[int, int, str, str], Awaitable[None] | None]


async def report_progress(
    ctx: Context | None,
    progress: float,
    total: float = 100,
    message: str | None = None,
) -> None:
    """Safely emit MCP-native progress when a context is available."""
    if ctx is None:
        return

    try:
        result = ctx.report_progress(progress, total=total, message=message)
        if inspect.isawaitable(result):
            await result
    except Exception:
        logger.debug("Failed to report MCP progress", exc_info=True)


async def log_message(
    ctx: Context | None,
    level: Literal["debug", "info", "warning", "error"],
    message: str,
    logger_name: str | None = None,
) -> None:
    """Safely emit MCP log messages when a context is available."""
    if ctx is None:
        return

    try:
        result = ctx.log(level, message, logger_name=logger_name)
        if inspect.isawaitable(result):
            await result
    except Exception:
        logger.debug("Failed to emit MCP log", exc_info=True)


def create_subrange_progress_callback(
    ctx: Context | None,
    start: float,
    end: float,
    total: float = 100,
) -> ToolProgressCallback:
    """Map internal step progress into a portion of the outer MCP progress bar."""

    async def _callback(step: int, total_steps: int, phase: str, message: str) -> None:
        bounded_total = max(total_steps, 1)
        clamped_step = min(max(step, 0), bounded_total)
        ratio = clamped_step / bounded_total
        mapped = start + ((end - start) * ratio)
        await report_progress(ctx, mapped, total=total, message=message or phase)

    return _callback


async def invoke_progress_callback(
    callback: ToolProgressCallback | None,
    step: int,
    total_steps: int,
    phase: str,
    message: str,
) -> None:
    """Call an internal progress callback if one was provided."""
    if callback is None:
        return

    result: Any = callback(step, total_steps, phase, message)
    if inspect.isawaitable(result):
        await result
