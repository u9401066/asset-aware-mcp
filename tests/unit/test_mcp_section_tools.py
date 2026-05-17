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


async def test_section_tree_facade_matches_direct(monkeypatch) -> None:
    from src.presentation.tools import section_tools

    async def fake_tree(**kwargs):
        return {"ok": True, "kwargs": kwargs}

    monkeypatch.setattr(section_tools, "list_section_tree", fake_tree)

    result = await section_tools.section(
        op="tree",
        doc_id="doc_1",
        max_depth=2,
        format="flat",
    )

    assert result == {
        "ok": True,
        "kwargs": {"doc_id": "doc_1", "max_depth": 2, "format": "flat"},
    }


async def test_section_detail_facade_matches_direct(monkeypatch) -> None:
    from src.presentation.tools import section_tools

    async def fake_detail(**kwargs):
        return {"ok": True, "kwargs": kwargs}

    monkeypatch.setattr(section_tools, "get_section_detail", fake_detail)

    result = await section_tools.section(
        op="detail",
        doc_id="doc_1",
        path="Intro/Methods",
        max_chars=2048,
    )

    assert result == {
        "ok": True,
        "kwargs": {"doc_id": "doc_1", "path": "Intro/Methods", "max_chars": 2048},
    }


async def test_section_blocks_facade_matches_direct(monkeypatch) -> None:
    from src.presentation.tools import section_tools

    async def fake_blocks(**kwargs):
        return {"ok": True, "kwargs": kwargs}

    monkeypatch.setattr(section_tools, "get_section_blocks", fake_blocks)

    result = await section_tools.section(
        op="blocks",
        doc_id="doc_1",
        path="Intro",
        include_children=False,
        block_types=["Text"],
        limit=7,
    )

    assert result == {
        "ok": True,
        "kwargs": {
            "doc_id": "doc_1",
            "path": "Intro",
            "include_children": False,
            "block_types": ["Text"],
            "limit": 7,
        },
    }


async def test_section_search_facade_matches_direct(monkeypatch) -> None:
    from src.presentation.tools import section_tools

    async def fake_search(**kwargs):
        return {"ok": True, "kwargs": kwargs}

    monkeypatch.setattr(section_tools, "search_sections", fake_search)

    result = await section_tools.section(
        op="search",
        doc_id="doc_1",
        query="shock",
        fuzzy=False,
        max_chars=4096,
    )

    assert result == {
        "ok": True,
        "kwargs": {
            "doc_id": "doc_1",
            "query": "shock",
            "fuzzy": False,
            "max_chars": 4096,
        },
    }


async def test_section_content_facade_matches_direct(monkeypatch) -> None:
    from src.presentation.tools import section_tools

    async def fake_content(**kwargs):
        return {"ok": True, "kwargs": kwargs}

    monkeypatch.setattr(section_tools, "get_section_content", fake_content)

    result = await section_tools.section(
        op="content",
        doc_id="doc_1",
        section_id="sec_methods",
        max_chars=1024,
    )

    assert result == {
        "ok": True,
        "kwargs": {
            "doc_id": "doc_1",
            "section_id": "sec_methods",
            "max_chars": 1024,
        },
    }


async def test_section_unknown_op_returns_error() -> None:
    from src.presentation.tools import section_tools

    result = await section_tools.section(op="unknown", doc_id="doc_1")

    assert result["success"] is False
    assert "Unknown section op" in result["error"]
