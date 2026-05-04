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

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.domain.entities import (
    DocumentAssets,
    DocumentManifest,
    FigureAsset,
    SectionAsset,
    TableAsset,
)
from src.domain.line_spans import annotate_marker_blocks, apply_asset_line_spans
from src.domain.marker_errors import MARKER_INSTALL_HINT, MarkerBackendUnavailable

AUTO_SAFE_CHUNK_PAGE_THRESHOLD = 10
AUTO_SAFE_CHUNK_SIZE = 1
AUTO_LARGE_CHUNK_PAGE_THRESHOLD = 800
AUTO_LARGE_CHUNK_SIZE = 200
AUTO_DISABLE_FIGURES_IMAGE_THRESHOLD = 2000


def _coerce_metadata_int(metadata: dict[str, Any], key: str, default: int = 0) -> int:
    value = metadata.get(key)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


@dataclass
class MarkerBlock:
    """Marker 解析出的區塊資訊。"""

    block_id: str
    block_type: str  # Text, Table, Figure, SectionHeader, etc.
    page: int  # 1-indexed
    text: str = ""
    bbox: list[float] = field(default_factory=list)  # [x0, y0, x1, y1]
    polygon: list[list[float]] = field(default_factory=list)  # [[x,y], ...]
    section_hierarchy: dict[str, str] = field(
        default_factory=dict
    )  # {"1": "Ch1", "2": "1.1"}
    children: list[MarkerBlock] = field(default_factory=list)
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

    @staticmethod
    def require_backend_available() -> None:
        """Preflight marker-pdf imports without loading OCR models."""
        try:
            from marker.converters.pdf import PdfConverter  # type: ignore # noqa: F401
            from marker.models import create_model_dict  # type: ignore # noqa: F401
            from marker.output import text_from_rendered  # type: ignore # noqa: F401
        except (ImportError, OSError) as exc:
            raise MarkerBackendUnavailable(MARKER_INSTALL_HINT) from exc

    def _get_models(self) -> dict:
        """懶加載 Marker 模型（首次使用時初始化）。"""
        if self._model_dict is None:
            from marker.models import create_model_dict  # type: ignore

            self._model_dict = create_model_dict()
        return self._model_dict

    def _get_converter(self, *, extract_images: bool) -> Any:
        """建立可重用的 Marker converter。"""
        from marker.converters.pdf import PdfConverter  # type: ignore

        return PdfConverter(
            artifact_dict=self._get_models(),
            config={"extract_images": extract_images},
        )

    @staticmethod
    def _stringify_marker_block_id(value: Any) -> str:
        """將 Marker block id 正規化為穩定的字串表示。"""
        if value is None:
            return ""
        return str(value)

    @staticmethod
    def _normalize_marker_image_key(value: str) -> str:
        """將 image filename / block path 正規化成可比對的 key。"""
        stem = Path(value).stem if "." in value else value
        return stem if not stem.startswith("/") else stem.replace("/", "_")

    @staticmethod
    def _shift_marker_block_reference(reference: str, page_offset: int) -> str:
        """將 Marker block path 的 page id 平移到原始 PDF 座標。"""
        if page_offset == 0 or not reference.startswith("/page/"):
            return reference

        parts = reference.split("/")
        if len(parts) < 4:
            return reference

        try:
            parts[2] = str(int(parts[2]) + page_offset)
        except ValueError:
            return reference
        return "/".join(parts)

    @staticmethod
    def _shift_marker_image_name(image_name: str, page_offset: int) -> str:
        """將 Marker renderer 產出的 image key page id 平移到原始 PDF 座標。"""
        if page_offset == 0:
            return image_name

        stem, dot, ext = image_name.rpartition(".")
        if not dot:
            stem = image_name

        parts = stem.split("_")
        if len(parts) < 5 or parts[1] != "page":
            return image_name

        try:
            parts[2] = str(int(parts[2]) + page_offset)
        except ValueError:
            return image_name

        shifted = "_".join(parts)
        return f"{shifted}.{ext}" if dot else shifted

    @staticmethod
    def _select_image_blocks(blocks: list[MarkerBlock]) -> list[MarkerBlock]:
        """優先保留語意 Figure block，必要時退回 Picture block。"""
        figure_blocks = [block for block in blocks if block.block_type == "Figure"]
        if figure_blocks:
            return figure_blocks
        return [block for block in blocks if block.block_type in {"Figure", "Picture"}]

    @staticmethod
    def _remap_page_number(page_number: int, page_map: list[int] | None) -> int:
        """將 subset-local 頁碼轉回原始 PDF 頁碼。"""
        if not page_map or page_number < 1 or page_number > len(page_map):
            return page_number
        return page_map[page_number - 1]

    def _remap_marker_image_name_to_original(
        self,
        image_name: str,
        page_map: list[int] | None,
    ) -> str:
        """將 subset-local Marker image key 映射回原始頁碼。"""
        if not page_map:
            return image_name

        stem, dot, ext = image_name.rpartition(".")
        if not dot:
            stem = image_name

        parts = stem.split("_")
        if len(parts) < 5 or parts[1] != "page":
            return image_name

        try:
            local_page = int(parts[2]) + 1
        except ValueError:
            return image_name

        original_page = self._remap_page_number(local_page, page_map)
        parts[2] = str(original_page - 1)
        remapped = "_".join(parts)
        return f"{remapped}.{ext}" if dot else remapped

    def _remap_marker_block_reference_to_original(
        self,
        reference: str,
        page_map: list[int] | None,
    ) -> str:
        """將 subset-local Marker block path 映射回原始 PDF 頁碼。"""
        if not page_map or not reference.startswith("/page/"):
            return reference

        parts = reference.split("/")
        if len(parts) < 4:
            return reference

        try:
            local_page = int(parts[2]) + 1
        except ValueError:
            return reference

        original_page = self._remap_page_number(local_page, page_map)
        parts[2] = str(original_page - 1)
        return "/".join(parts)

    @staticmethod
    def _count_pdf_pages(pdf_path: Path) -> int:
        """快速取得 PDF 頁數。"""
        import fitz  # type: ignore

        with fitz.open(str(pdf_path)) as pdf:
            return int(pdf.page_count)

    @staticmethod
    def _count_embedded_image_refs(pdf_path: Path) -> int:
        """估算 PDF 內嵌圖片數量，用於大檔自動策略。"""
        import fitz  # type: ignore

        image_count = 0
        with fitz.open(str(pdf_path)) as pdf:
            for page in pdf:
                image_count += len(page.get_images(full=True))
        return image_count

    def _resolve_parse_strategy(
        self,
        pdf_path: Path,
        *,
        extract_images: bool,
        max_pages_per_chunk: int | None,
    ) -> tuple[int, bool, int | None, dict[str, Any]]:
        """Resolve automatic chunking / figure extraction safeguards."""
        total_pages = self._count_pdf_pages(pdf_path)
        resolved_chunk_size = (
            max_pages_per_chunk
            if max_pages_per_chunk and max_pages_per_chunk > 0
            else None
        )
        auto_chunk_applied = False
        if (
            resolved_chunk_size is None
            and total_pages > AUTO_LARGE_CHUNK_PAGE_THRESHOLD
        ):
            resolved_chunk_size = AUTO_LARGE_CHUNK_SIZE
            auto_chunk_applied = True
        elif (
            resolved_chunk_size is None and total_pages > AUTO_SAFE_CHUNK_PAGE_THRESHOLD
        ):
            resolved_chunk_size = AUTO_SAFE_CHUNK_SIZE
            auto_chunk_applied = True

        resolved_extract_images = extract_images
        detected_image_refs = None
        auto_disable_figures_applied = False
        if extract_images:
            detected_image_refs = self._count_embedded_image_refs(pdf_path)
            if detected_image_refs > AUTO_DISABLE_FIGURES_IMAGE_THRESHOLD:
                resolved_extract_images = False
                auto_disable_figures_applied = True

        metadata: dict[str, Any] = {
            "requested_extract_images": extract_images,
            "requested_max_pages_per_chunk": max_pages_per_chunk or 0,
            "resolved_extract_images": resolved_extract_images,
            "resolved_max_pages_per_chunk": resolved_chunk_size or 0,
            "auto_chunk_applied": auto_chunk_applied,
            "auto_disable_figures_applied": auto_disable_figures_applied,
        }
        if detected_image_refs is not None:
            metadata["detected_image_refs"] = detected_image_refs

        return total_pages, resolved_extract_images, resolved_chunk_size, metadata

    def _apply_page_map(
        self,
        parse_result: MarkerParseResult,
        page_map: list[int],
        *,
        reported_page_count: int | None,
    ) -> MarkerParseResult:
        """將 subset-local parse result 的頁碼映射回原始 PDF。"""
        mapped_blocks = []
        for block in parse_result.blocks:
            metadata = dict(block.metadata)
            block_reference = metadata.get("id")
            if isinstance(block_reference, str):
                metadata["id"] = self._remap_marker_block_reference_to_original(
                    block_reference,
                    page_map,
                )
            mapped_blocks.append(
                MarkerBlock(
                    block_id=block.block_id,
                    block_type=block.block_type,
                    page=self._remap_page_number(block.page, page_map),
                    text=block.text,
                    bbox=list(block.bbox),
                    polygon=list(block.polygon),
                    section_hierarchy=dict(block.section_hierarchy),
                    children=list(block.children),
                    metadata=metadata,
                )
            )
        mapped_toc: list[dict[str, Any]] = []
        for item in parse_result.toc:
            mapped_item = dict(item)
            if isinstance(mapped_item.get("page"), int):
                mapped_item["page"] = self._remap_page_number(
                    mapped_item["page"],
                    page_map,
                )
            mapped_toc.append(mapped_item)
        mapped_images = {
            self._remap_marker_image_name_to_original(image_name, page_map): image_bytes
            for image_name, image_bytes in parse_result.images.items()
        }
        metadata = dict(parse_result.metadata)
        metadata["selected_page_count"] = len(page_map)

        return MarkerParseResult(
            markdown=parse_result.markdown,
            blocks=mapped_blocks,
            toc=mapped_toc,
            images=mapped_images,
            metadata=metadata,
            page_count=reported_page_count or max(page_map),
        )

    def _build_chunk_ranges(
        self,
        pdf_path: Path,
        max_pages_per_chunk: int,
    ) -> tuple[int, list[tuple[int, int]]]:
        """根據頁數上限建立連續 page chunks。"""
        import fitz  # type: ignore

        with fitz.open(str(pdf_path)) as pdf:
            total_pages = pdf.page_count

        if total_pages <= 0:
            return 0, []

        chunk_ranges = []
        for start_page in range(1, total_pages + 1, max_pages_per_chunk):
            end_page = min(start_page + max_pages_per_chunk - 1, total_pages)
            chunk_ranges.append((start_page, end_page))
        return total_pages, chunk_ranges

    def _materialize_chunk_pdfs(
        self,
        pdf_path: Path,
        chunk_ranges: list[tuple[int, int]],
        temp_dir: Path,
    ) -> list[tuple[Path, int]]:
        """將大型 PDF 拆成暫存 chunk PDFs，供 Marker 逐段解析。"""
        import fitz  # type: ignore

        chunk_paths: list[tuple[Path, int]] = []
        with fitz.open(str(pdf_path)) as pdf:
            for index, (start_page, end_page) in enumerate(chunk_ranges, 1):
                chunk_pdf = fitz.open()
                try:
                    chunk_pdf.insert_pdf(
                        pdf,
                        from_page=start_page - 1,
                        to_page=end_page - 1,
                    )
                    chunk_path = (
                        temp_dir / f"chunk_{index:04d}_{start_page}_{end_page}.pdf"
                    )
                    chunk_pdf.save(chunk_path)
                finally:
                    chunk_pdf.close()

                chunk_paths.append((chunk_path, start_page))
        return chunk_paths

    def _offset_blocks(
        self,
        blocks: list[MarkerBlock],
        page_offset: int,
    ) -> list[MarkerBlock]:
        """將 chunk-local block 頁碼平移回原始 PDF。"""
        if page_offset == 0:
            return blocks

        adjusted_blocks: list[MarkerBlock] = []
        for block in blocks:
            metadata = dict(block.metadata)
            block_reference = metadata.get("id")
            if isinstance(block_reference, str):
                metadata["id"] = self._shift_marker_block_reference(
                    block_reference,
                    page_offset,
                )
            adjusted_blocks.append(
                MarkerBlock(
                    block_id=block.block_id,
                    block_type=block.block_type,
                    page=block.page + page_offset,
                    text=block.text,
                    bbox=list(block.bbox),
                    polygon=list(block.polygon),
                    section_hierarchy=dict(block.section_hierarchy),
                    children=list(block.children),
                    metadata=metadata,
                )
            )
        return adjusted_blocks

    def _merge_parse_results(
        self,
        chunk_results: list[MarkerParseResult],
        total_pages: int,
    ) -> MarkerParseResult:
        """合併多個 chunk parse 結果，重建單一文件視圖。"""
        markdown_parts = [
            result.markdown.strip()
            for result in chunk_results
            if result.markdown.strip()
        ]
        merged_blocks: list[MarkerBlock] = []
        merged_images: dict[str, bytes] = {}
        merged_toc: list[dict[str, Any]] = []
        block_counter = 0

        for result in chunk_results:
            merged_toc.extend(result.toc)
            merged_images.update(result.images)
            for block in result.blocks:
                block_counter += 1
                metadata = dict(block.metadata)
                metadata["source_order"] = block_counter
                merged_blocks.append(
                    MarkerBlock(
                        block_id=f"blk_{block_counter:04d}",
                        block_type=block.block_type,
                        page=block.page,
                        text=block.text,
                        bbox=list(block.bbox),
                        polygon=list(block.polygon),
                        section_hierarchy=dict(block.section_hierarchy),
                        children=list(block.children),
                        metadata=metadata,
                    )
                )

        metadata = dict(chunk_results[0].metadata) if chunk_results else {}
        if len(chunk_results) > 1:
            metadata["chunk_count"] = len(chunk_results)

        return MarkerParseResult(
            markdown="\n\n".join(markdown_parts),
            blocks=merged_blocks,
            toc=merged_toc,
            images=merged_images,
            metadata=metadata,
            page_count=total_pages,
        )

    def _parse_single_pdf(
        self,
        converter: Any,
        pdf_path: Path,
        *,
        page_offset: int = 0,
    ) -> MarkerParseResult:
        """解析單一 PDF 或單一 chunk，並在必要時回填原始頁碼。"""
        from marker.output import text_from_rendered  # type: ignore

        rendered = converter(str(pdf_path))

        result = text_from_rendered(rendered)
        markdown_text = result[0] if isinstance(result, tuple) else str(result)

        local_blocks = self._extract_blocks(rendered)
        toc = self._extract_toc(rendered, blocks=local_blocks)
        images = self._extract_images(rendered, local_blocks)
        blocks = self._offset_blocks(local_blocks, page_offset)

        if page_offset:
            for item in toc:
                if isinstance(item.get("page"), int) and item["page"] > 0:
                    item["page"] += page_offset
            images = {
                self._shift_marker_image_name(name, page_offset): data
                for name, data in images.items()
            }

        metadata = self._extract_metadata(rendered)

        return MarkerParseResult(
            markdown=markdown_text,
            blocks=blocks,
            toc=toc,
            images=images,
            metadata=metadata,
            page_count=len(rendered.children) if hasattr(rendered, "children") else 0,
        )

    def parse(
        self,
        pdf_path: Path,
        *,
        extract_images: bool = True,
        max_pages_per_chunk: int | None = None,
        page_map: list[int] | None = None,
        reported_page_count: int | None = None,
    ) -> MarkerParseResult:
        """
        完整解析 PDF 文件。

        Args:
            pdf_path: PDF 檔案路徑
            extract_images: 是否在 render 階段擷取圖片
            max_pages_per_chunk: 每個 Marker chunk 最多頁數；設定後會逐段解析避免 OOM
            page_map: subset-local page index 對應的原始頁碼
            reported_page_count: 要回報給 manifest 的總頁數（通常是原始 PDF 頁數）

        Returns:
            MarkerParseResult 包含 markdown, blocks, toc, images
        """
        self.require_backend_available()
        (
            total_pages,
            resolved_extract_images,
            resolved_chunk_size,
            strategy_metadata,
        ) = self._resolve_parse_strategy(
            pdf_path,
            extract_images=extract_images,
            max_pages_per_chunk=max_pages_per_chunk,
        )
        converter = self._get_converter(extract_images=resolved_extract_images)

        if resolved_chunk_size is None or resolved_chunk_size <= 0:
            parse_result = self._parse_single_pdf(converter, pdf_path)
        else:
            _observed_pages, chunk_ranges = self._build_chunk_ranges(
                pdf_path,
                resolved_chunk_size,
            )
            if len(chunk_ranges) <= 1:
                parse_result = self._parse_single_pdf(converter, pdf_path)
            else:
                chunk_results: list[MarkerParseResult] = []
                with tempfile.TemporaryDirectory(
                    prefix="marker_chunks_"
                ) as temp_dir_name:
                    chunk_paths = self._materialize_chunk_pdfs(
                        pdf_path,
                        chunk_ranges,
                        Path(temp_dir_name),
                    )
                    for chunk_path, start_page in chunk_paths:
                        chunk_results.append(
                            self._parse_single_pdf(
                                converter,
                                chunk_path,
                                page_offset=start_page - 1,
                            )
                        )

                parse_result = self._merge_parse_results(chunk_results, total_pages)

        if page_map:
            parse_result = self._apply_page_map(
                parse_result,
                page_map,
                reported_page_count=reported_page_count,
            )

        parse_result.metadata.update(strategy_metadata)
        return parse_result

    def _extract_blocks(self, rendered: Any) -> list[MarkerBlock]:
        """從 rendered 結果提取結構化 blocks。"""
        blocks: list[MarkerBlock] = []
        block_counter = 0

        def traverse_node(
            node: Any, page_num: int = 1, section_hierarchy: dict | None = None
        ) -> None:
            nonlocal block_counter
            section_hierarchy = section_hierarchy or {}

            # 取得 block type
            block_type = getattr(node, "block_type", None) or type(node).__name__

            # 取得文字內容
            text = ""
            if hasattr(node, "text"):
                text = node.text or ""
            elif hasattr(node, "raw_text"):
                text = (
                    node.raw_text() if callable(node.raw_text) else str(node.raw_text)
                )

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
                    "id": self._stringify_marker_block_id(getattr(node, "id", None)),
                    "level": getattr(node, "level", None),
                    "source_order": block_counter,
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

    def _extract_toc(
        self,
        rendered: Any,
        *,
        blocks: list[MarkerBlock] | None = None,
    ) -> list[dict[str, Any]]:
        """提取目錄結構。"""
        toc = []

        if hasattr(rendered, "toc") and rendered.toc:
            for item in rendered.toc:
                toc.append(
                    {
                        "title": getattr(item, "title", str(item)),
                        "page": getattr(item, "page", 0),
                        "level": getattr(item, "level", 1),
                    }
                )
        else:
            # 從 SectionHeader blocks 建構 TOC
            for block in blocks or self._extract_blocks(rendered):
                if block.block_type == "SectionHeader" and block.text:
                    toc.append(
                        {
                            "title": block.text.strip(),
                            "page": block.page,
                            "level": block.metadata.get("level", 1) or 1,
                        }
                    )

        return toc

    def _extract_images(
        self,
        rendered: Any,
        blocks: list[MarkerBlock],
    ) -> dict[str, bytes]:
        """提取與 Figure/Picture block 對應的圖片。"""
        images: dict[str, bytes] = {}
        allowed_keys = {
            self._normalize_marker_image_key(block.metadata.get("id") or "")
            for block in self._select_image_blocks(blocks)
            if block.metadata.get("id")
        }

        if not allowed_keys:
            return images

        if hasattr(rendered, "images"):
            # Marker 的 images 是 dict[str, PIL.Image]
            for name, img in rendered.images.items():
                if self._normalize_marker_image_key(name) not in allowed_keys:
                    continue
                try:
                    import io

                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    images[name] = buf.getvalue()
                except Exception:  # noqa: S112 — image extraction failure is non-critical
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
        *,
        doc_id: str | None = None,
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

        resolved_doc_id = (
            doc_id or DocId.generate(pdf_path.stem, str(pdf_path.absolute())).value
        )

        # 確保輸出目錄存在
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "figures"
        images_dir.mkdir(exist_ok=True)

        # 儲存 markdown
        markdown_path = output_dir / "content.md"
        markdown_path.write_text(parse_result.markdown, encoding="utf-8")
        line_span_index = annotate_marker_blocks(
            parse_result.markdown,
            parse_result.blocks,
        )

        # 儲存圖片並建立 FigureAsset
        figures: list[FigureAsset] = []

        # Collect all Figure blocks for 1:1 matching
        figure_blocks = [
            block for block in parse_result.blocks if block.block_type == "Figure"
        ]

        for idx, (img_name, img_bytes) in enumerate(parse_result.images.items(), 1):
            ext = img_name.split(".")[-1] if "." in img_name else "png"
            fig_path = images_dir / f"fig_{idx}.{ext}"
            fig_path.write_bytes(img_bytes)
            matched = figure_blocks[idx - 1] if idx - 1 < len(figure_blocks) else None

            # Match corresponding Figure block by index
            page = 1
            caption = ""
            if matched is not None:
                page = matched.page
                caption = matched.metadata.get("caption", "")

            # Read actual image dimensions
            width, height = 0, 0
            try:
                import io

                from PIL import Image

                img = Image.open(io.BytesIO(img_bytes))
                width, height = img.size
            except Exception:  # noqa: S110 — PIL image size read failure is non-critical
                pass

            figures.append(
                FigureAsset(
                    id=f"fig_{idx}",
                    page=page,
                    path=str(fig_path),
                    ext=ext,
                    caption=caption,
                    width=width,
                    height=height,
                    figure_type="",
                    source="marker",
                    source_block_id=matched.block_id if matched else "",
                    source_order=_coerce_metadata_int(matched.metadata, "source_order")
                    if matched
                    else 0,
                    line_start=_coerce_metadata_int(matched.metadata, "line_start")
                    if matched and isinstance(matched.metadata.get("line_start"), int)
                    else None,
                    line_end=_coerce_metadata_int(matched.metadata, "line_end")
                    if matched and isinstance(matched.metadata.get("line_end"), int)
                    else None,
                    line_source=str(matched.metadata.get("line_match_strategy") or "")
                    if matched
                    else "",
                )
            )

        # 建立 SectionAsset
        sections: list[SectionAsset] = []
        for idx, toc_item in enumerate(parse_result.toc, 1):
            section_span = line_span_index.find_section_span(
                toc_item.get("title", ""),
                page_hint=toc_item.get("page", 0) or None,
            )
            sections.append(
                SectionAsset(
                    id=f"sec_{idx}",
                    title=toc_item.get("title", ""),
                    level=toc_item.get("level", 1),
                    page=toc_item.get("page", 0),
                    start_line=section_span.start_line if section_span else 0,
                    end_line=section_span.end_line if section_span else 0,
                    preview=(
                        line_span_index.extract_preview(
                            section_span.start_line,
                            section_span.end_line,
                        )
                        if section_span
                        else ""
                    ),
                )
            )

        # 建立 TableAsset（從 blocks 中提取）
        tables: list[TableAsset] = []
        table_idx = 0
        for block in parse_result.blocks:
            if block.block_type == "Table":
                table_idx += 1
                # Parse row/col counts from markdown
                row_count, col_count = 0, 0
                if block.text:
                    lines = [
                        line.strip()
                        for line in block.text.strip().splitlines()
                        if line.strip()
                    ]
                    data_lines = [
                        line for line in lines if not all(c in "-| :" for c in line)
                    ]
                    row_count = len(data_lines)
                    if data_lines:
                        col_count = max(data_lines[0].count("|") - 1, 0)
                tables.append(
                    TableAsset(
                        id=f"tab_{table_idx}",
                        page=block.page,
                        caption="",
                        preview=block.text[:100] if block.text else "",
                        markdown=block.text,
                        row_count=row_count,
                        col_count=col_count,
                        has_header=True,
                        source="marker",
                        source_block_id=block.block_id,
                        source_order=_coerce_metadata_int(
                            block.metadata, "source_order"
                        ),
                        line_start=_coerce_metadata_int(block.metadata, "line_start")
                        if isinstance(block.metadata.get("line_start"), int)
                        else None,
                        line_end=_coerce_metadata_int(block.metadata, "line_end")
                        if isinstance(block.metadata.get("line_end"), int)
                        else None,
                        line_source=str(
                            block.metadata.get("line_match_strategy") or ""
                        ),
                    )
                )

        apply_asset_line_spans(
            line_span_index,
            figures,
            tables,
            blocks=parse_result.blocks,
            sections=sections,
        )

        # 建立 DocumentAssets
        assets = DocumentAssets(
            tables=tables,
            figures=figures,
            sections=sections,
        )

        # 建立 DocumentManifest
        manifest = DocumentManifest(
            doc_id=resolved_doc_id,
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
                "text": b.text or "",
                "text_preview": (b.text[:500] if b.text else ""),
                "bbox": b.bbox,
                "section_hierarchy": b.section_hierarchy,
                "metadata": b.metadata,
            }
            for b in parse_result.blocks
        ]
        blocks_path = output_dir / "blocks.json"
        blocks_path.write_text(
            json.dumps(blocks_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return manifest

    def extract_to_manifest(
        self,
        pdf_path: Path,
        output_dir: Path,
        *,
        extract_images: bool = True,
        max_pages_per_chunk: int | None = None,
        page_map: list[int] | None = None,
        reported_page_count: int | None = None,
        doc_id: str | None = None,
    ) -> DocumentManifest:
        """
        一站式 API：解析 PDF 並輸出 DocumentManifest。

        Args:
            pdf_path: PDF 檔案路徑
            output_dir: 輸出目錄
            extract_images: 是否輸出圖片 assets
            max_pages_per_chunk: 每個 chunk 的最大頁數

        Returns:
            DocumentManifest
        """
        result = self.parse(
            pdf_path,
            extract_images=extract_images,
            max_pages_per_chunk=max_pages_per_chunk,
            page_map=page_map,
            reported_page_count=reported_page_count,
        )
        return self.convert_to_manifest(result, pdf_path, output_dir, doc_id=doc_id)
