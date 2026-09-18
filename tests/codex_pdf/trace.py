"""Validate actual Codex MCP events; agent prose cannot substitute for calls."""

from __future__ import annotations

import re
from typing import Any

from tests.codex_pdf.fixtures import TOOLS


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ValueError(message)


def result_text(call: dict[str, Any]) -> str:
    return "\n".join(
        block.get("text", "") for block in (call.get("result") or {}).get("content", [])
    )


def call_failed(call: dict[str, Any]) -> bool:
    text = result_text(call)
    return bool(
        call.get("status") != "completed"
        or call.get("error")
        or "❌" in text
        or re.search(r'"success"\s*:\s*false|"status"\s*:\s*"error"', text)
    )


def completed_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    require(
        any(event["type"] == "turn.completed" for event in events),
        "Codex turn did not complete",
    )
    calls = []
    for event in events:
        item = event.get("item", {})
        if event["type"] != "item.completed":
            continue
        kind = item.get("type")
        require(
            kind in {"agent_message", "reasoning", "plan", "mcp_tool_call"},
            f"Unexpected non-MCP action: {kind}",
        )
        if kind != "mcp_tool_call":
            continue
        require(item.get("server") == "asset_aware_under_test", "Unexpected MCP server")
        require(item.get("tool") in TOOLS, "Unexpected MCP tool")
        if not call_failed(item):
            calls.append(item)
    require(calls, "No completed MCP calls; agent prose is not evidence")
    required = {
        ("document", "preflight"),
        ("document", "ingest"),
        ("document", "inspect"),
        ("document", "export_assets"),
        ("get_job_status", None),
        ("table_manage", "create"),
        ("table_manage", "render"),
        ("table_manage", "delete"),
        ("table_manage", "list"),
        ("table_data", "add_rows"),
        ("table_data", "query_rows"),
        ("table_data", "update_cell"),
        ("table_data", "delete_row"),
        ("table_cite", "add"),
        ("table_cite", "get"),
    }
    observed = {
        (c["tool"], c["arguments"].get("op", c["arguments"].get("operation")))
        for c in calls
    }
    require(required <= observed, f"Missing workflow calls: {required - observed}")
    return calls


def tool_errors(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tool": event["item"]["tool"],
            "arguments": event["item"]["arguments"],
            "error": event["item"].get("error") or result_text(event["item"]),
        }
        for event in events
        if event["type"] == "item.completed"
        and event.get("item", {}).get("type") == "mcp_tool_call"
        and call_failed(event["item"])
    ]
