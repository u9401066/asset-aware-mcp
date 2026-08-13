"""Runtime MCP tool surface policy.

The codebase keeps legacy direct tools registered for explicit legacy mode, then
filters the public MCP v2 surface so agents see an easier default set.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from src.presentation.mcp_app import AssetAwareMCPServer

TOOL_SURFACE_ENV = "ASSET_AWARE_MCP_TOOL_SURFACE"
LEGACY_TOOLS_ENV = "ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS"

COMPACT_TOOLS = {
    "document",
    "document_asset",
    "evidence",
    "convert_document",
    "docx",
    "docx_table",
    "job",
    "knowledge",
    "etl_profile",
    "section",
    "plan_table",
    "table_manage",
    "table_data",
    "table_cite",
    "table_history",
    "table_draft",
    "discover_sources",
}

BALANCED_SHORTCUT_TOOLS = {
    "ingest_documents",
    "list_documents",
    "parse_pdf_structure",
    "fetch_document_asset",
    "find_evidence_spans",
    "verify_citation_ref",
    "citation_bundle",
    "ingest_docx",
    "get_docx_content",
    "save_docx",
    "get_job_status",
    "list_jobs",
    "docx_table_edit_plan",
}

BALANCED_TOOLS = COMPACT_TOOLS | BALANCED_SHORTCUT_TOOLS

_TRUE_VALUES = {"1", "true", "yes", "on"}


def requested_tool_surface() -> Literal["balanced", "compact", "legacy"]:
    """Resolve the configured public tool surface."""
    if os.getenv(LEGACY_TOOLS_ENV, "").strip().lower() in _TRUE_VALUES:
        return "legacy"

    configured = os.getenv(TOOL_SURFACE_ENV, "balanced").strip().lower()
    if configured in {"compact", "17"}:
        return "compact"
    if configured in {"legacy", "all", "full"}:
        return "legacy"
    return "balanced"


def public_tool_names_for_surface(
    surface: str | None = None,
) -> set[str] | None:
    """Return allowed public tool names, or None for the unfiltered legacy set."""
    resolved = (surface or requested_tool_surface()).strip().lower()
    if resolved in {"legacy", "all", "full"}:
        return None
    if resolved in {"compact", "17"}:
        return set(COMPACT_TOOLS)
    return set(BALANCED_TOOLS)


def apply_tool_surface_policy(mcp: AssetAwareMCPServer) -> None:
    """Filter registered tools through MCPServer's public removal API."""
    allowed = public_tool_names_for_surface()
    if allowed is None:
        return

    for tool_name in set(mcp.registered_tool_names) - allowed:
        mcp.remove_tool(tool_name)
