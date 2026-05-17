"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

# ============================================================================
# Docx Tools
# ============================================================================


class TestServerStartup:
    """Tests for server.py configuration."""

    def _list_tools(self, **env_overrides: str) -> set[str]:
        env = os.environ.copy()
        env.pop("ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS", None)
        env.pop("ASSET_AWARE_MCP_TOOL_SURFACE", None)
        env.update(env_overrides)
        result = subprocess.run(
            [sys.executable, "-m", "src.server", "list-tools", "--json"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
        return set(json.loads(result.stdout)["tools"])

    def test_configure_logging(self) -> None:
        """configure_logging sets up handlers without error."""
        from src.presentation.server import configure_logging

        configure_logging()  # Should not raise

    def test_tool_count(self) -> None:
        """Balanced default exposes agent-friendly shortcuts without tool overload."""
        registered = self._list_tools(ASSET_AWARE_MCP_TOOL_SURFACE="balanced")

        assert registered == {
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

    def test_compact_surface_lists_only_facade_tools(self) -> None:
        """Compact mode exposes the 17 operation-based entrypoints only."""
        tools = self._list_tools(ASSET_AWARE_MCP_TOOL_SURFACE="compact")

        assert tools == {
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

    def test_legacy_surface_keeps_direct_tools_when_enabled(self) -> None:
        """Legacy mode keeps direct tools for existing clients and allow-lists."""
        tools = self._list_tools(ASSET_AWARE_MCP_TOOL_SURFACE="legacy")

        assert "document" in tools
        assert "section" in tools
        assert "ingest_documents" in tools
        assert "save_docx" in tools
        assert "delete_document" in tools
        assert len(tools) >= 63

    def test_legacy_flag_keeps_direct_tools_for_compatibility(self) -> None:
        """The older compatibility flag still enables the full surface."""
        tools = self._list_tools(ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS="true")

        assert "delete_document" in tools
        assert len(tools) >= 63


# ============================================================================
# Job Service — Concurrency Guard
# ============================================================================
