"""Regression tests for hard MCP response-size limits."""

from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.mcpserver.utilities.func_metadata import _convert_to_content

from src.presentation.response_limits import (
    format_limited_file_response,
    format_limited_json_response,
    format_limited_text_response,
    format_omitted_image_response,
    text_sha256,
)


def _mcp_text_content(result: object) -> str:
    """Return the SDK 2 TextContent text produced for a tool return value."""
    blocks = _convert_to_content(result)
    assert len(blocks) == 1
    text = getattr(blocks[0], "text", None)
    assert isinstance(text, str)
    return text


@pytest.mark.parametrize("content_chars", [2 * 1024 * 1024, 8 * 1024 * 1024])
def test_text_response_total_never_exceeds_cap(content_chars: int) -> None:
    text = ("evidence```資料" * ((content_chars // 13) + 1))[:content_chars]
    result = format_limited_text_response(
        title="Large evidence",
        text=text,
        max_chars=4_096,
        language="markdown",
        guidance="persist the full bundle",
    )

    assert len(result) <= 4_096
    assert len(_mcp_text_content(result)) <= 4_096
    assert text_sha256(text) in result
    assert "Full content was not inlined" in result


@pytest.mark.parametrize("content_chars", [2 * 1024 * 1024, 8 * 1024 * 1024])
def test_json_response_serialization_never_exceeds_cap(content_chars: int) -> None:
    payload = {
        "success": True,
        "doc_id": "doc_large",
        "entries": [{"quote": ("證據" * ((content_chars // 2) + 1))[:content_chars]}],
    }

    result = format_limited_json_response(
        title="Large JSON evidence",
        payload=payload,
        max_chars=4_096,
        guidance="persist the full bundle",
    )

    assert len(_mcp_text_content(result)) <= 4_096
    assert isinstance(result, dict)
    assert result["response_truncated"] is True
    assert result["sha256"].startswith("sha256:")


@pytest.mark.parametrize("unit", ["A", "🧪"])
def test_json_response_cap_matches_sdk2_text_content_serialization(unit: str) -> None:
    payload = {
        "success": True,
        "doc_id": "doc_sdk2",
        "entries": [
            {
                "quote": unit * (2 * 1024 * 1024),
                # Pretty-print indentation was the regression trigger: the old
                # compact estimate fit while SDK 2's TextContent exceeded cap.
                "section_hierarchy": ["nested"] * 700,
            }
        ],
    }

    result = format_limited_json_response(
        title="SDK 2 JSON evidence",
        payload=payload,
        max_chars=12_000,
    )

    assert len(_mcp_text_content(result)) <= 12_000
    assert isinstance(result, dict)
    assert result["response_truncated"] is True


def test_file_response_metadata_and_preview_fit_inside_cap(tmp_path: Path) -> None:
    path = tmp_path / "large.md"
    path.write_text("A```B" * (512 * 1024), encoding="utf-8")

    result = format_limited_file_response(
        title="Large file",
        path=path,
        max_chars=2_048,
        language="markdown",
    )

    assert len(result) <= 2_048
    assert len(_mcp_text_content(result)) <= 2_048
    assert str(path) in result
    assert "preview_chars" in result


def test_small_responses_remain_exact() -> None:
    text = "small exact response"
    payload = {"success": True, "quote": "small exact quote"}

    assert (
        format_limited_text_response(title="Small", text=text, max_chars=4_096) == text
    )
    assert (
        format_limited_json_response(title="Small", payload=payload, max_chars=4_096)
        == payload
    )


@pytest.mark.parametrize("cap", [1, 8, 64, 256])
def test_pathological_positive_caps_are_still_hard_limits(cap: int) -> None:
    text_result = format_limited_text_response(
        title="Tiny",
        text="x" * 10_000,
        max_chars=cap,
    )
    json_result = format_limited_json_response(
        title="Tiny",
        payload={"success": True, "quote": "x" * 10_000},
        max_chars=cap,
    )
    image_result = format_omitted_image_response(
        title="Tiny image",
        data="a" * 10_000,
        max_chars=cap,
    )

    assert len(text_result) <= cap
    assert len(_mcp_text_content(text_result)) <= cap
    assert len(_mcp_text_content(json_result)) <= cap
    assert len(image_result) <= cap
    assert len(_mcp_text_content(image_result)) <= cap
