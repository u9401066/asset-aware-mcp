"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

# ============================================================================
# Docx Tools
# ============================================================================


class TestServerStartup:
    """Tests for server.py configuration."""

    def test_configure_logging(self) -> None:
        """configure_logging sets up handlers without error."""
        from src.presentation.server import configure_logging

        configure_logging()  # Should not raise

    def test_tool_count(self) -> None:
        """Legacy and consolidated MCP tools are registered during compatibility window."""
        from src.presentation.mcp_app import mcp

        registered = {t.name for t in mcp._tool_manager._tools.values()}
        expected = {
            "document",
            "document_asset",
            "docx",
            "docx_table",
            "convert_document",
            "evidence",
            "job",
            "etl_profile",
            "knowledge",
            "ingest_documents",
            "ingest_docx",
            "save_docx",
            "citation_bundle",
            "detect_etl_profile",
            "docx_table_edit_plan",
            "find_evidence_spans",
            "verify_citation_ref",
            "get_job_status",
        }
        assert expected <= registered
        assert len(registered) == 62, f"Expected 62 tools, got {len(registered)}"


# ============================================================================
# Job Service — Concurrency Guard
# ============================================================================
