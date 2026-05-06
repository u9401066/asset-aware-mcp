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


@pytest.mark.asyncio
async def test_resource_document_segmentation_reads_existing_json_without_export(
    tmp_path,
) -> None:
    doc_dir = tmp_path / "doc_demo"
    doc_dir.mkdir()
    segmentation_path = doc_dir / "segmentation.json"
    segmentation_path.write_text(
        '{"doc_id":"doc_demo","segments":[]}', encoding="utf-8"
    )

    with (
        patch(
            "src.presentation.resources.document_resources.document_service"
        ) as mock_service,
        patch(
            "src.presentation.tools.document_tools.export_document_segmentation",
            new_callable=AsyncMock,
        ) as mock_export,
    ):
        mock_service.repository.get_doc_dir.return_value = doc_dir
        from src.presentation.resources.document_resources import (
            resource_document_segmentation,
        )

        result = await resource_document_segmentation("doc_demo")

    assert result == '{"doc_id":"doc_demo","segments":[]}'
    mock_export.assert_not_called()
