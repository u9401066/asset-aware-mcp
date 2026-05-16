"""Regression tests for section MCP tool response sizing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from src.domain.entities import FetchResult
from src.domain.value_objects import AssetType


async def test_get_section_content_large_section_returns_preview(
    monkeypatch,
) -> None:
    """Large section bodies should be summarized instead of inlined."""
    from src.presentation.tools import section_tools

    large_section = "# Methods\n\n" + ("A" * 80_000)
    mock_assets = MagicMock()
    mock_assets.fetch_asset = AsyncMock(
        return_value=FetchResult(
            doc_id="doc_big",
            asset_type=AssetType.SECTION,
            asset_id="sec_methods",
            success=True,
            text_content=large_section,
            page=7,
            line_start=10,
            line_end=500,
            line_source="document",
        )
    )
    monkeypatch.setattr(section_tools, "asset_service", mock_assets)

    result = await section_tools.get_section_content("doc_big", "sec_methods")

    assert len(result) < 20_000
    assert "sha256:" in result
    assert "sec_methods" in result
    assert "A" * 30_000 not in result
