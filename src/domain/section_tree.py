"""
Domain Layer - Section Tree

動態 Section 結構，支援任意深度的章節層級。
從 Marker 的 blocks.json 建構，不 hardcode 層級數。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator


@dataclass
class SectionNode:
    """
    動態 section 節點，支援任意深度。

    Attributes:
        title: 節點標題
        path: 完整路徑 ["Ch79", "Shock", "Patho"]
        depth: 層級深度 (1-based)
        page_start: 起始頁碼
        page_end: 結束頁碼
        block_count: 該節點的 block 數量（含子節點）
        direct_block_count: 該節點直屬的 block 數量（不含子節點）
        text_length: 文字長度（估算 token 用）
        children: 子節點 (title -> SectionNode)
        block_ids: 該節點直屬的 block IDs
    """

    title: str
    path: "list[str]" = field(default_factory=list)
    depth: int = 1

    # 統計資訊
    page_start: int | None = None
    page_end: int | None = None
    block_count: int = 0
    direct_block_count: int = 0
    text_length: int = 0

    # 子節點 (title -> SectionNode)
    children: "dict[str, SectionNode]" = field(default_factory=dict)

    # 該節點直屬的 block IDs
    block_ids: "list[str]" = field(default_factory=list)

    def add_block(self, block_id: str, page: int, text_len: int = 0) -> None:
        """新增 block 到此節點。"""
        self.block_ids.append(block_id)
        self.direct_block_count += 1
        self.block_count += 1
        self.text_length += text_len

        # 更新頁碼範圍
        if self.page_start is None or page < self.page_start:
            self.page_start = page
        if self.page_end is None or page > self.page_end:
            self.page_end = page

    def get_child(self, title: str) -> "SectionNode | None":
        """取得子節點。"""
        return self.children.get(title)

    def get_or_create_child(self, title: str) -> "SectionNode":
        """取得或建立子節點。"""
        if title not in self.children:
            self.children[title] = SectionNode(
                title=title,
                path=self.path + [title],
                depth=self.depth + 1,
            )
        return self.children[title]

    def update_stats_from_children(self) -> None:
        """從子節點更新統計資訊。"""
        for child in self.children.values():
            child.update_stats_from_children()
            self.block_count += child.block_count
            self.text_length += child.text_length

            # 更新頁碼範圍
            if child.page_start is not None:
                if self.page_start is None or child.page_start < self.page_start:
                    self.page_start = child.page_start
            if child.page_end is not None:
                if self.page_end is None or child.page_end > self.page_end:
                    self.page_end = child.page_end

    def get_all_block_ids(self) -> list[str]:
        """取得所有 block IDs（含子節點）。"""
        result = list(self.block_ids)
        for child in self.children.values():
            result.extend(child.get_all_block_ids())
        return result

    def find_by_path(self, path: list[str]) -> "SectionNode | None":
        """根據路徑找到節點。"""
        if not path:
            return self

        first, *rest = path
        child = self.children.get(first)
        if child is None:
            return None

        if not rest:
            return child
        return child.find_by_path(rest)

    def iter_all(self, max_depth: int | None = None) -> Iterator["SectionNode"]:
        """遍歷所有節點（含自己）。"""
        yield self
        if max_depth is None or self.depth < max_depth:
            for child in self.children.values():
                yield from child.iter_all(max_depth)

    def to_tree_string(
        self,
        max_depth: int | None = None,
        prefix: str = "",
        is_last: bool = True,
    ) -> str:
        """轉為樹狀字串。"""
        lines = []

        # 選擇圖示
        if self.depth == 1:
            icon = "📖"
        elif self.children:
            icon = "📑"
        else:
            icon = "📄"

        # 頁碼資訊
        page_info = ""
        if self.page_start and self.page_end:
            if self.page_start == self.page_end:
                page_info = f" (P{self.page_start})"
            else:
                page_info = f" (P{self.page_start}-{self.page_end})"

        # Block 統計
        block_info = f", {self.block_count} blocks" if self.block_count > 0 else ""

        # 本節點
        connector = "└── " if is_last else "├── "
        if self.depth == 1:
            lines.append(f"{icon} {self.title}{page_info}{block_info}")
        else:
            lines.append(f"{prefix}{connector}{icon} {self.title}{page_info}{block_info}")

        # 子節點
        if max_depth is None or self.depth < max_depth:
            child_prefix = prefix + ("    " if is_last else "│   ")
            children_list = list(self.children.values())
            for i, child in enumerate(children_list):
                is_child_last = (i == len(children_list) - 1)
                lines.append(child.to_tree_string(max_depth, child_prefix, is_child_last))

        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """轉為字典（用於 JSON 序列化）。"""
        return {
            "title": self.title,
            "path": self.path,
            "depth": self.depth,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "block_count": self.block_count,
            "direct_block_count": self.direct_block_count,
            "text_length": self.text_length,
            "block_ids": self.block_ids,
            "children": {k: v.to_dict() for k, v in self.children.items()},
        }

    def estimate_tokens(self) -> int:
        """估算 token 數量。"""
        return self.text_length // 4


class SectionTree:
    """
    Section 樹狀結構管理器。

    從 blocks.json 動態建構，支援任意深度。
    """

    def __init__(self, doc_id: str, title: str = "Document"):
        """
        初始化 Section Tree。

        Args:
            doc_id: 文件 ID
            title: 根節點標題
        """
        self.doc_id = doc_id
        self.root = SectionNode(title=title, path=[title], depth=1)
        self.blocks: dict[str, dict[str, Any]] = {}  # block_id -> block data
        self.max_depth = 1

    def add_block(self, block: dict[str, Any]) -> None:
        """
        新增 block 到樹中。

        Args:
            block: Block 資料，需包含：
                - block_id: str
                - section_hierarchy: dict[str, str] e.g. {"1": "Ch1", "2": "Sec1.1"}
                - page: int
                - text: str
        """
        block_id = block.get("block_id", "")
        section_hierarchy = block.get("section_hierarchy", {})
        page = block.get("page", 0)
        text = block.get("text", "")

        # 儲存 block 資料
        self.blocks[block_id] = block

        # 建構 section path
        # section_hierarchy 是 {"1": "Title1", "2": "Title2", ...}
        # 按 key 排序取得有序路徑
        sorted_keys = sorted(section_hierarchy.keys(), key=lambda x: int(x) if x.isdigit() else 999)
        section_path = [section_hierarchy[k] for k in sorted_keys if section_hierarchy[k]]

        # 如果沒有 section，放到根節點
        if not section_path:
            self.root.add_block(block_id, page, len(text))
            return

        # 更新根節點標題（用第一個 section）
        if self.root.title == "Document" and section_path:
            self.root.title = section_path[0]
            self.root.path = [section_path[0]]

        # 遍歷路徑，建立/找到節點
        current = self.root

        # 如果第一層不是根節點，需要特殊處理
        if section_path[0] != self.root.title:
            # 根節點是容器，第一層是子節點
            current = self.root.get_or_create_child(section_path[0])
            section_path = section_path[1:]
        else:
            # 第一層就是根節點
            section_path = section_path[1:]

        # 遍歷剩餘路徑
        for title in section_path:
            current = current.get_or_create_child(title)

        # 新增 block
        current.add_block(block_id, page, len(text))

        # 更新最大深度
        if current.depth > self.max_depth:
            self.max_depth = current.depth

    def build_stats(self) -> None:
        """建構統計資訊（從子節點向上彙總）。"""
        self.root.update_stats_from_children()

    def find_section(self, path: list[str] | str) -> SectionNode | None:
        """
        根據路徑找到 section。

        Args:
            path: 路徑，可以是 list 或 "/" 分隔的字串
        """
        if isinstance(path, str):
            path = [p.strip() for p in path.split("/") if p.strip()]

        if not path:
            return self.root

        # 嘗試從根節點開始
        if path[0] == self.root.title:
            return self.root.find_by_path(path[1:])

        # 嘗試從根節點的子節點開始
        return self.root.find_by_path(path)

    def search_sections(self, query: str, fuzzy: bool = True) -> list[SectionNode]:
        """
        搜尋 section 標題。

        Args:
            query: 搜尋關鍵字
            fuzzy: 是否模糊匹配
        """
        results = []
        query_lower = query.lower()

        for node in self.root.iter_all():
            title_lower = node.title.lower()
            if fuzzy:
                if query_lower in title_lower:
                    results.append(node)
            else:
                if query_lower == title_lower:
                    results.append(node)

        return results

    def get_blocks_for_section(
        self,
        path: list[str] | str,
        include_children: bool = True,
        block_types: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        取得特定 section 的 blocks。

        Args:
            path: Section 路徑
            include_children: 是否包含子 section
            block_types: 篩選 block 類型
        """
        node = self.find_section(path)
        if node is None:
            return []

        # 取得 block IDs
        if include_children:
            block_ids = node.get_all_block_ids()
        else:
            block_ids = node.block_ids

        # 取得 block 資料
        result = []
        for bid in block_ids:
            block = self.blocks.get(bid)
            if block:
                # 檢查類型篩選
                if block_types:
                    if block.get("block_type") not in block_types:
                        continue
                result.append(block)

        # 按頁碼排序
        result.sort(key=lambda b: (b.get("page", 0), b.get("block_id", "")))

        return result

    def to_tree_string(self, max_depth: int | None = None) -> str:
        """輸出樹狀字串。"""
        return self.root.to_tree_string(max_depth)

    def to_flat_list(self, max_depth: int | None = None) -> list[dict[str, Any]]:
        """輸出扁平列表。"""
        result = []
        for node in self.root.iter_all(max_depth):
            result.append({
                "title": node.title,
                "path": "/".join(node.path),
                "depth": node.depth,
                "page_start": node.page_start,
                "page_end": node.page_end,
                "block_count": node.block_count,
                "est_tokens": node.estimate_tokens(),
            })
        return result

    def to_dict(self) -> dict[str, Any]:
        """輸出 JSON 結構。"""
        return {
            "doc_id": self.doc_id,
            "max_depth": self.max_depth,
            "total_blocks": len(self.blocks),
            "tree": self.root.to_dict(),
        }


def build_section_tree_from_blocks(
    doc_id: str,
    blocks: list[dict[str, Any]],
    doc_title: str = "Document",
) -> SectionTree:
    """
    從 blocks 列表建構 SectionTree。

    Args:
        doc_id: 文件 ID
        blocks: Blocks 列表
        doc_title: 文件標題

    Returns:
        SectionTree 實例
    """
    tree = SectionTree(doc_id, doc_title)

    for block in blocks:
        tree.add_block(block)

    tree.build_stats()

    return tree
