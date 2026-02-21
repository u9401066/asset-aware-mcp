"""
Unit Tests — Marker Block 資料模型

測試 MarkerBlock, MarkerParseResult 的建立與驗證。
不需要 Marker 模型，純 Python 資料結構測試。

對應規格：docs/marker-etl-spec.md Section 2.3
"""

from __future__ import annotations

from src.infrastructure.marker_adapter import MarkerBlock, MarkerParseResult


class TestMarkerBlock:
    """MarkerBlock 資料模型測試。"""

    def test_create_with_defaults(self):
        """QB: MarkerBlock 建立時預設值正確。"""
        block = MarkerBlock(
            block_id="blk_0001",
            block_type="Text",
            page=1,
        )
        assert block.block_id == "blk_0001"
        assert block.block_type == "Text"
        assert block.page == 1
        assert block.text == ""
        assert block.bbox == []
        assert block.polygon == []
        assert block.section_hierarchy == {}
        assert block.children == []
        assert block.metadata == {}

    def test_create_with_all_fields(self):
        """QB: MarkerBlock 所有欄位正確填入。"""
        block = MarkerBlock(
            block_id="blk_0042",
            block_type="SectionHeader",
            page=3,
            text="Introduction",
            bbox=[72.0, 100.0, 540.0, 120.0],
            polygon=[[72.0, 100.0], [540.0, 100.0], [540.0, 120.0], [72.0, 120.0]],
            section_hierarchy={"1": "Chapter 1", "2": "Introduction"},
            metadata={"id": "marker_123", "level": 2},
        )
        assert block.block_type == "SectionHeader"
        assert block.text == "Introduction"
        assert len(block.bbox) == 4
        assert block.bbox[0] < block.bbox[2]  # x0 < x1
        assert block.bbox[1] < block.bbox[3]  # y0 < y1
        assert block.section_hierarchy["2"] == "Introduction"
        assert block.metadata["level"] == 2

    def test_bbox_format_valid(self):
        """QB-5: bbox 格式 [x0, y0, x1, y1] where x0 < x1, y0 < y1。"""
        block = MarkerBlock(
            block_id="blk_0001",
            block_type="Text",
            page=1,
            bbox=[10.0, 20.0, 500.0, 40.0],
        )
        x0, y0, x1, y1 = block.bbox
        assert x0 < x1, f"bbox x0 ({x0}) should be < x1 ({x1})"
        assert y0 < y1, f"bbox y0 ({y0}) should be < y1 ({y1})"

    def test_section_hierarchy_keys_are_numeric_strings(self):
        """QB-6: section_hierarchy key 為數字字串。"""
        hierarchy = {"1": "Chapter", "2": "Section", "3": "Subsection"}
        block = MarkerBlock(
            block_id="blk_0001",
            block_type="Text",
            page=1,
            section_hierarchy=hierarchy,
        )
        for key in block.section_hierarchy:
            assert key.isdigit(), (
                f"section_hierarchy key '{key}' should be numeric string"
            )

    def test_section_hierarchy_no_shared_mutation(self):
        """不同 block 的 section_hierarchy 不應共享參考。"""
        block1 = MarkerBlock(block_id="blk_0001", block_type="Text", page=1)
        block2 = MarkerBlock(block_id="blk_0002", block_type="Text", page=1)

        block1.section_hierarchy["1"] = "Chapter 1"
        assert "1" not in block2.section_hierarchy

    def test_block_types_known(self):
        """QB-3: block_type 應為已知類型。"""
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
        }
        for bt in known_types:
            block = MarkerBlock(block_id="blk_0001", block_type=bt, page=1)
            assert block.block_type == bt


class TestMarkerParseResult:
    """MarkerParseResult 資料模型測試。"""

    def test_create_empty_result(self):
        """MarkerParseResult 可以建立空結果。"""
        result = MarkerParseResult(
            markdown="",
            blocks=[],
            toc=[],
            images={},
            metadata={},
            page_count=0,
        )
        assert result.markdown == ""
        assert len(result.blocks) == 0
        assert result.page_count == 0

    def test_create_with_content(self):
        """MarkerParseResult 帶完整內容。"""
        blocks = [
            MarkerBlock(
                block_id="blk_0001", block_type="SectionHeader", page=1, text="Title"
            ),
            MarkerBlock(
                block_id="blk_0002", block_type="Text", page=1, text="Content here"
            ),
        ]
        toc = [{"title": "Title", "page": 1, "level": 1}]

        result = MarkerParseResult(
            markdown="# Title\n\nContent here",
            blocks=blocks,
            toc=toc,
            images={},
            metadata={"title": "My Document"},
            page_count=1,
        )
        assert len(result.blocks) == 2
        assert result.blocks[0].block_type == "SectionHeader"
        assert len(result.toc) == 1
        assert result.metadata["title"] == "My Document"

    def test_blocks_have_unique_ids(self):
        """QB-2: 每個 block 的 block_id 都是唯一的。"""
        blocks = [
            MarkerBlock(block_id=f"blk_{i:04d}", block_type="Text", page=1)
            for i in range(1, 11)
        ]
        result = MarkerParseResult(
            markdown="",
            blocks=blocks,
            toc=[],
            images={},
            metadata={},
            page_count=1,
        )
        ids = [b.block_id for b in result.blocks]
        assert len(ids) == len(set(ids)), "block_ids must be unique"

    def test_page_numbers_1_indexed(self):
        """QB-4: page 為 1-indexed。"""
        blocks = [
            MarkerBlock(block_id="blk_0001", block_type="Text", page=1),
            MarkerBlock(block_id="blk_0002", block_type="Text", page=2),
            MarkerBlock(block_id="blk_0003", block_type="Text", page=3),
        ]
        result = MarkerParseResult(
            markdown="",
            blocks=blocks,
            toc=[],
            images={},
            metadata={},
            page_count=3,
        )
        for block in result.blocks:
            assert block.page >= 1, f"page should be >= 1, got {block.page}"
            assert block.page <= result.page_count, (
                f"page {block.page} exceeds page_count {result.page_count}"
            )
