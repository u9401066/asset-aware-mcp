"""Tests for bounded MCP context emission helpers."""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Any, cast

import pytest
from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import MCPDeprecationWarning

from src.presentation import mcp_context


class HangingContext:
    async def report_progress(self, *_args, **_kwargs) -> None:
        await asyncio.Event().wait()


class ProtocolLoggingMustNotBeCalled:
    async def log(self, *_args, **_kwargs) -> None:
        raise AssertionError("MCP protocol logging is deprecated")


@pytest.mark.asyncio
async def test_report_progress_times_out_transport_backpressure(monkeypatch) -> None:
    monkeypatch.setattr(mcp_context, "MCP_CONTEXT_EMIT_TIMEOUT_SECONDS", 0.01)

    await asyncio.wait_for(
        mcp_context.report_progress(HangingContext(), 10, message="working"),
        timeout=0.2,
    )


@pytest.mark.asyncio
async def test_log_message_uses_standard_logger_without_protocol_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger=mcp_context.__name__)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        warnings.warn("unrelated warning remains visible", UserWarning, stacklevel=1)
        await mcp_context.log_message(
            cast(Any, ProtocolLoggingMustNotBeCalled()),
            "info",
            "working",
        )

    assert (mcp_context.__name__, logging.INFO, "working") in caplog.record_tuples
    assert any(item.category is UserWarning for item in caught)
    assert not any(issubclass(item.category, MCPDeprecationWarning) for item in caught)


@pytest.mark.asyncio
async def test_log_message_without_context_remains_noop(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG, logger=mcp_context.__name__)

    await mcp_context.log_message(None, "error", "must not be logged")

    assert "must not be logged" not in caplog.text


@pytest.mark.asyncio
async def test_stdio_tool_logging_stays_on_stderr_without_mcp_deprecation(
    tmp_path: Path,
) -> None:
    """Exercise SDK 2 Context injection over the real stdio transport."""
    stderr_path = tmp_path / "server.stderr.log"
    missing_pdf = tmp_path / "missing.pdf"
    env = {
        **os.environ,
        "DATA_DIR": str(tmp_path / "data"),
        "ENABLE_LIGHTRAG": "false",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONWARNINGS": "always",
    }
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.server"],
        env=env,
    )

    with stderr_path.open("w+", encoding="utf-8") as errlog:
        async with Client(stdio_client(params, errlog=errlog)) as client:
            result = await asyncio.wait_for(
                client.call_tool(
                    "parse_pdf_structure",
                    {"pdf_path": str(missing_pdf)},
                ),
                timeout=10,
            )
        errlog.flush()
        errlog.seek(0)
        stderr = errlog.read()

    assert not result.is_error
    assert "parse_pdf_structure start" in stderr
    assert "MCPDeprecationWarning" not in stderr
    assert "SEP-2577" not in stderr
