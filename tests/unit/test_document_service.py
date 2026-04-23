"""Unit tests for DocumentService CRUD and PDF→DOCX conversion helpers."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.document_service import (
    DocumentService,
    build_doc_id_unique_suffix,
    format_page_ranges,
    normalize_page_ranges,
    remap_markdown_page_markers,
)
from src.domain.etl_profile import ETLProfile
from src.infrastructure.marker_adapter import MarkerBlock


def test_normalize_page_ranges_merges_adjacent_ranges() -> None:
    assert normalize_page_ranges(["1-3", "4", "8-9", "9-10"], 12) == (
        (1, 4),
        (8, 10),
    )


def test_normalize_page_ranges_rejects_out_of_bounds_pages() -> None:
    with pytest.raises(ValueError, match="exceeds total page count"):
        normalize_page_ranges(["3-12"], 10)


def test_remap_markdown_page_markers_rewrites_subset_numbers() -> None:
    markdown = "<!-- Page 1 -->\nA\n<!-- Page 2 -->\nB"
    remapped = remap_markdown_page_markers(markdown, [10, 12])
    assert remapped == "<!-- Page 10 -->\nA\n<!-- Page 12 -->\nB"


def test_build_doc_id_unique_suffix_includes_page_ranges() -> None:
    suffix = build_doc_id_unique_suffix(Path("paper.pdf"), ((3, 5), (9, 9)))
    assert suffix.endswith("#pages=3-5,9")
    assert format_page_ranges(((3, 5), (9, 9))) == "3-5,9"


@pytest.mark.asyncio
async def test_delete_document_success() -> None:
    repository = MagicMock()
    repository.load_manifest.return_value = MagicMock(filename="paper.pdf")
    repository.delete_document.return_value = True

    service = DocumentService(repository=repository, pdf_extractor=MagicMock())

    result = await service.delete_document("doc_123")

    assert result == {
        "success": True,
        "doc_id": "doc_123",
        "filename": "paper.pdf",
        "warnings": [],
    }


@pytest.mark.asyncio
async def test_delete_document_removes_kg_entries() -> None:
    repository = MagicMock()
    repository.load_manifest.return_value = MagicMock(filename="paper.pdf")
    repository.delete_document.return_value = True
    knowledge_graph = MagicMock()
    knowledge_graph.is_available = True
    knowledge_graph.delete_document = AsyncMock(
        return_value={"status": "success", "message": "deleted"}
    )

    service = DocumentService(
        repository=repository,
        pdf_extractor=MagicMock(),
        knowledge_graph=knowledge_graph,
    )

    result = await service.delete_document("doc_123")

    assert result["success"] is True
    assert result["warnings"] == []
    assert result["knowledge_graph_status"] == "success"
    knowledge_graph.delete_document.assert_awaited_once_with("doc_123")


@pytest.mark.asyncio
async def test_delete_document_warns_when_kg_delete_fails() -> None:
    repository = MagicMock()
    repository.load_manifest.return_value = MagicMock(filename="paper.pdf")
    repository.delete_document.return_value = True
    knowledge_graph = MagicMock()
    knowledge_graph.is_available = True
    knowledge_graph.delete_document = AsyncMock(side_effect=RuntimeError("boom"))

    service = DocumentService(
        repository=repository,
        pdf_extractor=MagicMock(),
        knowledge_graph=knowledge_graph,
    )

    result = await service.delete_document("doc_123")

    assert result["success"] is True
    assert result["warnings"]
    assert "Knowledge graph deletion failed" in result["warnings"][0]


@pytest.mark.asyncio
async def test_convert_pdf_to_docx_rejects_fidelity_mode() -> None:
    service = DocumentService(repository=MagicMock(), pdf_extractor=MagicMock())

    result = await service.convert_pdf_to_docx("doc_123", mode="fidelity")

    assert result["success"] is False
    assert "content mode only" in result["error"]


@pytest.mark.asyncio
async def test_convert_pdf_to_docx_success(monkeypatch, tmp_path: Path) -> None:
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path
    repository.load_markdown.return_value = "# Title\n\nHello world"
    repository.load_manifest.return_value = MagicMock(
        title="Paper Title",
        assets=MagicMock(figures=[], tables=[MagicMock()]),
    )

    service = DocumentService(repository=repository, pdf_extractor=MagicMock())

    captured: dict[str, object] = {}

    def fake_build(markdown, manifest, output_path):
        captured["markdown"] = markdown
        captured["output_path"] = output_path

    monkeypatch.setattr(service, "_build_docx_from_markdown", fake_build)

    result = await service.convert_pdf_to_docx("doc_123")

    assert result == {
        "success": True,
        "doc_id": "doc_123",
        "output_path": str(tmp_path / "converted_from_pdf.docx"),
        "mode": "content",
        "figures_embedded": 0,
        "tables_found": 1,
    }
    assert captured["markdown"] == "# Title\n\nHello world"
    assert captured["output_path"] == tmp_path / "converted_from_pdf.docx"


@pytest.mark.asyncio
async def test_convert_pdf_to_pptx_rejects_fidelity_mode() -> None:
    service = DocumentService(repository=MagicMock(), pdf_extractor=MagicMock())

    result = await service.convert_pdf_to_pptx("doc_123", mode="fidelity")

    assert result["success"] is False
    assert "content mode only" in result["error"]


@pytest.mark.asyncio
async def test_convert_pdf_to_pptx_success(monkeypatch, tmp_path: Path) -> None:
    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path
    repository.load_markdown.return_value = "# Slide 1\n\n- bullet"
    repository.load_manifest.return_value = MagicMock(
        title="Deck Title",
        filename="slides.pdf",
        assets=MagicMock(
            figures=[MagicMock(path=tmp_path / "fig1.png", caption="Cap")]
        ),
    )

    service = DocumentService(repository=repository, pdf_extractor=MagicMock())

    captured: dict[str, object] = {}

    def fake_build(markdown, manifest, output_path):
        captured["markdown"] = markdown
        captured["output_path"] = output_path
        return {"total_slides": 3, "figure_slides": 1}

    monkeypatch.setattr(service, "_build_pptx_from_markdown", fake_build)

    result = await service.convert_pdf_to_pptx("doc_123")

    assert result == {
        "success": True,
        "doc_id": "doc_123",
        "output_path": str(tmp_path / "converted_from_pdf.pptx"),
        "mode": "content",
        "slides_created": 3,
        "figure_slides": 1,
    }
    assert captured["markdown"] == "# Slide 1\n\n- bullet"
    assert captured["output_path"] == tmp_path / "converted_from_pdf.pptx"


@pytest.mark.asyncio
async def test_ingest_reports_progress_callback(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    repository = MagicMock()
    repository.get_doc_dir.return_value = tmp_path / "doc_test"
    repository.save_markdown.return_value = tmp_path / "content.md"
    repository.save_manifest.return_value = None

    extractor = MagicMock()
    extractor.extract_text.return_value = "# Title\n\nHello"
    extractor.get_page_count.return_value = 1
    extractor.get_toc.return_value = []
    extractor.get_title.return_value = "Paper"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[])
    service._extract_tables = AsyncMock(return_value=[])

    progress_events: list[tuple[int, int, str, str]] = []

    async def progress_callback(
        step: int, total: int, phase: str, message: str
    ) -> None:
        progress_events.append((step, total, phase, message))

    results = await service.ingest([str(pdf_path)], progress_callback=progress_callback)

    assert len(results) == 1
    assert results[0].success is True
    assert progress_events
    assert progress_events[-1][0] == progress_events[-1][1]
    assert progress_events[-1][2] == "Completed"


@pytest.mark.asyncio
async def test_save_marker_images_falls_back_to_bbox_render(
    monkeypatch, tmp_path: Path
) -> None:
    repository = MagicMock()
    repository.save_image.return_value = tmp_path / "fig_7_1.png"
    service = DocumentService(
        repository=repository,
        pdf_extractor=MagicMock(),
        profile=ETLProfile.default(),
    )

    block = MarkerBlock(
        block_id="blk_0001",
        block_type="Figure",
        page=7,
        text="",
        bbox=[10.0, 20.0, 110.0, 180.0],
        metadata={"id": "/page/6/Figure/0", "caption": "Figure 49.5", "source_order": 1},
    )
    parse_result = SimpleNamespace(
        blocks=[block],
        images={},
    )

    def fake_render(*args, **kwargs):
        return (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR"
            b"\x00\x00\x00d\x00\x00\x00x\x08\x02\x00\x00\x00"
            b"\x00\x00\x00\x00"
        )

    monkeypatch.setattr(service, "_render_pdf_block_image", fake_render)
    monkeypatch.setattr(service, "_get_image_dimensions", lambda _: (100, 120))

    figures = await service._save_marker_images(
        "doc_test",
        parse_result,
        pdf_path=tmp_path / "source.pdf",
    )

    assert len(figures) == 1
    assert figures[0].id == "fig_7_1"
    assert figures[0].page == 7
    assert figures[0].caption == "Figure 49.5"
    repository.save_image.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_scopes_doc_id_and_page_markers_for_page_ranges(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 original")
    doc_dir = tmp_path / "doc_pages"
    doc_dir.mkdir()

    repository = MagicMock()
    repository.get_doc_dir.return_value = doc_dir
    repository.save_markdown.return_value = tmp_path / "content.md"
    repository.save_manifest.return_value = None

    extractor = MagicMock()

    def fake_get_page_count(path: Path) -> int:
        return 10 if path == pdf_path else 2

    extractor.get_page_count.side_effect = fake_get_page_count
    extractor.extract_text.return_value = (
        "<!-- Page 1 -->\nAlpha\n<!-- Page 2 -->\nBeta"
    )
    extractor.get_toc.return_value = [(1, "Methods", 2)]
    extractor.get_title.return_value = "Paper"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[])
    service._extract_tables = AsyncMock(return_value=[])

    captured_suffix: dict[str, str] = {}

    def fake_generate(_filename: str, unique_suffix: str):
        captured_suffix["value"] = unique_suffix
        return MagicMock(value="doc_pages")

    monkeypatch.setattr(
        "src.application.document_service.DocId.generate", fake_generate
    )
    monkeypatch.setattr(
        "src.application.document_service.materialize_pdf_page_subset",
        lambda _source_path, output_path, _page_ranges: (
            output_path.write_bytes(b"%PDF-1.4 subset"),
            output_path,
        )[1],
    )

    results = await service.ingest([str(pdf_path)], page_ranges=["3-4"])

    assert results[0].success is True
    assert results[0].pages_processed == 2
    assert captured_suffix["value"].endswith("#pages=3-4")
    repository.save_markdown.assert_called_once_with(
        "doc_pages",
        "<!-- Page 3 -->\nAlpha\n<!-- Page 4 -->\nBeta",
    )
    manifest = repository.save_manifest.call_args.args[0]
    assert manifest.page_count == 10


@pytest.mark.asyncio
async def test_ingest_remaps_table_and_image_pages_for_page_ranges(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 original")
    doc_dir = tmp_path / "doc_pages"
    doc_dir.mkdir()

    repository = MagicMock()
    repository.get_doc_dir.return_value = doc_dir
    repository.save_markdown.return_value = tmp_path / "content.md"
    repository.save_manifest.return_value = None

    extractor = MagicMock()
    extractor.get_page_count.side_effect = lambda path: 10 if path == pdf_path else 2
    extractor.extract_text.return_value = "<!-- Page 1 -->\n# Title"
    extractor.get_toc.return_value = []
    extractor.get_title.return_value = "Paper"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[MagicMock(page=3)])
    service._extract_tables = AsyncMock(return_value=[MagicMock(page=4)])

    monkeypatch.setattr(
        "src.application.document_service.DocId.generate",
        lambda *_args: MagicMock(value="doc_pages"),
    )
    monkeypatch.setattr(
        "src.application.document_service.materialize_pdf_page_subset",
        lambda _source_path, output_path, _page_ranges: (
            output_path.write_bytes(b"%PDF-1.4 subset"),
            output_path,
        )[1],
    )

    await service.ingest([str(pdf_path)], page_ranges=["3-4"])

    service._extract_and_save_images.assert_awaited_once()
    assert service._extract_and_save_images.await_args.kwargs["page_map"] == [3, 4]
    service._extract_tables.assert_awaited_once()
    assert service._extract_tables.await_args.kwargs["page_map"] == [3, 4]


@pytest.mark.asyncio
async def test_ingest_ocr_runs_on_page_range_subset(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 original")
    doc_dir = tmp_path / "doc_pages"
    doc_dir.mkdir()

    repository = MagicMock()
    repository.get_doc_dir.return_value = doc_dir
    repository.save_markdown.return_value = tmp_path / "content.md"
    repository.save_manifest.return_value = None

    extractor = MagicMock()
    extractor.get_page_count.side_effect = lambda path: 10 if path == pdf_path else 2
    extractor.extract_text.return_value = "<!-- Page 1 -->\n# Title"
    extractor.get_toc.return_value = []
    extractor.get_title.return_value = "Paper"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[])
    service._extract_tables = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "src.application.document_service.DocId.generate",
        lambda *_args: MagicMock(value="doc_pages"),
    )
    monkeypatch.setattr(
        "src.application.document_service.materialize_pdf_page_subset",
        lambda _source_path, output_path, _page_ranges: (
            output_path.write_bytes(b"%PDF-1.4 subset"),
            output_path,
        )[1],
    )

    captured: dict[str, Path] = {}

    def fake_ocr(_doc_id: str, source_path: Path, **_kwargs) -> Path:
        captured["source_path"] = source_path
        ocr_path = doc_dir / "ocr_processed.pdf"
        ocr_path.write_bytes(b"%PDF-1.4 ocr")
        return ocr_path

    monkeypatch.setattr(service, "_preprocess_pdf_with_ocr", fake_ocr)

    await service.ingest([str(pdf_path)], ocr_enabled=True, page_ranges=["3-4"])

    assert captured["source_path"] == doc_dir / "selected_pages.pdf"
    extractor.extract_text.assert_called_once_with(doc_dir / "ocr_processed.pdf")


@pytest.mark.asyncio
async def test_ingest_overwrites_stale_original_pdf_copy(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 fresh")
    doc_dir = tmp_path / "doc_fixed"
    doc_dir.mkdir()
    (doc_dir / "original.pdf").write_bytes(b"%PDF-1.4 stale")

    repository = MagicMock()
    repository.get_doc_dir.return_value = doc_dir
    repository.save_markdown.return_value = tmp_path / "content.md"
    repository.save_manifest.return_value = None

    extractor = MagicMock()
    extractor.extract_text.return_value = "# Title\n\nHello"
    extractor.get_page_count.return_value = 1
    extractor.get_toc.return_value = []
    extractor.get_title.return_value = "Paper"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[])
    service._extract_tables = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "src.application.document_service.DocId.generate",
        lambda *_args: MagicMock(value="doc_fixed"),
    )

    results = await service.ingest([str(pdf_path)])

    assert results[0].success is True
    assert (doc_dir / "original.pdf").read_bytes() == b"%PDF-1.4 fresh"


@pytest.mark.asyncio
async def test_pymupdf_ingest_persists_searchable_blocks_json(
    monkeypatch, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "chapter.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 original")
    doc_dir = tmp_path / "doc_blocks"
    doc_dir.mkdir()

    repository = MagicMock()
    repository.get_doc_dir.return_value = doc_dir
    repository.save_markdown.return_value = doc_dir / "content.md"
    repository.save_manifest.return_value = None
    repository.save_blocks.side_effect = lambda _doc_id, blocks: (
        (doc_dir / "blocks.json").write_text(
            json.dumps(blocks, ensure_ascii=False), encoding="utf-8"
        ),
        doc_dir / "blocks.json",
    )[1]
    repository.save_citation_index.return_value = doc_dir / "citation_index.jsonl"

    extractor = MagicMock()
    extractor.extract_text.return_value = (
        "<!-- Page 1 -->\n# Airway Management\n\nDifficult mask ventilation predicts "
        "difficult intubation.\n\n<!-- Page 2 -->\n## Rescue Strategy\n\nUse oxygenation first."
    )
    extractor.get_page_count.return_value = 2
    extractor.get_toc.return_value = []
    extractor.get_title.return_value = "Airway Management"

    service = DocumentService(repository=repository, pdf_extractor=extractor)
    service._extract_and_save_images = AsyncMock(return_value=[])
    service._extract_tables = AsyncMock(return_value=[])

    monkeypatch.setattr(
        "src.application.document_service.DocId.generate",
        lambda *_args: MagicMock(value="doc_blocks"),
    )

    results = await service.ingest([str(pdf_path)])

    assert results[0].success is True
    blocks_path = doc_dir / "blocks.json"
    assert blocks_path.exists()

    blocks = json.loads(blocks_path.read_text(encoding="utf-8"))
    assert any(block["block_type"] == "SectionHeader" for block in blocks)
    text_blocks = [block for block in blocks if block["block_type"] == "Text"]
    assert text_blocks
    assert any(
        "difficult mask ventilation predicts difficult intubation"
        in block["text"].lower()
        for block in text_blocks
    )
    assert all(
        isinstance((block.get("metadata") or {}).get("line_start"), int)
        and isinstance((block.get("metadata") or {}).get("line_end"), int)
        for block in blocks
    )
