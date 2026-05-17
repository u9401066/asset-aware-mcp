#!/usr/bin/env python3
"""Smoke a real MCP stdio server command."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_TIMEOUT_SECONDS = 15


async def _smoke(command: list[str], *, timeout: float) -> dict[str, object]:
    env = {
        **os.environ,
        "DATA_DIR": os.environ.get(
            "DATA_DIR", str(Path(tempfile.mkdtemp(prefix="asset-aware-mcp-data-")))
        ),
        "ENABLE_LIGHTRAG": os.environ.get("ENABLE_LIGHTRAG", "false"),
        "PYTHONIOENCODING": "utf-8",
    }
    params = StdioServerParameters(command=command[0], args=command[1:], env=env)

    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await asyncio.wait_for(session.initialize(), timeout=timeout)
        tools = await asyncio.wait_for(session.list_tools(), timeout=timeout)
        tool_names = sorted(tool.name for tool in tools.tools)
        result = await asyncio.wait_for(
            session.call_tool("list_documents", {}),
            timeout=timeout,
        )

    required = {"list_documents", "knowledge"}
    missing = sorted(required - set(tool_names))
    if missing:
        raise RuntimeError(f"MCP stdio server missing required tools: {missing}")
    if result.isError:
        raise RuntimeError("MCP stdio list_documents returned an error result")

    return {
        "command": command,
        "tool_count": len(tool_names),
        "required_tools": sorted(required),
        "called_tool": "list_documents",
        "status": "ok",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a real MCP initialize/list-tools/list_documents stdio smoke."
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Timeout in seconds for each MCP operation.",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to launch after --, for example: -- asset-aware-mcp",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        command = ["asset-aware-mcp"]

    summary = asyncio.run(_smoke(command, timeout=args.timeout))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
