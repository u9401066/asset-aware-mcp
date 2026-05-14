"""
Unit tests for MCP presentation-layer tools.

Tests tool functions directly (without MCP transport) to validate
error handling, input validation, and response formatting.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

# ============================================================================
# Docx Tools
# ============================================================================


class TestProfileTools:
    """Tests for profile_tools.py MCP functions."""

    async def test_list_etl_profiles(self) -> None:
        """list_etl_profiles returns profile list."""
        from src.presentation.tools.profile_tools import list_etl_profiles

        result = await list_etl_profiles()
        assert "profiles" in result
        assert result["count"] >= 1
        assert any(p["name"] == "default" for p in result["profiles"])

    async def test_get_etl_profile_not_found(self) -> None:
        """get_etl_profile returns error for unknown profile."""
        from src.presentation.tools.profile_tools import get_etl_profile

        result = await get_etl_profile("nonexistent_profile")
        assert result["success"] is False
        assert "available" in result

    async def test_get_current_etl_profile(self) -> None:
        """get_current_etl_profile returns current profile info."""
        from src.presentation.tools.profile_tools import get_current_etl_profile

        result = await get_current_etl_profile()
        assert "name" in result

    async def test_etl_profile_op_routes_set(self) -> None:
        """etl_profile(op='set') delegates to the existing profile switcher."""
        with patch(
            "src.presentation.tools.profile_tools.set_etl_profile",
            new_callable=AsyncMock,
        ) as mock_set:
            mock_set.return_value = {"success": True}
            from src.presentation.tools.profile_tools import etl_profile

            result = await etl_profile("set", name="arxiv")

        assert result == {"success": True}
        mock_set.assert_awaited_once_with("arxiv")

    async def test_etl_profile_op_rejects_missing_name(self) -> None:
        """etl_profile(op='get') requires a profile name."""
        from src.presentation.tools.profile_tools import etl_profile

        result = await etl_profile("get")

        assert result["success"] is False
        assert "name is required" in result["error"]

    async def test_etl_profile_op_routes_load(self) -> None:
        """etl_profile(op='load') delegates custom profile loading."""
        with patch(
            "src.presentation.tools.profile_tools.load_etl_profile_from_json",
            new_callable=AsyncMock,
        ) as mock_load:
            mock_load.return_value = {"success": True}
            from src.presentation.tools.profile_tools import etl_profile

            result = await etl_profile("load", json_path="profile.json")

        assert result == {"success": True}
        mock_load.assert_awaited_once_with("profile.json")

    async def test_detect_etl_profile_from_sample_text(self) -> None:
        """detect_etl_profile recommends a profile with reasons."""
        from src.presentation.tools.profile_tools import detect_etl_profile

        result = await detect_etl_profile(
            sample_text="arXiv:2601.12345\n1. Introduction\nBody",
        )

        assert result["success"] is True
        assert result["recommended_profile"] == "arxiv"
        assert result["confidence"] > 0.4
        assert any("arXiv" in reason for reason in result["reasons"])

    async def test_set_etl_profile_rebinds_document_tool_services(self) -> None:
        """Profile switching updates already-imported presentation service aliases."""
        from src.presentation import dependencies
        from src.presentation.tools import document_tools, profile_tools, table_tools

        old_profile_name = dependencies.etl_profile.name

        result = await profile_tools.set_etl_profile("default")

        try:
            assert result["success"] is True
            assert document_tools.document_service is dependencies.document_service
            assert document_tools.pdf_extractor is dependencies.pdf_extractor
            assert table_tools.document_service is dependencies.document_service
            assert (
                dependencies.job_service.document_service
                is dependencies.document_service
            )
        finally:
            dependencies.rebuild_for_profile(old_profile_name)
            document_tools.document_service = dependencies.document_service
            document_tools.pdf_extractor = dependencies.pdf_extractor
            table_tools.document_service = dependencies.document_service
            dependencies.job_service.set_document_service(dependencies.document_service)


# ============================================================================
# Knowledge Tools
# ============================================================================
