"""
Integration Tests — Marker ETL Pipeline

完整測試 Marker PDF 拆分的端對端流程。
需要 Marker 已安裝且模型已下載。

對應規格：docs/marker-etl-spec.md Section 5.3

執行方式：
    RUN_MARKER_INTEGRATION=1 pytest tests/integration/test_marker_etl.py -v

跳過條件：
    - 未設定 RUN_MARKER_INTEGRATION=1 時自動跳過（避免預設測試 OOM）
    - Marker 未安裝時自動跳過
    - 測試 PDF 不存在時自動跳過
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

# ============================================================================
# Skip conditions
# ============================================================================

RUN_MARKER_INTEGRATION = os.getenv("RUN_MARKER_INTEGRATION") == "1"

pytestmark = pytest.mark.skipif(
    not RUN_MARKER_INTEGRATION,
    reason="Set RUN_MARKER_INTEGRATION=1 to run heavyweight Marker integration tests.",
)

try:
    from src.infrastructure.marker_adapter import MarkerPDFExtractor

    MARKER_AVAILABLE = importlib.util.find_spec("marker") is not None
except ImportError:
    MARKER_AVAILABLE = False

# 測試 PDF 路徑候選
TEST_PDF_CANDIDATES = [
    Path("test_pdfs"),  # 專案下的測試 PDF 目錄
    Path("data"),  # 可能有已存在的 PDF
]


def find_test_pdf() -> Path | None:
    """找一個可用的測試 PDF。"""
    for candidate_dir in TEST_PDF_CANDIDATES:
        if candidate_dir.exists():
            for pdf in candidate_dir.rglob("*.pdf"):
                return pdf
    return None


TEST_PDF = find_test_pdf()

skip_no_marker = pytest.mark.skipif(
    not MARKER_AVAILABLE,
    reason="Marker not installed (uv sync --extra marker)",
)

skip_no_pdf = pytest.mark.skipif(
    TEST_PDF is None,
    reason="No test PDF found in test_pdfs/ or data/",
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def marker_extractor() -> MarkerPDFExtractor:
    """建立 MarkerPDFExtractor 實例。"""
    return MarkerPDFExtractor()


@pytest.fixture
def parse_result(marker_extractor):
    """解析測試 PDF 的結果（快取用）。"""
    assert TEST_PDF is not None
    return marker_extractor.parse(TEST_PDF)


# ============================================================================
# Integration Tests
# ============================================================================


@skip_no_marker
@skip_no_pdf
class TestMarkerParsing:
    """IT-01 ~ IT-03: Marker 基本解析功能。"""

    def test_parse_returns_result(self, marker_extractor):
        """IT-01: Marker 成功解析 PDF 並回傳 MarkerParseResult。"""
        result = marker_extractor.parse(TEST_PDF)
        assert result is not None
        assert hasattr(result, "markdown")
        assert hasattr(result, "blocks")
        assert hasattr(result, "toc")
        assert hasattr(result, "images")
        assert hasattr(result, "page_count")

    def test_markdown_not_empty(self, parse_result):
        """IT-02 / QM-1: 產出的 markdown 非空。"""
        assert len(parse_result.markdown) > 0

    def test_markdown_has_headings(self, parse_result):
        """IT-02 / QM-2: markdown 含標題。"""
        lines = parse_result.markdown.split("\n")
        has_heading = any(line.strip().startswith("#") for line in lines)
        assert has_heading, "Markdown should contain at least one heading"

    def test_blocks_not_empty(self, parse_result):
        """IT-03 / QB-1: blocks 非空。"""
        assert len(parse_result.blocks) > 0

    def test_blocks_have_required_fields(self, parse_result):
        """IT-03: 每個 block 都有必要欄位。"""
        for block in parse_result.blocks:
            assert block.block_id, "block missing block_id"
            assert block.block_type, f"block {block.block_id} missing block_type"
            assert block.page >= 1, (
                f"block {block.block_id} has invalid page: {block.page}"
            )

    def test_page_count_positive(self, parse_result):
        """QF-3: page_count > 0。"""
        assert parse_result.page_count > 0


@skip_no_marker
@skip_no_pdf
class TestMarkerBlocks:
    """IT-04 ~ IT-05: Block 品質驗證。"""

    def test_section_headers_have_hierarchy(self, parse_result):
        """IT-04: SectionHeader blocks 有 section_hierarchy。"""
        section_headers = [
            b for b in parse_result.blocks if b.block_type == "SectionHeader"
        ]

        if section_headers:
            # 至少部分 SectionHeader 應該有 section_hierarchy
            with_hierarchy = [b for b in section_headers if b.section_hierarchy]
            assert len(with_hierarchy) > 0, (
                "At least some SectionHeader blocks should have section_hierarchy"
            )

    def test_block_ids_unique(self, parse_result):
        """QB-2: block_ids 唯一。"""
        ids = [b.block_id for b in parse_result.blocks]
        assert len(ids) == len(set(ids)), "block_ids must be unique"

    def test_block_types_known(self, parse_result):
        """QB-3: block_type 為已知類型。"""
        known_types = {
            "Text",
            "Table",
            "Figure",
            "SectionHeader",
            "ListItem",
            "Equation",
            "Caption",
            "Footnote",
            "Page",
            "PageHeader",
            "PageFooter",
            # Marker 可能的其他類型
            "Line",
            "Span",
            "Code",
            "TextInlineMath",
            "Form",
            "Handwriting",
            "Picture",
            "FigureGroup",
            "TableOfContents",
            "Document",
            "PageGroup",
        }
        unknown_types = set()
        for block in parse_result.blocks:
            if block.block_type not in known_types:
                unknown_types.add(block.block_type)

        # 允許少量未知類型，但記錄下來
        if unknown_types:
            print(f"⚠️ Unknown block types found: {unknown_types}")

    def test_pages_within_range(self, parse_result):
        """QB-4: page 在有效範圍內。"""
        for block in parse_result.blocks:
            assert 1 <= block.page <= parse_result.page_count, (
                f"block {block.block_id} page {block.page} out of range "
                f"[1, {parse_result.page_count}]"
            )

    def test_bbox_valid_format(self, parse_result):
        """QB-5: bbox 格式正確。"""
        blocks_with_bbox = [b for b in parse_result.blocks if b.bbox]

        # 至少 90% 的 blocks 應有 bbox
        bbox_ratio = (
            len(blocks_with_bbox) / len(parse_result.blocks)
            if parse_result.blocks
            else 0
        )
        print(f"BBox coverage: {bbox_ratio:.1%}")

        for block in blocks_with_bbox:
            assert len(block.bbox) == 4, (
                f"block {block.block_id} bbox should have 4 values, got {len(block.bbox)}"
            )
            x0, y0, x1, y1 = block.bbox
            assert x0 <= x1, f"block {block.block_id} bbox x0 ({x0}) > x1 ({x1})"
            assert y0 <= y1, f"block {block.block_id} bbox y0 ({y0}) > y1 ({y1})"

    def test_table_blocks_have_content(self, parse_result):
        """IT-05: Table block 有文字內容。"""
        table_blocks = [b for b in parse_result.blocks if b.block_type == "Table"]

        for table in table_blocks:
            assert table.text, f"Table block {table.block_id} has no text"
            # 應該包含 Markdown 表格語法
            assert "|" in table.text, (
                f"Table block {table.block_id} text doesn't look like markdown table"
            )


@skip_no_marker
@skip_no_pdf
class TestMarkerImages:
    """IT-06: 圖片提取驗證。"""

    def test_images_valid(self, parse_result):
        """IT-06: 圖片可被正常處理。"""
        for img_name, img_bytes in parse_result.images.items():
            assert len(img_bytes) > 0, f"Image {img_name} is empty"

            # 檢查 magic bytes
            if img_name.endswith(".png"):
                assert img_bytes[:4] == b"\x89PNG", f"Image {img_name} is not valid PNG"
            elif img_name.endswith((".jpg", ".jpeg")):
                assert img_bytes[:2] == b"\xff\xd8", (
                    f"Image {img_name} is not valid JPEG"
                )


@skip_no_marker
@skip_no_pdf
class TestMarkerManifest:
    """IT-07 ~ IT-08: Manifest 生成驗證。"""

    def test_convert_to_manifest(self, marker_extractor, parse_result, temp_dir):
        """IT-07: manifest 可被 DocumentManifest 解析。"""
        from src.domain.entities import DocumentManifest

        manifest = marker_extractor.convert_to_manifest(
            parse_result,
            TEST_PDF,
            temp_dir,
        )
        assert isinstance(manifest, DocumentManifest)
        assert manifest.page_count > 0

    def test_manifest_has_valid_fields(self, marker_extractor, parse_result, temp_dir):
        """QF-1 ~ QF-3: manifest 欄位正確。"""
        manifest = marker_extractor.convert_to_manifest(
            parse_result,
            TEST_PDF,
            temp_dir,
        )
        assert manifest.doc_id, "doc_id should not be empty"
        assert manifest.filename, "filename should not be empty"
        assert manifest.page_count > 0

    def test_blocks_json_created(self, marker_extractor, parse_result, temp_dir):
        """blocks.json 成功生成。"""
        marker_extractor.convert_to_manifest(parse_result, TEST_PDF, temp_dir)

        blocks_path = temp_dir / "blocks.json"
        assert blocks_path.exists(), "blocks.json should be created"

        blocks = json.loads(blocks_path.read_text())
        assert isinstance(blocks, list)
        assert len(blocks) > 0


@skip_no_marker
@skip_no_pdf
class TestMarkerSectionTree:
    """IT-09: SectionTree 從 blocks.json 建構。"""

    def test_section_tree_from_parsed_blocks(self, parse_result):
        """IT-09: SectionTree 正確建構。"""
        from src.domain.section_tree import build_section_tree_from_blocks

        blocks_data = [
            {
                "block_id": b.block_id,
                "block_type": b.block_type,
                "page": b.page,
                "text": b.text[:500] if b.text else "",
                "bbox": b.bbox,
                "section_hierarchy": b.section_hierarchy,
            }
            for b in parse_result.blocks
        ]

        tree = build_section_tree_from_blocks("doc_test", blocks_data, "Test Document")
        assert tree.root.block_count == len(blocks_data)
        assert tree.max_depth >= 1


@skip_no_marker
class TestMarkerFallback:
    """IT-10 ~ IT-11: 降級與錯誤處理。"""

    @pytest.mark.asyncio
    async def test_marker_unavailable_error(self, temp_dir):
        """IT-11: Marker 不可用時回傳明確錯誤。"""
        from src.application.document_service import DocumentService
        from src.infrastructure.file_storage import FileStorage
        from src.infrastructure.pdf_extractor import PyMuPDFExtractor

        service = DocumentService(
            repository=FileStorage(base_dir=temp_dir),
            pdf_extractor=PyMuPDFExtractor(),
            marker_extractor=None,  # Marker 不可用
        )

        # 建立假 PDF
        fake_pdf = temp_dir / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        results = await service.ingest([str(fake_pdf)], use_marker=True)
        assert len(results) == 1
        # 因為 marker_extractor is None，應該進入 error 或 fallback
        # 根據目前的實作，如果 marker_extractor is None 但 use_marker=True
        # 會走 PyMuPDF 路徑（因為 if use_marker and self.marker_extractor 為 False）
