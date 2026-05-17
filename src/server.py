"""Console entry point for Asset-Aware MCP.

With no arguments this module preserves the historical behavior and starts the
stdio MCP server. Operator commands such as ``--help`` and ``doctor`` run without
opening stdio transport, so VSIX/package smoke checks can diagnose the runtime.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def run_stdio_server() -> None:
    from src.presentation.server import main as run_server

    run_server()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="asset-aware-mcp",
        description=(
            "Asset-Aware MCP stdio server and runtime diagnostics. "
            "Run with no arguments to start the MCP server."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("serve", help="start the stdio MCP server")

    doctor = subparsers.add_parser("doctor", help="print runtime diagnostics")
    doctor.add_argument("--json", action="store_true", help="emit diagnostics as JSON")

    health = subparsers.add_parser("health", help="alias for doctor")
    health.add_argument("--json", action="store_true", help="emit diagnostics as JSON")

    list_tools = subparsers.add_parser(
        "list-tools", help="list registered MCP tool names"
    )
    list_tools.add_argument("--json", action="store_true", help="emit tools as JSON")
    return parser


def _write(text: str) -> None:
    sys.stdout.write(text)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        run_stdio_server()
        return 0

    parser = _build_parser()
    try:
        parsed = parser.parse_args(args)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        return 0 if exc.code is None else 1

    if parsed.command == "serve":
        run_stdio_server()
        return 0
    if parsed.command in {"doctor", "health"}:
        from src.presentation.diagnostics import (
            collect_runtime_status,
            format_runtime_status,
        )

        status = collect_runtime_status()
        if parsed.json:
            _write(json.dumps(status, indent=2, sort_keys=True) + "\n")
        else:
            _write(format_runtime_status(status))
        return 0
    if parsed.command == "list-tools":
        from src.presentation.diagnostics import registered_tool_names
        from src.presentation.tool_surface import requested_tool_surface

        tool_names = registered_tool_names()
        if parsed.json:
            _write(
                json.dumps(
                    {
                        "count": len(tool_names),
                        "surface": requested_tool_surface(),
                        "tools": tool_names,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        else:
            _write(
                f"# Asset-Aware MCP Tools ({requested_tool_surface()}, "
                f"{len(tool_names)} tools)\n"
            )
            _write("\n".join(tool_names) + "\n")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
