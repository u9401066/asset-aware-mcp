"""
Unit Tests — Marker Block 轉換邏輯

測試 DocumentService 中的 Block → Asset 轉換方法。
不需要 Marker 模型，使用假資料測試轉換邏輯。

對應規格：docs/marker-etl-spec.md Section 2.2
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.document_service import DocumentService
from src.domain.entities import IngestResult
from src.infrastructure.marker_adapter import (
    MarkerBlock,
    MarkerParseResult,
    MarkerPDFExtractor,
)


@pytest.fixture
def mock_service(temp_dir: Path) -> DocumentService:
    """建立帶 mock 依賴的 DocumentService。"""
    mock_repo = MagicMock()
    mock_repo.get_doc_dir.return_value = temp_dir
    mock_repo.save_markdown.return_value = temp_dir / "full.md"
    mock_repo.save_image.return_value = temp_dir / "images" / "fig_1.png"

    mock_extractor = MagicMock()
    mock_extractor.get_page_count.return_value = 5

    service = DocumentService(
        repository=mock_repo,
        pdf_extractor=mock_extractor,
    )
    return service


class TestConvertBlocksToJson:
    """測試 _convert_blocks_to_json 方法。"""

    def test_basic_conversion(self, mock_service: DocumentService):
        """Block 正確轉為 JSON dict。"""
        blocks = [
            MarkerBlock(
                block_id="blk_0001",
                block_type="Text",
                page=1,
                text="Hello world",
                bbox=[10.0, 20.0, 500.0, 40.0],
                polygon=[[10.0, 20.0], [500.0, 20.0]],
                section_hierarchy={"1": "Intro"},
                metadata={"id": "m1", "level": None},
            ),
        ]
        result = mock_service._convert_blocks_to_json(blocks)

        assert len(result) == 1
        assert result[0]["block_id"] == "blk_0001"
        assert result[0]["block_type"] == "Text"
        assert result[0]["page"] == 1
        assert result[0]["text"] == "Hello world"
        assert result[0]["bbox"] == [10.0, 20.0, 500.0, 40.0]
        assert result[0]["section_hierarchy"] == {"1": "Intro"}

    def test_text_truncation(self, mock_service: DocumentService):
        """長文字被截斷至 500 字元。"""
        long_text = "A" * 1000
        blocks = [
            MarkerBlock(block_id="blk_0001", block_type="Text", page=1, text=long_text),
        ]
        result = mock_service._convert_blocks_to_json(blocks)

        assert len(result[0]["text"]) == 500

    def test_empty_text_handled(self, mock_service: DocumentService):
        """空文字正確處理。"""
        blocks = [
            MarkerBlock(block_id="blk_0001", block_type="Text", page=1, text=""),
        ]
        result = mock_service._convert_blocks_to_json(blocks)
        assert result[0]["text"] == ""

    def test_json_serializable(self, mock_service: DocumentService):
        """轉換結果可被 json.dumps 序列化。"""
        blocks = [
            MarkerBlock(
                block_id="blk_0001",
                block_type="SectionHeader",
                page=1,
                text="Title",
                bbox=[10.0, 20.0, 500.0, 40.0],
                section_hierarchy={"1": "Title"},
                metadata={"id": "m1"},
            ),
        ]
        result = mock_service._convert_blocks_to_json(blocks)

        # 不應拋出例外
        serialized = json.dumps(result, ensure_ascii=False)
        assert isinstance(serialized, str)

    def test_multiple_blocks(self, mock_service: DocumentService):
        """多個 blocks 全部轉換。"""
        blocks = [
            MarkerBlock(block_id=f"blk_{i:04d}", block_type="Text", page=i)
            for i in range(1, 6)
        ]
        result = mock_service._convert_blocks_to_json(blocks)
        assert len(result) == 5


class TestExtractTablesFromBlocks:
    """測試 _extract_tables_from_blocks 方法。"""

    def test_extract_single_table(self, mock_service: DocumentService):
        """QT-1: Table block 正確轉為 TableAsset。"""
        blocks = [
            MarkerBlock(
                block_id="blk_0001",
                block_type="Table",
                page=3,
                text="| A | B |\n|---|---|\n| 1 | 2 |",
            ),
        ]
        tables = mock_service._extract_tables_from_blocks(blocks)

        assert len(tables) == 1
        assert tables[0].id == "tab_1"
        assert tables[0].page == 3
        assert tables[0].source == "marker"
        assert "| A | B |" in tables[0].markdown

    def test_extract_multiple_tables(self, mock_service: DocumentService):
        """多個 Table block 都被提取。"""
        blocks = [
            MarkerBlock(
                block_id="blk_0001", block_type="Text", page=1, text="Some text"
            ),
            MarkerBlock(
                block_id="blk_0002",
                block_type="Table",
                page=2,
                text="| A |\n|---|\n| 1 |",
            ),
            MarkerBlock(
                block_id="blk_0003", block_type="Text", page=2, text="More text"
            ),
            MarkerBlock(
                block_id="blk_0004",
                block_type="Table",
                page=4,
                text="| B |\n|---|\n| 2 |",
            ),
        ]
        tables = mock_service._extract_tables_from_blocks(blocks)

        assert len(tables) == 2
        assert tables[0].id == "tab_1"
        assert tables[1].id == "tab_2"
        assert tables[0].page == 2
        assert tables[1].page == 4

    def test_no_tables(self, mock_service: DocumentService):
        """無 Table block 時回傳空列表。"""
        blocks = [
            MarkerBlock(
                block_id="blk_0001", block_type="Text", page=1, text="Just text"
            ),
        ]
        tables = mock_service._extract_tables_from_blocks(blocks)
        assert tables == []

    def test_table_preview_truncated(self, mock_service: DocumentService):
        """QT: preview 截斷至 100 字元。"""
        long_table = "| " + "A " * 200 + "|\n|---|\n| 1 |"
        blocks = [
            MarkerBlock(
                block_id="blk_0001", block_type="Table", page=1, text=long_table
            ),
        ]
        tables = mock_service._extract_tables_from_blocks(blocks)
        assert len(tables[0].preview) <= 100

    def test_table_row_col_parsed(self, mock_service: DocumentService):
        """QT-3: row_count 和 col_count 從 markdown 正確解析。"""
        table_md = "| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |"
        blocks = [
            MarkerBlock(block_id="blk_0001", block_type="Table", page=1, text=table_md),
        ]
        tables = mock_service._extract_tables_from_blocks(blocks)

        assert tables[0].row_count == 3  # header + 2 data rows
        assert tables[0].col_count == 3

    def test_table_row_col_empty_text(self, mock_service: DocumentService):
        """空表格文字 row_count/col_count 為 0。"""
        blocks = [
            MarkerBlock(block_id="blk_0001", block_type="Table", page=1, text=""),
        ]
        tables = mock_service._extract_tables_from_blocks(blocks)

        assert tables[0].row_count == 0
        assert tables[0].col_count == 0

    def test_table_single_column(self, mock_service: DocumentService):
        """單欄表格正確解析。"""
        table_md = "| Name |\n|------|\n| Alice |"
        blocks = [
            MarkerBlock(block_id="blk_0001", block_type="Table", page=1, text=table_md),
        ]
        tables = mock_service._extract_tables_from_blocks(blocks)

        assert tables[0].row_count == 2
        assert tables[0].col_count == 1


class TestExtractSectionsFromToc:
    """測試 _extract_sections_from_toc 方法。"""

    def test_basic_toc_conversion(self, mock_service: DocumentService):
        """QS: TOC 正確轉為 SectionAsset。"""
        toc = [
            {"title": "Abstract", "page": 1, "level": 1},
            {"title": "Introduction", "page": 1, "level": 1},
            {"title": "Background", "page": 2, "level": 2},
            {"title": "Methods", "page": 3, "level": 1},
        ]
        markdown = """# Abstract

Intro

# Introduction

Body

<!-- Page 2 -->

## Background

Details

<!-- Page 3 -->

# Methods

Procedure
"""
        sections = mock_service._extract_sections_from_toc(toc, markdown)

        assert len(sections) == 4
        assert sections[0].title == "Abstract"
        assert sections[0].level == 1
        assert sections[2].title == "Background"
        assert sections[2].level == 2
        assert sections[3].start_line > 0
        assert sections[3].end_line > sections[3].start_line

    def test_empty_toc(self, mock_service: DocumentService):
        """空 TOC 回傳空列表。"""
        sections = mock_service._extract_sections_from_toc([], "")
        assert sections == []

    def test_section_ids_sequential(self, mock_service: DocumentService):
        """Section IDs 按順序編號。"""
        toc = [
            {"title": "A", "page": 1, "level": 1},
            {"title": "B", "page": 2, "level": 1},
            {"title": "C", "page": 3, "level": 1},
        ]
        sections = mock_service._extract_sections_from_toc(
            toc, "# A\n\n<!-- Page 2 -->\n# B\n\n<!-- Page 3 -->\n# C\n"
        )
        assert sections[0].id == "sec_1"
        assert sections[1].id == "sec_2"
        assert sections[2].id == "sec_3"


class TestIngestResultBackend:
    """測試 IngestResult 的 backend 欄位。"""

    def test_default_backend_pymupdf(self):
        """預設 backend 為 pymupdf。"""
        result = IngestResult(doc_id="test", filename="test.pdf")
        assert result.backend == "pymupdf"

    def test_marker_backend(self):
        """Marker 解析結果標記 backend 為 marker。"""
        result = IngestResult(doc_id="test", filename="test.pdf", backend="marker")
        assert result.backend == "marker"


class TestParseTableDimensions:
    """測試 _parse_table_dimensions 靜態方法。"""

    def test_standard_table(self):
        """標準 3x3 表格。"""
        md = "| A | B | C |\n|---|---|---|\n| 1 | 2 | 3 |\n| 4 | 5 | 6 |"
        row, col = DocumentService._parse_table_dimensions(md)
        assert row == 3
        assert col == 3

    def test_empty_string(self):
        """空字串 → (0, 0)。"""
        row, col = DocumentService._parse_table_dimensions("")
        assert row == 0
        assert col == 0

    def test_single_cell(self):
        """單一儲存格。"""
        md = "| A |\n|---|\n| 1 |"
        row, col = DocumentService._parse_table_dimensions(md)
        assert row == 2
        assert col == 1

    def test_header_only(self):
        """只有 header 行。"""
        md = "| A | B |\n|---|---|"
        row, col = DocumentService._parse_table_dimensions(md)
        assert row == 1
        assert col == 2

    def test_no_separator(self):
        """無分隔線（仍可解析）。"""
        md = "| X | Y |\n| 1 | 2 |"
        row, col = DocumentService._parse_table_dimensions(md)
        assert row == 2
        assert col == 2


class TestGetImageDimensions:
    """測試 _get_image_dimensions 靜態方法。"""

    def test_valid_png(self):
        """有效 PNG 圖片可讀取尺寸。"""
        import io

        from PIL import Image

        img = Image.new("RGB", (200, 100))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        img_bytes = buf.getvalue()

        w, h = DocumentService._get_image_dimensions(img_bytes)
        assert w == 200
        assert h == 100

    def test_invalid_bytes(self):
        """無效圖片資料回傳 (0, 0)。"""
        w, h = DocumentService._get_image_dimensions(b"not an image")
        assert w == 0
        assert h == 0

    def test_empty_bytes(self):
        """空 bytes 回傳 (0, 0)。"""
        w, h = DocumentService._get_image_dimensions(b"")
        assert w == 0
        assert h == 0


class TestSaveMarkerImagesFigureMatching:
    """測試 _save_marker_images 的 Figure-Block 匹配修復。"""

    @pytest.fixture
    def service_with_mock(self, temp_dir: Path) -> DocumentService:
        """帶 mock repo 的 service。"""
        mock_repo = MagicMock()
        mock_repo.get_doc_dir.return_value = temp_dir

        # save_image 回傳不同路徑
        def fake_save_image(doc_id, image_id, data, ext):
            return temp_dir / "images" / f"{image_id}.{ext}"

        mock_repo.save_image.side_effect = fake_save_image

        mock_extractor = MagicMock()
        mock_extractor.profile = MagicMock(filters=MagicMock(min_figure_px=50))
        return DocumentService(
            repository=mock_repo,
            pdf_extractor=mock_extractor,
        )

    @pytest.mark.asyncio
    async def test_multiple_figures_matched_correctly(
        self, service_with_mock: DocumentService
    ):
        """每張圖片匹配到對應的 Figure block（不是全部匹配第一個）。"""
        import io

        from PIL import Image

        # 建立 3 張假圖片
        images = {}
        for i, key in enumerate(
            [
                "_page_1_Figure_2.png",
                "_page_4_Figure_3.png",
                "_page_7_Figure_4.png",
            ],
            1,
        ):
            img = Image.new("RGB", (100 + i * 50, 80 + i * 30))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            images[key] = buf.getvalue()

        parse_result = MagicMock()
        parse_result.images = images
        parse_result.blocks = [
            MarkerBlock(block_id="blk_0001", block_type="Text", page=1, text="intro"),
            MarkerBlock(
                block_id="blk_0002",
                block_type="Figure",
                page=2,
                text="",
                metadata={"id": "/page/1/Figure/2", "caption": "Fig 1"},
            ),
            MarkerBlock(
                block_id="blk_0003",
                block_type="Figure",
                page=5,
                text="",
                metadata={"id": "/page/4/Figure/3", "caption": "Fig 2"},
            ),
            MarkerBlock(
                block_id="blk_0004",
                block_type="Figure",
                page=8,
                text="",
                metadata={"id": "/page/7/Figure/4", "caption": "Fig 3"},
            ),
        ]

        figures = await service_with_mock._save_marker_images("test_doc", parse_result)

        assert len(figures) == 3
        # 每張圖片應匹配到不同的 Figure block
        assert figures[0].page == 2
        assert figures[0].caption == "Fig 1"
        assert figures[1].page == 5
        assert figures[1].caption == "Fig 2"
        assert figures[2].page == 8
        assert figures[2].caption == "Fig 3"

    @pytest.mark.asyncio
    async def test_image_dimensions_populated(self, service_with_mock: DocumentService):
        """圖片尺寸被正確讀取（不再是 0x0）。"""
        import io

        from PIL import Image

        img = Image.new("RGB", (320, 240))
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        parse_result = MagicMock()
        parse_result.images = {"_page_0_Figure_1.png": buf.getvalue()}
        parse_result.blocks = [
            MarkerBlock(
                block_id="blk_0001",
                block_type="Figure",
                page=1,
                text="",
                metadata={"id": "/page/0/Figure/1"},
            ),
        ]

        figures = await service_with_mock._save_marker_images("test_doc", parse_result)

        assert figures[0].width == 320
        assert figures[0].height == 240

    @pytest.mark.asyncio
    async def test_more_images_than_figure_blocks(
        self, service_with_mock: DocumentService
    ):
        """只儲存能精準對回 Figure block 的圖片。"""
        import io

        from PIL import Image

        images = {}
        for key in [
            "_page_2_Figure_1.png",
            "_page_99_Figure_1.png",
            "_page_100_Figure_2.png",
        ]:
            img = Image.new("RGB", (100, 100))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            images[key] = buf.getvalue()

        parse_result = MagicMock()
        parse_result.images = images
        parse_result.blocks = [
            MarkerBlock(
                block_id="blk_0001",
                block_type="Figure",
                page=3,
                text="",
                metadata={"id": "/page/2/Figure/1", "caption": "Only one"},
            ),
        ]

        figures = await service_with_mock._save_marker_images("test_doc", parse_result)

        assert len(figures) == 1
        assert figures[0].page == 3
        assert figures[0].caption == "Only one"


class TestMarkerChunking:
    """測試大型 PDF chunked Marker parsing。"""

    def test_parse_passes_extract_images_to_converter(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "chunked.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        extractor = MarkerPDFExtractor()
        captured: dict[str, object] = {}

        def fake_get_converter(*, extract_images: bool) -> object:
            captured["extract_images"] = extract_images
            return object()

        def fake_parse_single_pdf(
            _converter: object,
            _pdf_path: Path,
            *,
            page_offset: int = 0,
        ) -> MarkerParseResult:
            return MarkerParseResult(
                markdown="# Chunk",
                blocks=[
                    MarkerBlock(
                        block_id="blk_0001",
                        block_type="Text",
                        page=1 + page_offset,
                    )
                ],
                toc=[],
                images={},
                metadata={},
                page_count=1,
            )

        monkeypatch.setattr(extractor, "_get_converter", fake_get_converter)
        monkeypatch.setattr(extractor, "_parse_single_pdf", fake_parse_single_pdf)
        monkeypatch.setattr(
            extractor,
            "_resolve_parse_strategy",
            lambda _pdf_path, *, extract_images, max_pages_per_chunk: (
                1,
                extract_images,
                None,
                {},
            ),
        )

        result = extractor.parse(pdf_path, extract_images=False)

        assert captured["extract_images"] is False
        assert result.page_count == 1

    def test_parse_merges_chunked_results(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "large.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        extractor = MarkerPDFExtractor()
        converter = object()

        monkeypatch.setattr(
            extractor,
            "_get_converter",
            lambda *, extract_images: converter,
        )
        monkeypatch.setattr(
            extractor,
            "_resolve_parse_strategy",
            lambda _pdf_path, *, extract_images, max_pages_per_chunk: (
                4,
                extract_images,
                2,
                {},
            ),
        )
        monkeypatch.setattr(
            extractor,
            "_build_chunk_ranges",
            lambda _pdf_path, _max_pages: (4, [(1, 2), (3, 4)]),
        )
        monkeypatch.setattr(
            extractor,
            "_materialize_chunk_pdfs",
            lambda _pdf_path, _ranges, temp_dir: [
                (temp_dir / "chunk_1.pdf", 1),
                (temp_dir / "chunk_2.pdf", 3),
            ],
        )

        def fake_parse_single_pdf(
            _converter: object,
            _pdf_path: Path,
            *,
            page_offset: int = 0,
        ) -> MarkerParseResult:
            chunk_index = 1 if page_offset == 0 else 2
            return MarkerParseResult(
                markdown=f"# Chunk {chunk_index}",
                blocks=[
                    MarkerBlock(
                        block_id="blk_0001",
                        block_type="Text",
                        page=page_offset + 1,
                        text=f"Chunk {chunk_index}",
                        metadata={
                            "id": f"/page/{page_offset}/Text/1",
                            "source_order": 1,
                        },
                    )
                ],
                toc=[
                    {
                        "title": f"Section {chunk_index}",
                        "page": page_offset + 1,
                        "level": 1,
                    }
                ],
                images={f"_page_{page_offset}_Figure_1.png": b"img"},
                metadata={"title": "Large PDF"},
                page_count=2,
            )

        monkeypatch.setattr(extractor, "_parse_single_pdf", fake_parse_single_pdf)

        result = extractor.parse(pdf_path, max_pages_per_chunk=2)

        assert result.page_count == 4
        assert result.metadata["chunk_count"] == 2
        assert result.markdown == "# Chunk 1\n\n# Chunk 2"
        assert [block.block_id for block in result.blocks] == ["blk_0001", "blk_0002"]
        assert [block.metadata["source_order"] for block in result.blocks] == [1, 2]
        assert set(result.images) == {
            "_page_0_Figure_1.png",
            "_page_2_Figure_1.png",
        }

    def test_parse_auto_disables_images_for_image_heavy_pdf(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "images.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        extractor = MarkerPDFExtractor()
        captured: dict[str, object] = {}

        monkeypatch.setattr(extractor, "_count_pdf_pages", lambda _pdf_path: 10)
        monkeypatch.setattr(
            extractor,
            "_count_embedded_image_refs",
            lambda _pdf_path: 3001,
        )

        def fake_get_converter(*, extract_images: bool) -> object:
            captured["extract_images"] = extract_images
            return object()

        monkeypatch.setattr(extractor, "_get_converter", fake_get_converter)
        monkeypatch.setattr(
            extractor,
            "_parse_single_pdf",
            lambda _converter, _pdf_path, *, page_offset=0: MarkerParseResult(
                markdown="# Chunk",
                blocks=[],
                toc=[],
                images={},
                metadata={},
                page_count=10,
            ),
        )

        result = extractor.parse(pdf_path, extract_images=True)

        assert captured["extract_images"] is False
        assert result.metadata["auto_disable_figures_applied"] is True
        assert result.metadata["resolved_extract_images"] is False

    def test_parse_auto_chunks_large_pdf_by_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "huge.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        extractor = MarkerPDFExtractor()
        converter = object()
        observed_chunk_size: dict[str, int] = {}

        monkeypatch.setattr(extractor, "_count_pdf_pages", lambda _pdf_path: 1200)
        monkeypatch.setattr(
            extractor,
            "_count_embedded_image_refs",
            lambda _pdf_path: 0,
        )
        monkeypatch.setattr(
            extractor,
            "_get_converter",
            lambda *, extract_images: converter,
        )
        monkeypatch.setattr(
            extractor,
            "_build_chunk_ranges",
            lambda _pdf_path, max_pages: (
                observed_chunk_size.setdefault("value", max_pages),
                (1200, [(1, max_pages)]),
            )[1],
        )
        monkeypatch.setattr(
            extractor,
            "_parse_single_pdf",
            lambda _converter, _pdf_path, *, page_offset=0: MarkerParseResult(
                markdown="# Chunk",
                blocks=[],
                toc=[],
                images={},
                metadata={},
                page_count=1200,
            ),
        )

        result = extractor.parse(pdf_path)

        assert observed_chunk_size["value"] == 200
        assert result.metadata["auto_chunk_applied"] is True
        assert result.metadata["resolved_max_pages_per_chunk"] == 200

    def test_parse_remaps_subset_local_pages_back_to_original(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        pdf_path = tmp_path / "subset.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")

        extractor = MarkerPDFExtractor()
        monkeypatch.setattr(
            extractor,
            "_resolve_parse_strategy",
            lambda _pdf_path, *, extract_images, max_pages_per_chunk: (
                2,
                extract_images,
                None,
                {},
            ),
        )
        monkeypatch.setattr(
            extractor, "_get_converter", lambda *, extract_images: object()
        )
        monkeypatch.setattr(
            extractor,
            "_parse_single_pdf",
            lambda _converter, _pdf_path, *, page_offset=0: MarkerParseResult(
                markdown="# Section",
                blocks=[
                    MarkerBlock(
                        block_id="blk_0001",
                        block_type="Figure",
                        page=1,
                        metadata={"id": "/page/0/Figure/1"},
                    )
                ],
                toc=[{"title": "Section", "page": 2, "level": 1}],
                images={"_page_0_Figure_1.png": b"img"},
                metadata={},
                page_count=2,
            ),
        )

        result = extractor.parse(
            pdf_path,
            page_map=[10, 12],
            reported_page_count=300,
        )

        assert result.page_count == 300
        assert result.blocks[0].page == 10
        assert result.toc[0]["page"] == 12
        assert set(result.images) == {"_page_9_Figure_1.png"}
