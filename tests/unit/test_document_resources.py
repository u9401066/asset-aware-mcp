from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_resource_document_sections_shows_first_section_line_range() -> None:
    manifest = MagicMock(
        title="Demo",
        assets=MagicMock(
            sections=[
                MagicMock(
                    title="Intro",
                    id="sec_intro",
                    level=1,
                    start_line=0,
                    end_line=3,
                )
            ]
        ),
    )

    with patch(
        "src.presentation.resources.document_resources.document_service"
    ) as mock_service:
        mock_service.get_manifest = AsyncMock(return_value=manifest)
        from src.presentation.resources.document_resources import (
            resource_document_sections,
        )

        result = await resource_document_sections("doc_demo")

    assert "L1-3" in result
