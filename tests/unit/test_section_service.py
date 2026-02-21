"""
Unit Tests — Section Service

測試 SectionService 的服務層邏輯。
使用 mock 的 blocks.json 檔案，不需要 Marker 模型。

對應規格：docs/marker-etl-spec.md Section 3.2
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.application.section_service import SectionService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_blocks_data() -> list[dict]:
    """模擬 blocks.json 的內容。"""
    return [
        {
            "block_id": "blk_0001",
            "block_type": "SectionHeader",
            "page": 1,
            "text": "Abstract",
            "bbox": [72.0, 100.0, 540.0, 120.0],
            "section_hierarchy": {"1": "Abstract"},
        },
        {
            "block_id": "blk_0002",
            "block_type": "Text",
            "page": 1,
            "text": "This paper presents a novel method for analyzing...",
            "bbox": [72.0, 130.0, 540.0, 200.0],
            "section_hierarchy": {"1": "Abstract"},
        },
        {
            "block_id": "blk_0003",
            "block_type": "SectionHeader",
            "page": 1,
            "text": "Introduction",
            "bbox": [72.0, 220.0, 540.0, 240.0],
            "section_hierarchy": {"1": "Introduction"},
        },
        {
            "block_id": "blk_0004",
            "block_type": "Text",
            "page": 1,
            "text": "Anesthesiology has seen significant advances...",
            "bbox": [72.0, 250.0, 540.0, 400.0],
            "section_hierarchy": {"1": "Introduction"},
        },
        {
            "block_id": "blk_0005",
            "block_type": "SectionHeader",
            "page": 2,
            "text": "Methods",
            "bbox": [72.0, 100.0, 540.0, 120.0],
            "section_hierarchy": {"1": "Methods"},
        },
        {
            "block_id": "blk_0006",
            "block_type": "SectionHeader",
            "page": 2,
            "text": "Data Collection",
            "bbox": [72.0, 130.0, 540.0, 150.0],
            "section_hierarchy": {"1": "Methods", "2": "Data Collection"},
        },
        {
            "block_id": "blk_0007",
            "block_type": "Text",
            "page": 2,
            "text": "We collected data from multiple hospitals...",
            "bbox": [72.0, 160.0, 540.0, 300.0],
            "section_hierarchy": {"1": "Methods", "2": "Data Collection"},
        },
        {
            "block_id": "blk_0008",
            "block_type": "Table",
            "page": 3,
            "text": "| Hospital | Patients | Outcome |\n|---|---|---|\n| A | 100 | Good |",
            "bbox": [72.0, 100.0, 540.0, 200.0],
            "section_hierarchy": {"1": "Results"},
        },
    ]


@pytest.fixture
def sample_manifest_data() -> dict:
    """模擬 manifest.json 的內容。"""
    return {
        "doc_id": "doc_test_abc123",
        "filename": "test_paper.pdf",
        "title": "Test Paper Title",
        "page_count": 5,
    }


@pytest.fixture
def setup_data_dir(
    temp_dir: Path,
    sample_blocks_data: list[dict],
    sample_manifest_data: dict,
) -> tuple[Path, str]:
    """
    建立測試用的 data 目錄結構。

    Returns:
        (data_dir, doc_id) tuple
    """
    doc_id = "doc_test_abc123"
    doc_dir = temp_dir / doc_id
    doc_dir.mkdir(parents=True)

    # 寫入 blocks.json
    blocks_path = doc_dir / "blocks.json"
    blocks_path.write_text(json.dumps(sample_blocks_data, ensure_ascii=False, indent=2))

    # 寫入 {doc_id}_manifest.json (與 FileStorage 慣例一致)
    manifest_path = doc_dir / f"{doc_id}_manifest.json"
    manifest_path.write_text(
        json.dumps(sample_manifest_data, ensure_ascii=False, indent=2)
    )

    return temp_dir, doc_id


# ============================================================================
# Tests
# ============================================================================


class TestSectionServiceLoad:
    """SectionService 載入與快取測試。"""

    def test_load_tree_success(self, setup_data_dir):
        """正確載入 blocks.json 並建構樹。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        tree = service._load_tree(doc_id)
        assert tree is not None
        assert tree.doc_id == doc_id
        assert tree.root.block_count > 0

    def test_load_tree_no_blocks(self, temp_dir: Path):
        """QMT-1: blocks.json 不存在時回傳 None。"""
        service = SectionService(data_dir=temp_dir)

        tree = service._load_tree("nonexistent_doc")
        assert tree is None

    def test_cache_works(self, setup_data_dir):
        """快取機制：第二次不重新載入。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        tree1 = service._load_tree(doc_id)
        tree2 = service._load_tree(doc_id)
        assert tree1 is tree2  # 同一個物件（快取命中）

    def test_clear_cache_specific(self, setup_data_dir):
        """clear_cache 正確清除指定文件。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        service._load_tree(doc_id)
        assert doc_id in service._tree_cache

        service.clear_cache(doc_id)
        assert doc_id not in service._tree_cache

    def test_clear_cache_all(self, setup_data_dir):
        """clear_cache 清除所有快取。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        service._load_tree(doc_id)
        service.clear_cache()
        assert len(service._tree_cache) == 0


class TestListSectionTree:
    """list_section_tree 測試。"""

    @pytest.mark.asyncio
    async def test_tree_format(self, setup_data_dir):
        """QMT-2: tree 格式正確。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.list_section_tree(doc_id, format="tree")
        assert "Section Tree" in result
        assert "```" in result  # 有 code block
        assert doc_id in result

    @pytest.mark.asyncio
    async def test_flat_format(self, setup_data_dir):
        """QMT-2: flat 格式正確。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.list_section_tree(doc_id, format="flat")
        assert "Depth" in result
        assert "Path" in result
        assert "|" in result  # 表格格式

    @pytest.mark.asyncio
    async def test_json_format(self, setup_data_dir):
        """QMT-2: json 格式正確。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.list_section_tree(doc_id, format="json")
        assert "```json" in result
        # JSON 部分應可被解析
        json_start = result.index("```json") + 7
        json_end = result.index("```", json_start)
        json_str = result[json_start:json_end].strip()
        parsed = json.loads(json_str)
        assert "doc_id" in parsed

    @pytest.mark.asyncio
    async def test_no_blocks_error(self, temp_dir: Path):
        """QMT-1: 無 blocks.json 時回傳錯誤訊息。"""
        service = SectionService(data_dir=temp_dir)
        result = await service.list_section_tree("nonexistent_doc")

        assert "❌" in result
        assert "blocks.json not found" in result
        assert "ingest_documents" in result  # 應包含修復建議

    @pytest.mark.asyncio
    async def test_max_depth_limit(self, setup_data_dir):
        """max_depth 限制深度。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result_full = await service.list_section_tree(doc_id, max_depth=None)
        result_limited = await service.list_section_tree(doc_id, max_depth=1)

        # 限制深度後，輸出應更短
        assert len(result_limited) <= len(result_full)


class TestGetSectionDetail:
    """get_section_detail 測試。"""

    @pytest.mark.asyncio
    async def test_found(self, setup_data_dir):
        """QMT: 成功找到 section。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.get_section_detail(doc_id, "Methods")
        assert "Methods" in result
        assert "Path:" in result

    @pytest.mark.asyncio
    async def test_not_found_with_suggestions(self, setup_data_dir):
        """QMT: 找不到時提供建議。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.get_section_detail(doc_id, "Methodzzz")
        assert "❌" in result
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_nested_path(self, setup_data_dir):
        """QMT: 支援巢狀路徑。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.get_section_detail(doc_id, "Methods/Data Collection")
        assert "Data Collection" in result


class TestGetSectionBlocks:
    """get_section_blocks 測試。"""

    @pytest.mark.asyncio
    async def test_get_blocks(self, setup_data_dir):
        """QMT-3: 取得 section 的 blocks。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.get_section_blocks(doc_id, "Abstract")
        assert "Blocks" in result
        assert "blk_" in result

    @pytest.mark.asyncio
    async def test_include_children(self, setup_data_dir):
        """QMT-3: include_children 開關。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        with_children = await service.get_section_blocks(
            doc_id, "Methods", include_children=True
        )
        without_children = await service.get_section_blocks(
            doc_id, "Methods", include_children=False
        )

        # 含子節點的結果應 ≥ 不含子節點的
        assert len(with_children) >= len(without_children)

    @pytest.mark.asyncio
    async def test_filter_block_types(self, setup_data_dir):
        """QMT: 過濾 block_types。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.get_section_blocks(
            doc_id, "Results", block_types=["Table"]
        )
        # 如果有 Table blocks，結果應只包含 Table
        if "Block" in result and "Table" in result:
            assert "Text" not in result or "block_type" not in result


class TestSearchSections:
    """search_sections 測試。"""

    @pytest.mark.asyncio
    async def test_search_found(self, setup_data_dir):
        """QMT-4: 搜尋到結果。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.search_sections(doc_id, "method")
        assert "Found" in result
        assert "Methods" in result

    @pytest.mark.asyncio
    async def test_search_not_found(self, setup_data_dir):
        """QMT-4: 搜尋無結果。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result = await service.search_sections(doc_id, "xyzzy_nonexistent")
        assert "No sections found" in result

    @pytest.mark.asyncio
    async def test_search_case_insensitive(self, setup_data_dir):
        """QMT-4: 搜尋不區分大小寫。"""
        data_dir, doc_id = setup_data_dir
        service = SectionService(data_dir=data_dir)

        result_lower = await service.search_sections(doc_id, "abstract")
        result_upper = await service.search_sections(doc_id, "ABSTRACT")

        # 都應該找到 Abstract
        assert "Abstract" in result_lower
        assert "Abstract" in result_upper
