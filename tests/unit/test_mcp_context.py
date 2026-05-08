"""Tests for bounded MCP context emission helpers."""

from __future__ import annotations

import asyncio

import pytest

from src.presentation import mcp_context


class HangingContext:
    async def report_progress(self, *_args, **_kwargs) -> None:
        await asyncio.Event().wait()

    async def log(self, *_args, **_kwargs) -> None:
        await asyncio.Event().wait()


@pytest.mark.asyncio
async def test_report_progress_times_out_transport_backpressure(monkeypatch) -> None:
    monkeypatch.setattr(mcp_context, "MCP_CONTEXT_EMIT_TIMEOUT_SECONDS", 0.01)

    await asyncio.wait_for(
        mcp_context.report_progress(HangingContext(), 10, message="working"),
        timeout=0.2,
    )


@pytest.mark.asyncio
async def test_log_message_times_out_transport_backpressure(monkeypatch) -> None:
    monkeypatch.setattr(mcp_context, "MCP_CONTEXT_EMIT_TIMEOUT_SECONDS", 0.01)

    await asyncio.wait_for(
        mcp_context.log_message(HangingContext(), "info", "working"),
        timeout=0.2,
    )
