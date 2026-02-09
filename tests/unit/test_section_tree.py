"""
Unit Tests — Section Tree 資料結構

測試 SectionNode, SectionTree, build_section_tree_from_blocks。
不需要 Marker 模型或真實 blocks.json，使用造假資料。

對應規格：docs/marker-etl-spec.md Section 3
"""

from __future__ import annotations

import pytest

from src.domain.section_tree import SectionNode, SectionTree, build_section_tree_from_blocks


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def simple_blocks() -> list[dict]:
    """簡單的 blocks 資料（2 層結構）。"""
    return [
        {
            "block_id": "blk_0001",
            "block_type": "SectionHeader",
            "page": 1,
            "text": "Introduction",
            "section_hierarchy": {"1": "Introduction"},
        },
        {
            "block_id": "blk_0002",
            "block_type": "Text",
            "page": 1,
            "text": "This is the introduction paragraph." * 10,
            "section_hierarchy": {"1": "Introduction"},
        },
        {
            "block_id": "blk_0003",
            "block_type": "SectionHeader",
            "page": 2,
            "text": "Methods",
            "section_hierarchy": {"1": "Methods"},
        },
        {
            "block_id": "blk_0004",
            "block_type": "Text",
            "page": 2,
            "text": "We used the following methods.",
            "section_hierarchy": {"1": "Methods"},
        },
        {
            "block_id": "blk_0005",
            "block_type": "SectionHeader",
            "page": 2,
            "text": "Data Collection",
            "section_hierarchy": {"1": "Methods", "2": "Data Collection"},
        },
        {
            "block_id": "blk_0006",
            "block_type": "Text",
            "page": 2,
            "text": "Data was collected from hospitals.",
            "section_hierarchy": {"1": "Methods", "2": "Data Collection"},
        },
        {
            "block_id": "blk_0007",
            "block_type": "SectionHeader",
            "page": 3,
            "text": "Results",
            "section_hierarchy": {"1": "Results"},
        },
        {
            "block_id": "blk_0008",
            "block_type": "Table",
            "page": 3,
            "text": "| A | B |\n|---|---|\n| 1 | 2 |",
            "section_hierarchy": {"1": "Results"},
        },
    ]


@pytest.fixture
def deep_blocks() -> list[dict]:
    """深層 blocks 資料（4 層結構）。"""
    return [
        {
            "block_id": "blk_0001",
            "block_type": "SectionHeader",
            "page": 1,
            "text": "Chapter 79: Shock",
            "section_hierarchy": {"1": "Chapter 79: Shock"},
        },
        {
            "block_id": "blk_0002",
            "block_type": "SectionHeader",
            "page": 1,
            "text": "Pathophysiology",
            "section_hierarchy": {"1": "Chapter 79: Shock", "2": "Pathophysiology"},
        },
        {
            "block_id": "blk_0003",
            "block_type": "SectionHeader",
            "page": 2,
            "text": "Cellular Mechanisms",
            "section_hierarchy": {"1": "Chapter 79: Shock", "2": "Pathophysiology", "3": "Cellular Mechanisms"},
        },
        {
            "block_id": "blk_0004",
            "block_type": "SectionHeader",
            "page": 2,
            "text": "Mitochondrial Dysfunction",
            "section_hierarchy": {
                "1": "Chapter 79: Shock",
                "2": "Pathophysiology",
                "3": "Cellular Mechanisms",
                "4": "Mitochondrial Dysfunction",
            },
        },
        {
            "block_id": "blk_0005",
            "block_type": "Text",
            "page": 2,
            "text": "Mitochondrial dysfunction plays a key role in shock.",
            "section_hierarchy": {
                "1": "Chapter 79: Shock",
                "2": "Pathophysiology",
                "3": "Cellular Mechanisms",
                "4": "Mitochondrial Dysfunction",
            },
        },
    ]


# ============================================================================
# SectionNode Tests
# ============================================================================


class TestSectionNode:
    """SectionNode 單元測試。"""

    def test_create_node(self):
        """建立節點。"""
        node = SectionNode(title="Introduction", path=["Introduction"], depth=1)
        assert node.title == "Introduction"
        assert node.depth == 1
        assert node.block_count == 0
        assert node.children == {}

    def test_add_block(self):
        """新增 block 更新統計。"""
        node = SectionNode(title="Test", path=["Test"], depth=1)
        node.add_block("blk_0001", page=1, text_len=100)
        node.add_block("blk_0002", page=2, text_len=200)

        assert node.block_count == 2
        assert node.direct_block_count == 2
        assert node.text_length == 300
        assert node.page_start == 1
        assert node.page_end == 2
        assert "blk_0001" in node.block_ids

    def test_get_or_create_child(self):
        """建立/取得子節點。"""
        parent = SectionNode(title="Root", path=["Root"], depth=1)

        child1 = parent.get_or_create_child("Child1")
        assert child1.title == "Child1"
        assert child1.depth == 2
        assert child1.path == ["Root", "Child1"]

        # 再次取得同名子節點，應回傳同一物件
        child1_again = parent.get_or_create_child("Child1")
        assert child1_again is child1

    def test_update_stats_from_children(self):
        """QST-4: 從子節點更新統計。"""
        parent = SectionNode(title="Root", path=["Root"], depth=1)
        parent.add_block("blk_root", page=1, text_len=50)

        child = parent.get_or_create_child("Child")
        child.add_block("blk_child_1", page=2, text_len=100)
        child.add_block("blk_child_2", page=3, text_len=150)

        parent.update_stats_from_children()

        # 父節點的 block_count 應該包含子節點
        assert parent.block_count == 3  # 1 (自己) + 2 (子節點)
        assert parent.text_length == 300  # 50 + 100 + 150
        assert parent.page_start == 1
        assert parent.page_end == 3

    def test_get_all_block_ids(self):
        """取得所有 block IDs（含子節點）。"""
        parent = SectionNode(title="Root", path=["Root"], depth=1)
        parent.add_block("blk_root", page=1)

        child = parent.get_or_create_child("Child")
        child.add_block("blk_child_1", page=2)
        child.add_block("blk_child_2", page=3)

        all_ids = parent.get_all_block_ids()
        assert set(all_ids) == {"blk_root", "blk_child_1", "blk_child_2"}

    def test_find_by_path(self):
        """根據路徑找到節點。"""
        root = SectionNode(title="Root", path=["Root"], depth=1)
        child = root.get_or_create_child("A")
        grandchild = child.get_or_create_child("B")

        assert root.find_by_path(["A", "B"]) is grandchild
        assert root.find_by_path(["A"]) is child
        assert root.find_by_path([]) is root
        assert root.find_by_path(["X"]) is None

    def test_iter_all(self):
        """遍歷所有節點。"""
        root = SectionNode(title="Root", path=["Root"], depth=1)
        root.get_or_create_child("A")
        root.get_or_create_child("B")

        nodes = list(root.iter_all())
        assert len(nodes) == 3
        titles = [n.title for n in nodes]
        assert "Root" in titles
        assert "A" in titles
        assert "B" in titles

    def test_iter_all_with_max_depth(self):
        """限制深度的遍歷。"""
        root = SectionNode(title="Root", path=["Root"], depth=1)
        child = root.get_or_create_child("A")
        child.get_or_create_child("B")

        nodes_depth_1 = list(root.iter_all(max_depth=1))
        assert len(nodes_depth_1) == 1  # 只有 Root

        nodes_depth_2 = list(root.iter_all(max_depth=2))
        assert len(nodes_depth_2) == 2  # Root + A

    def test_estimate_tokens(self):
        """估算 token 數量（text_length // 4）。"""
        node = SectionNode(title="Test", path=["Test"], depth=1)
        node.add_block("blk_0001", page=1, text_len=400)
        assert node.estimate_tokens() == 100

    def test_to_tree_string(self):
        """轉為樹狀字串。"""
        root = SectionNode(title="Doc", path=["Doc"], depth=1)
        root.get_or_create_child("A")
        root.get_or_create_child("B")

        tree_str = root.to_tree_string()
        assert "Doc" in tree_str
        assert "A" in tree_str
        assert "B" in tree_str

    def test_to_dict(self):
        """轉為字典。"""
        node = SectionNode(title="Test", path=["Test"], depth=1)
        node.add_block("blk_0001", page=1, text_len=100)

        d = node.to_dict()
        assert d["title"] == "Test"
        assert d["depth"] == 1
        assert d["block_count"] == 1
        assert "blk_0001" in d["block_ids"]


# ============================================================================
# SectionTree Tests
# ============================================================================


class TestSectionTree:
    """SectionTree 單元測試。"""

    def test_empty_tree(self):
        """空 blocks 建構空樹。"""
        tree = build_section_tree_from_blocks("doc_test", [], "Test Doc")
        assert tree.doc_id == "doc_test"
        assert tree.root.title == "Test Doc"
        assert tree.root.block_count == 0

    def test_simple_tree(self, simple_blocks: list[dict]):
        """QST: 簡單 blocks 正確建構樹。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        # 應該有 Introduction, Methods, Results 三個主要 section
        assert tree.max_depth >= 2  # 因為有 Data Collection 子節點
        assert tree.root.block_count == len(simple_blocks)

    def test_deep_tree(self, deep_blocks: list[dict]):
        """QST-2: 深層結構正確建構。"""
        tree = build_section_tree_from_blocks("doc_test", deep_blocks, "Textbook")

        assert tree.max_depth >= 4

    def test_find_section_by_string_path(self, simple_blocks: list[dict]):
        """find_section 支援字串路徑。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        # 搜尋 Methods 下的 Data Collection
        node = tree.find_section("Methods/Data Collection")
        assert node is not None
        assert node.title == "Data Collection"

    def test_find_section_by_list_path(self, simple_blocks: list[dict]):
        """find_section 支援列表路徑。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        node = tree.find_section(["Methods", "Data Collection"])
        assert node is not None
        assert node.title == "Data Collection"

    def test_find_section_not_found(self, simple_blocks: list[dict]):
        """find_section 找不到時回傳 None。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        node = tree.find_section("Nonexistent Section")
        assert node is None

    def test_search_sections_fuzzy(self, simple_blocks: list[dict]):
        """search_sections 模糊搜尋。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        results = tree.search_sections("method")
        assert len(results) >= 1
        titles = [r.title for r in results]
        assert any("Methods" in t for t in titles)

    def test_search_sections_exact(self, simple_blocks: list[dict]):
        """search_sections 精確搜尋。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        results = tree.search_sections("Methods", fuzzy=False)
        assert len(results) >= 1

    def test_get_blocks_for_section_with_children(self, simple_blocks: list[dict]):
        """get_blocks_for_section 含子節點。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        blocks = tree.get_blocks_for_section("Methods", include_children=True)
        # 應包含 Methods 自己的 blocks + Data Collection 的 blocks
        assert len(blocks) >= 3  # header + text + data collection blocks

    def test_get_blocks_for_section_without_children(self, simple_blocks: list[dict]):
        """get_blocks_for_section 不含子節點。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        blocks = tree.get_blocks_for_section("Methods", include_children=False)
        # 只有 Methods 直屬的 blocks
        blocks_with_children = tree.get_blocks_for_section("Methods", include_children=True)
        assert len(blocks) <= len(blocks_with_children)

    def test_get_blocks_filter_by_type(self, simple_blocks: list[dict]):
        """get_blocks_for_section 過濾 block_types。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        # 只取 Table blocks
        table_blocks = tree.get_blocks_for_section("Results", block_types=["Table"])
        for block in table_blocks:
            assert block["block_type"] == "Table"

    def test_block_count_accumulation(self, simple_blocks: list[dict]):
        """QST-4: block_count 正確向上累計。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        # 根節點的 block_count 應等於所有 blocks 數量
        assert tree.root.block_count == len(simple_blocks)

    def test_page_range(self, simple_blocks: list[dict]):
        """QST-5: page_start/page_end 正確。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        assert tree.root.page_start == 1
        assert tree.root.page_end == 3

    def test_to_flat_list(self, simple_blocks: list[dict]):
        """to_flat_list 正確輸出。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        flat = tree.to_flat_list()
        assert len(flat) > 0
        for item in flat:
            assert "title" in item
            assert "path" in item
            assert "depth" in item
            assert "block_count" in item

    def test_to_dict(self, simple_blocks: list[dict]):
        """to_dict 包含必要欄位。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        d = tree.to_dict()
        assert d["doc_id"] == "doc_test"
        assert "max_depth" in d
        assert "total_blocks" in d
        assert "tree" in d

    def test_blocks_sorted_by_page(self, simple_blocks: list[dict]):
        """QB-8: get_blocks_for_section 結果按頁碼排序。"""
        tree = build_section_tree_from_blocks("doc_test", simple_blocks, "Test Paper")

        all_blocks = tree.get_blocks_for_section(tree.root.title, include_children=True)
        pages = [b.get("page", 0) for b in all_blocks]
        assert pages == sorted(pages), "blocks should be sorted by page"


# ============================================================================
# Edge Cases
# ============================================================================


class TestSectionTreeEdgeCases:
    """邊界情況測試。"""

    def test_blocks_without_section_hierarchy(self):
        """沒有 section_hierarchy 的 blocks 歸入根節點。"""
        blocks = [
            {"block_id": "blk_0001", "block_type": "Text", "page": 1, "text": "Orphan text"},
        ]
        tree = build_section_tree_from_blocks("doc_test", blocks, "Doc")

        assert tree.root.block_count == 1
        assert "blk_0001" in tree.root.block_ids

    def test_blocks_with_empty_section_hierarchy(self):
        """空的 section_hierarchy。"""
        blocks = [
            {
                "block_id": "blk_0001",
                "block_type": "Text",
                "page": 1,
                "text": "Text",
                "section_hierarchy": {},
            },
        ]
        tree = build_section_tree_from_blocks("doc_test", blocks, "Doc")
        assert tree.root.block_count == 1

    def test_single_block_single_section(self):
        """只有一個 block 一個 section。"""
        blocks = [
            {
                "block_id": "blk_0001",
                "block_type": "SectionHeader",
                "page": 1,
                "text": "Only Section",
                "section_hierarchy": {"1": "Only Section"},
            },
        ]
        tree = build_section_tree_from_blocks("doc_test", blocks, "Doc")
        assert tree.root.block_count == 1

    def test_very_deep_hierarchy(self):
        """非常深的層級結構（6 層）。"""
        hierarchy = {str(i): f"Level {i}" for i in range(1, 7)}
        blocks = [
            {
                "block_id": "blk_0001",
                "block_type": "Text",
                "page": 1,
                "text": "Deep content",
                "section_hierarchy": hierarchy,
            },
        ]
        tree = build_section_tree_from_blocks("doc_test", blocks, "Doc")
        assert tree.max_depth >= 6

    def test_unicode_section_titles(self):
        """Unicode 章節標題（中文、日文等）。"""
        blocks = [
            {
                "block_id": "blk_0001",
                "block_type": "SectionHeader",
                "page": 1,
                "text": "第一章 緒論",
                "section_hierarchy": {"1": "第一章 緒論"},
            },
            {
                "block_id": "blk_0002",
                "block_type": "Text",
                "page": 1,
                "text": "本研究探討...",
                "section_hierarchy": {"1": "第一章 緒論"},
            },
        ]
        tree = build_section_tree_from_blocks("doc_test", blocks, "文件")

        results = tree.search_sections("緒論")
        assert len(results) >= 1
