"""
Infrastructure Layer - Marker PDF Adapter

使用 marker-pdf 進行結構化 PDF 解析，提供：
- Block-level 解析（polygon, bbox, section_hierarchy）
- 目錄 (TOC) 提取
- 圖片 + 圖說 (caption) 提取
- 章節層級追蹤

比 PyMuPDF 更精準的結構化輸出。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from marker.converters.pdf import PdfConverter  # type: ignore
from marker.models import create_model_dict  # type: ignore
from marker.output import text_from_rendered  # type: ignore

from src.domain.entities import (
    DocumentAssets,
    DocumentManifest,
    FigureAsset,
    SectionAsset,
    TableAsset,
)


@dataclass
class MarkerBlock:
    """Marker 解析出的區塊資訊。"""

    block_id: str
    block_type: str  # Text, Table, Figure, SectionHeader, etc.
    page: int  # 1-indexed
    text: str = ""
    bbox: list[float] = field(default_factory=list)  # [x0, y0, x1, y1]
    polygon: list[list[float]] = field(default_factory=list)  # [[x,y], ...]
    section_hierarchy: dict[str, str] = field(default_factory=dict)  # {"1": "Ch1", "2": "1.1"}
    children: list["MarkerBlock"] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarkerParseResult:
    """Marker 完整解析結果。"""

    markdown: str
    blocks: list[MarkerBlock]
    toc: list[dict[str, Any]]  # [{title, page, level}, ...]
    images: dict[str, bytes]  # {filename: image_bytes}
    metadata: dict[str, Any]
    page_count: int


class MarkerPDFExtractor:
    """
    使用 marker-pdf 的結構化 PDF 提取器。

    提供比 PyMuPDF 更豐富的結構資訊：
    - Block tree with section_hierarchy
    - Polygon coordinates for each block
    - Figure captions detection
    - TOC extraction
    """

    def __init__(self, output_dir: Path | None = None):
        """
        初始化 Marker 提取器。

        Args:
            output_dir: 圖片輸出目錄（預設為臨時目錄）
        """
        self.output_dir = output_dir or Path("./temp_output")
        self._model_dict: dict | None = None

    def _get_models(self) -> dict:
        """懶加載 Marker 模型（首次使用時初始化）。"""
        if self._model_dict is None:
            self._model_dict = create_model_dict()
        return self._model_dict

    def parse(self, pdf_path: Path) -> MarkerParseResult:
        """
        完整解析 PDF 文件。

        Args:
            pdf_path: PDF 檔案路徑

        Returns:
            MarkerParseResult 包含 markdown, blocks, toc, images
        """
        converter = PdfConverter(artifact_dict=self._get_models())
        rendered = converter(str(pdf_path))

        # 提取 markdown 文字 (text_from_rendered returns tuple: (text, format, images_dict))
        result = text_from_rendered(rendered)
        markdown_text = result[0] if isinstance(result, tuple) else str(result)

        # 解析 blocks
        blocks = self._extract_blocks(rendered)

        # 提取 TOC
        toc = self._extract_toc(rendered)

        # 提取圖片
        images = self._extract_images(rendered)

        # 取得 metadata
        metadata = self._extract_metadata(rendered)

        return MarkerParseResult(
            markdown=markdown_text,
            blocks=blocks,
            toc=toc,
            images=images,
            metadata=metadata,
            page_count=len(rendered.children) if hasattr(rendered, "children") else 0,
        )

    def _extract_blocks(self, rendered: Any) -> list[MarkerBlock]:
        """從 rendered 結果提取結構化 blocks。"""
        blocks: list[MarkerBlock] = []
        block_counter = 0

        def traverse_node(node: Any, page_num: int = 1, section_hierarchy: dict | None = None):
            nonlocal block_counter
            section_hierarchy = section_hierarchy or {}

            # 取得 block type
            block_type = getattr(node, "block_type", None) or type(node).__name__

            # 取得文字內容
            text = ""
            if hasattr(node, "text"):
                text = node.text or ""
            elif hasattr(node, "raw_text"):
                text = node.raw_text() if callable(node.raw_text) else str(node.raw_text)

            # 取得 bbox/polygon
            bbox = []
            polygon = []
            if hasattr(node, "polygon"):
                polygon = node.polygon if isinstance(node.polygon, list) else []
                if polygon and len(polygon) >= 4:
                    xs = [p[0] for p in polygon if len(p) >= 2]
                    ys = [p[1] for p in polygon if len(p) >= 2]
                    if xs and ys:
                        bbox = [min(xs), min(ys), max(xs), max(ys)]
            elif hasattr(node, "bbox"):
                bbox = list(node.bbox) if node.bbox else []

            # 取得 page
            if hasattr(node, "page_id"):
                page_num = (node.page_id or 0) + 1  # 0-indexed to 1-indexed

            # 更新 section hierarchy（如果是 SectionHeader）
            current_hierarchy = dict(section_hierarchy)
            if block_type == "SectionHeader" and text:
                level = getattr(node, "level", 1)
                current_hierarchy[str(level)] = text.strip()
                # 清除更低層級
                for key in list(current_hierarchy.keys()):
                    if int(key) > level:
                        del current_hierarchy[key]

            block_counter += 1
            block = MarkerBlock(
                block_id=f"blk_{block_counter:04d}",
                block_type=block_type,
                page=page_num,
                text=text,
                bbox=bbox,
                polygon=polygon,
                section_hierarchy=current_hierarchy,
                metadata={
                    "id": getattr(node, "id", None),
                    "level": getattr(node, "level", None),
                },
            )
            blocks.append(block)

            # 遞迴處理子節點
            children = getattr(node, "children", []) or []
            for child in children:
                traverse_node(child, page_num, current_hierarchy)

        # 開始遍歷
        if hasattr(rendered, "children"):
            for page_idx, page in enumerate(rendered.children):
                traverse_node(page, page_idx + 1)
        else:
            traverse_node(rendered)

        return blocks

    def _extract_toc(self, rendered: Any) -> list[dict[str, Any]]:
        """提取目錄結構。"""
        toc = []

        if hasattr(rendered, "toc") and rendered.toc:
            for item in rendered.toc:
                toc.append({
                    "title": getattr(item, "title", str(item)),
                    "page": getattr(item, "page", 0),
                    "level": getattr(item, "level", 1),
                })
        else:
            # 從 SectionHeader blocks 建構 TOC
            for block in self._extract_blocks(rendered):
                if block.block_type == "SectionHeader" and block.text:
                    toc.append({
                        "title": block.text.strip(),
                        "page": block.page,
                        "level": block.metadata.get("level", 1) or 1,
                    })

        return toc

    def _extract_images(self, rendered: Any) -> dict[str, bytes]:
        """提取所有圖片。"""
        images = {}

        if hasattr(rendered, "images"):
            # Marker 的 images 是 dict[str, PIL.Image]
            for name, img in rendered.images.items():
                try:
                    import io
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    images[name] = buf.getvalue()
                except Exception:
                    continue

        return images

    def _extract_metadata(self, rendered: Any) -> dict[str, Any]:
        """提取文件 metadata。"""
        metadata = {}

        if hasattr(rendered, "metadata"):
            metadata = dict(rendered.metadata) if rendered.metadata else {}

        return metadata

    def convert_to_manifest(
        self,
        parse_result: MarkerParseResult,
        pdf_path: Path,
        output_dir: Path,
    ) -> DocumentManifest:
        """
        將 Marker 解析結果轉換為 DocumentManifest。

        Args:
            parse_result: Marker 解析結果
            pdf_path: 原始 PDF 路徑
            output_dir: 輸出目錄 (存放 markdown, images)

        Returns:
            DocumentManifest
        """
        # 生成 doc_id (使用與 DocumentService 一致的慣例)
        from src.domain.value_objects import DocId
        doc_id = DocId.generate(pdf_path.stem, str(pdf_path.absolute())).value

        # 確保輸出目錄存在
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "figures"
        images_dir.mkdir(exist_ok=True)

        # 儲存 markdown
        markdown_path = output_dir / "content.md"
        markdown_path.write_text(parse_result.markdown, encoding="utf-8")

        # 儲存圖片並建立 FigureAsset
        figures: list[FigureAsset] = []

        # Collect all Figure blocks for 1:1 matching
        figure_blocks = [
            block for block in parse_result.blocks
            if block.block_type == "Figure"
        ]

        for idx, (img_name, img_bytes) in enumerate(parse_result.images.items(), 1):
            ext = img_name.split(".")[-1] if "." in img_name else "png"
            fig_path = images_dir / f"fig_{idx}.{ext}"
            fig_path.write_bytes(img_bytes)

            # Match corresponding Figure block by index
            page = 1
            caption = ""
            if idx - 1 < len(figure_blocks):
                matched = figure_blocks[idx - 1]
                page = matched.page
                caption = matched.metadata.get("caption", "")

            # Read actual image dimensions
            width, height = 0, 0
            try:
                import io
                from PIL import Image
                img = Image.open(io.BytesIO(img_bytes))
                width, height = img.size
            except Exception:
                pass

            figures.append(FigureAsset(
                id=f"fig_{idx}",
                page=page,
                path=str(fig_path),
                ext=ext,
                caption=caption,
                width=width,
                height=height,
                figure_type="",
                source="marker",
            ))

        # 建立 SectionAsset
        sections: list[SectionAsset] = []
        for idx, toc_item in enumerate(parse_result.toc, 1):
            sections.append(SectionAsset(
                id=f"sec_{idx}",
                title=toc_item.get("title", ""),
                level=toc_item.get("level", 1),
                page=toc_item.get("page", 0),
                start_line=0,
                end_line=0,
                preview="",
            ))

        # 建立 TableAsset（從 blocks 中提取）
        tables: list[TableAsset] = []
        table_idx = 0
        for block in parse_result.blocks:
            if block.block_type == "Table":
                table_idx += 1
                # Parse row/col counts from markdown
                row_count, col_count = 0, 0
                if block.text:
                    lines = [l.strip() for l in block.text.strip().splitlines() if l.strip()]
                    data_lines = [l for l in lines if not all(c in "-| :" for c in l)]
                    row_count = len(data_lines)
                    if data_lines:
                        col_count = max(data_lines[0].count("|") - 1, 0)
                tables.append(TableAsset(
                    id=f"tab_{table_idx}",
                    page=block.page,
                    caption="",
                    preview=block.text[:100] if block.text else "",
                    markdown=block.text,
                    row_count=row_count,
                    col_count=col_count,
                    has_header=True,
                    source="marker",
                ))

        # 建立 DocumentAssets
        assets = DocumentAssets(
            tables=tables,
            figures=figures,
            sections=sections,
        )

        # 建立 DocumentManifest
        manifest = DocumentManifest(
            doc_id=doc_id,
            filename=pdf_path.name,
            title=parse_result.metadata.get("title", pdf_path.stem),
            toc=[item["title"] for item in parse_result.toc],
            assets=assets,
            lightrag_entities=[],
            page_count=parse_result.page_count,
            markdown_path=str(markdown_path),
            manifest_path=str(output_dir / "manifest.json"),
        )

        # 儲存 manifest
        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(
            manifest.model_dump_json(indent=2),
            encoding="utf-8",
        )

        # 儲存 blocks.json (額外的結構化資料)
        blocks_data = [
            {
                "block_id": b.block_id,
                "block_type": b.block_type,
                "page": b.page,
                "text": b.text[:500] if b.text else "",  # 截斷避免過大
                "bbox": b.bbox,
                "section_hierarchy": b.section_hierarchy,
            }
            for b in parse_result.blocks
        ]
        blocks_path = output_dir / "blocks.json"
        blocks_path.write_text(
            json.dumps(blocks_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return manifest

    def extract_to_manifest(self, pdf_path: Path, output_dir: Path) -> DocumentManifest:
        """
        一站式 API：解析 PDF 並輸出 DocumentManifest。

        Args:
            pdf_path: PDF 檔案路徑
            output_dir: 輸出目錄

        Returns:
            DocumentManifest
        """
        result = self.parse(pdf_path)
        return self.convert_to_manifest(result, pdf_path, output_dir)
