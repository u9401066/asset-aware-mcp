from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_escape_table_cell_handles_crlf_and_cr() -> None:
    from src.presentation.markdown_utils import escape_table_cell

    assert escape_table_cell("a\r\nb\rc|d\\e") == "a b c\\|d\\\\e"


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


@pytest.mark.asyncio
async def test_resource_document_segmentation_large_file_returns_preview(
    tmp_path,
) -> None:
    """Huge segmentation resources should point to the artifact instead of inlining it."""
    doc_dir = tmp_path / "doc_big"
    doc_dir.mkdir()
    segmentation_path = doc_dir / "segmentation.json"
    segmentation_path.write_text(
        '{"doc_id":"doc_big","segments":['
        + ('{"text":"' + ("C" * 200) + '"},') * 500
        + "{}]}",
        encoding="utf-8",
    )

    with patch(
        "src.presentation.resources.document_resources.document_service"
    ) as mock_service:
        mock_service.repository.get_doc_dir.return_value = doc_dir
        from src.presentation.resources.document_resources import (
            resource_document_segmentation,
        )

        result = await resource_document_segmentation("doc_big")

    assert len(result) < 20_000
    assert "segmentation.json" in result
    assert "sha256:" in result
    assert "C" * 30_000 not in result


@pytest.mark.asyncio
async def test_resource_document_figures_escapes_pipe_cells() -> None:
    manifest = MagicMock(
        title="Demo",
        assets=MagicMock(
            figures=[
                MagicMock(
                    id="fig|1",
                    page=1,
                    width=640,
                    height=480,
                    caption="Alpha | Beta",
                )
            ]
        ),
    )

    with patch(
        "src.presentation.resources.document_resources.document_service"
    ) as mock_service:
        mock_service.get_manifest = AsyncMock(return_value=manifest)
        from src.presentation.resources.document_resources import (
            resource_document_figures,
        )

        result = await resource_document_figures("doc_demo")

    assert "`fig\\|1`" in result
    assert "Alpha \\| Beta" in result
    assert "640×480" in result


@pytest.mark.asyncio
async def test_resource_knowledge_graph_summary_times_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """KG resource requests should be bounded like KG tool calls."""
    from src.presentation.resources import document_resources

    async def slow_export_graph(**_kwargs):
        await asyncio.sleep(1)
        return {"format": "summary"}

    with patch.object(document_resources, "knowledge_graph") as mock_graph:
        mock_graph.export_graph = AsyncMock(side_effect=slow_export_graph)
        monkeypatch.setattr(
            document_resources,
            "KNOWLEDGE_RESOURCE_TIMEOUT_SECONDS",
            0.01,
            raising=False,
        )

        result = await document_resources.resource_knowledge_graph_summary()

    assert "timed out" in result
