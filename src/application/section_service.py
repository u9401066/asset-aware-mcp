"""
Application Layer - Section Service

提供 Section 樹狀結構的查詢和操作服務。
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Literal

from src.domain.section_tree import SectionTree, build_section_tree_from_blocks

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.repositories import DocumentRepository

_DOC_ID_RE = re.compile(r"^(?:doc|docx)_[a-z0-9_]+$")


class SectionService:
    """
    Section 服務層。

    負責：
    - 從 blocks.json 載入並建構 SectionTree
    - 提供 section 查詢和導航功能
    - 快取管理
    """

    def __init__(
        self,
        data_dir: Path | None = None,
        repository: DocumentRepository | None = None,
    ):
        """
        初始化 Section Service。

        Args:
            data_dir: 資料目錄（data/{doc_id}/ 結構）
        """
        if data_dir is None and repository is None:
            raise ValueError("SectionService requires data_dir or repository")
        self.data_dir = data_dir.resolve() if data_dir is not None else None
        self.repository = repository
        self._tree_cache: dict[str, SectionTree] = {}

    def _get_doc_dir(self, doc_id: str) -> Path:
        if self.repository is not None:
            return self.repository.get_doc_dir(doc_id)
        if self.data_dir is None:
            raise ValueError("data_dir is not configured")
        if not _DOC_ID_RE.fullmatch(doc_id):
            raise ValueError(f"Invalid document id: {doc_id}")
        doc_dir = (self.data_dir / doc_id).resolve()
        doc_dir.relative_to(self.data_dir)
        return doc_dir

    def _get_blocks_path(self, doc_id: str) -> Path:
        """取得 blocks.json 路徑。"""
        return self._get_doc_dir(doc_id) / "blocks.json"

    def _get_manifest_path(self, doc_id: str) -> Path:
        """取得 manifest.json 路徑。"""
        return self._get_doc_dir(doc_id) / f"{doc_id}_manifest.json"

    def _load_tree(self, doc_id: str) -> SectionTree | None:
        """
        載入或取得快取的 SectionTree。

        Args:
            doc_id: 文件 ID

        Returns:
            SectionTree 或 None（如果 blocks.json 不存在）
        """
        # 檢查快取
        if doc_id in self._tree_cache:
            return self._tree_cache[doc_id]

        # 載入 blocks.json
        try:
            blocks_path = self._get_blocks_path(doc_id)
        except ValueError:
            return None
        if not blocks_path.exists():
            return None

        try:
            blocks = json.loads(blocks_path.read_text(encoding="utf-8"))
        except Exception:
            return None

        # 嘗試從 manifest 取得標題
        doc_title = "Document"
        manifest_path = self._get_manifest_path(doc_id)
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                doc_title = (
                    manifest.get("title") or manifest.get("filename") or "Document"
                )
            except Exception:  # noqa: S110 — manifest parse failure is non-critical
                pass

        # 建構 tree
        tree = build_section_tree_from_blocks(doc_id, blocks, doc_title)

        # 快取
        self._tree_cache[doc_id] = tree

        return tree

    def clear_cache(self, doc_id: str | None = None) -> None:
        """
        清除快取。

        Args:
            doc_id: 指定要清除的文件，None 表示全部清除
        """
        if doc_id:
            self._tree_cache.pop(doc_id, None)
        else:
            self._tree_cache.clear()

    async def list_section_tree(
        self,
        doc_id: str,
        max_depth: int | None = None,
        format: Literal["tree", "flat", "json"] = "tree",
    ) -> str:
        """
        列出文件的 section 結構樹。

        Args:
            doc_id: 文件 ID
            max_depth: 最大顯示深度
            format: 輸出格式 (tree/flat/json)

        Returns:
            Section 樹狀結構（Markdown 格式）
        """
        tree = self._load_tree(doc_id)

        if tree is None:
            return (
                f"❌ **blocks.json not found for doc_id: `{doc_id}`**\n\n"
                f"Please run `ingest_documents` with `use_marker=True` first to generate blocks.json."
            )

        lines = [
            f"# 📚 Section Tree: {tree.root.title}",
            "",
            f"**Doc ID:** `{doc_id}`",
            f"**Max Depth:** {tree.max_depth}",
            f"**Total Blocks:** {len(tree.blocks)}",
            "",
        ]

        if format == "tree":
            lines.append("```")
            lines.append(tree.to_tree_string(max_depth))
            lines.append("```")

        elif format == "flat":
            flat_list = tree.to_flat_list(max_depth)
            lines.append("| Depth | Path | Pages | Blocks | Est. Tokens |")
            lines.append("|-------|------|-------|--------|-------------|")
            for item in flat_list:
                pages = (
                    f"{item['page_start']}-{item['page_end']}"
                    if item["page_start"]
                    else "-"
                )
                lines.append(
                    f"| {item['depth']} | {item['path']} | {pages} | "
                    f"{item['block_count']} | ~{item['est_tokens']} |"
                )

        elif format == "json":
            lines.append("```json")
            lines.append(json.dumps(tree.to_dict(), indent=2, ensure_ascii=False))
            lines.append("```")

        return "\n".join(lines)

    async def get_section_detail(
        self,
        doc_id: str,
        path: list[str] | str,
    ) -> str:
        """
        取得特定 section 的詳細資訊。

        Args:
            doc_id: 文件 ID
            path: Section 路徑

        Returns:
            Section 詳情
        """
        tree = self._load_tree(doc_id)

        if tree is None:
            return f"❌ blocks.json not found for doc_id: `{doc_id}`"

        node = tree.find_section(path)

        if node is None:
            # 提供搜尋建議
            if isinstance(path, str):
                search_query = path.split("/")[-1]
            else:
                search_query = path[-1] if path else ""

            suggestions = tree.search_sections(search_query)[:5]

            lines = [
                f"❌ **Section not found:** `{path}`",
                "",
            ]

            if suggestions:
                lines.append("**Did you mean:**")
                for s in suggestions:
                    lines.append(f"- `{'/'.join(s.path)}`")

            return "\n".join(lines)

        # 建構詳情
        lines = [
            f"## 📑 {node.title}",
            "",
            f"**Path:** {' > '.join(node.path)}",
            f"**Depth:** {node.depth}",
        ]

        if node.page_start and node.page_end:
            if node.page_start == node.page_end:
                lines.append(f"**Pages:** {node.page_start}")
            else:
                lines.append(f"**Pages:** {node.page_start}-{node.page_end}")

        lines.extend(
            [
                f"**Total Blocks:** {node.block_count}",
                f"**Direct Blocks:** {node.direct_block_count}",
                f"**Est. Tokens:** ~{node.estimate_tokens()}",
            ]
        )

        # 子節點
        if node.children:
            lines.append(f"\n### Sub-sections ({len(node.children)})")
            for child in node.children.values():
                page_info = ""
                if child.page_start and child.page_end:
                    if child.page_start == child.page_end:
                        page_info = f", P{child.page_start}"
                    else:
                        page_info = f", P{child.page_start}-{child.page_end}"

                icon = "📑" if child.children else "📄"
                lines.append(
                    f"- {icon} **{child.title}** ({child.block_count} blocks{page_info})"
                )

        # 預覽內容
        if node.block_ids:
            lines.append("\n### Preview")
            preview_blocks = []
            for bid in node.block_ids[:3]:
                block = tree.blocks.get(bid)
                if block:
                    text = block.get("text", "")[:200]
                    if text:
                        preview_blocks.append(text)

            if preview_blocks:
                preview_text = " ".join(preview_blocks)[:500]
                lines.append(f"> {preview_text}...")

        # 操作提示
        lines.extend(
            [
                "",
                "---",
                "**Next:**",
                f'- Get blocks: `get_section_blocks("{doc_id}", "{"/".join(node.path)}")`',
            ]
        )

        if node.children:
            first_child = next(iter(node.children.values()))
            lines.append(
                f'- Drill down: `get_section_detail("{doc_id}", "{"/".join(first_child.path)}")`'
            )

        return "\n".join(lines)

    async def get_section_blocks(
        self,
        doc_id: str,
        path: list[str] | str,
        include_children: bool = True,
        block_types: list[str] | None = None,
        limit: int | None = None,
    ) -> str:
        """
        取得特定 section 的 blocks。

        Args:
            doc_id: 文件 ID
            path: Section 路徑
            include_children: 是否包含子 section
            block_types: 篩選類型
            limit: 限制數量

        Returns:
            Blocks 列表
        """
        tree = self._load_tree(doc_id)

        if tree is None:
            return f"❌ blocks.json not found for doc_id: `{doc_id}`"

        node = tree.find_section(path)

        if node is None:
            return f"❌ Section not found: `{path}`"

        blocks = tree.get_blocks_for_section(path, include_children, block_types)

        if limit:
            blocks = blocks[:limit]

        if not blocks:
            return f"No blocks found in section: `{'/'.join(node.path)}`"

        lines = [
            f'## 📦 Blocks in "{node.title}"',
            "",
            f"**Section:** {' > '.join(node.path)}",
            f"**Total:** {len(blocks)} blocks",
            f"**Include Children:** {'Yes' if include_children else 'No'}",
        ]

        if block_types:
            lines.append(f"**Filter:** {', '.join(block_types)}")

        lines.append("")

        # 輸出每個 block
        for i, block in enumerate(blocks, 1):
            block_id = block.get("block_id", "")
            block_type = block.get("block_type", "Unknown")
            page = block.get("page", 0)
            bbox = block.get("bbox", [])
            text = block.get("text", "")
            section_hierarchy = block.get("section_hierarchy", {})

            # 建構 section path
            sorted_keys = sorted(
                section_hierarchy.keys(), key=lambda x: int(x) if x.isdigit() else 999
            )
            section_path = [
                section_hierarchy[k] for k in sorted_keys if section_hierarchy[k]
            ]

            lines.append(f"### Block {i} ({block_type}, P{page})")
            lines.append(f"**ID:** `{block_id}`")

            if bbox:
                lines.append(f"**BBox:** `{bbox}`")

            if section_path:
                lines.append(f"**Section:** {' > '.join(section_path)}")

            # 文字內容（截斷長文）
            if text:
                if len(text) > 500:
                    lines.append(f"\n> {text[:500]}...\n")
                else:
                    lines.append(f"\n> {text}\n")

        # Token 估算
        total_text_len = sum(len(b.get("text", "")) for b in blocks)
        lines.append(f"\n---\n**Est. Tokens:** ~{total_text_len // 4}")

        return "\n".join(lines)

    async def search_sections(
        self,
        doc_id: str,
        query: str,
        fuzzy: bool = True,
    ) -> str:
        """
        搜尋 section 名稱。

        Args:
            doc_id: 文件 ID
            query: 搜尋關鍵字
            fuzzy: 是否模糊匹配

        Returns:
            匹配的 section 列表
        """
        tree = self._load_tree(doc_id)

        if tree is None:
            return f"❌ blocks.json not found for doc_id: `{doc_id}`"

        results = tree.search_sections(query, fuzzy)

        if not results:
            return f'No sections found matching "{query}"'

        lines = [
            f'## 🔍 Found {len(results)} sections matching "{query}"',
            "",
        ]

        for i, node in enumerate(results, 1):
            page_info = ""
            if node.page_start and node.page_end:
                if node.page_start == node.page_end:
                    page_info = f"P{node.page_start}"
                else:
                    page_info = f"P{node.page_start}-{node.page_end}"

            lines.append(f"### {i}. {node.title}")
            lines.append(f"- **Path:** `{'/'.join(node.path)}`")
            if page_info:
                lines.append(f"- **Pages:** {page_info}")
            lines.append(f"- **Blocks:** {node.block_count}")
            lines.append(f"- **Est. Tokens:** ~{node.estimate_tokens()}")
            lines.append("")

        return "\n".join(lines)
