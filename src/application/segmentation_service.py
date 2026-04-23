"""Application service for unified document segmentation export."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.application.output_paths import resolve_document_output_path
from src.domain.entities import DocumentManifest, FigureAsset, TableAsset
from src.domain.line_spans import annotate_marker_blocks
from src.domain.reading_order import ReadingOrderPolicy
from src.domain.segmentation import DocumentSegment, DocumentSegmentation

if TYPE_CHECKING:
    from pathlib import Path

    from src.domain.repositories import DocumentRepository


class SegmentationService:
    """Build a normalized segmentation schema from manifest and block artifacts."""

    def __init__(self, repository: DocumentRepository):
        self.repository = repository
        self.reading_order_policy = ReadingOrderPolicy()

    async def export_document_segmentation(
        self,
        doc_id: str,
        page: int | None = None,
        limit: int | None = None,
    ) -> DocumentSegmentation:
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            raise ValueError(f"Document not found: {doc_id}")

        doc_dir = self.repository.get_doc_dir(doc_id)
        markdown = self.repository.load_markdown(doc_id) or ""
        blocks = self.repository.load_blocks(doc_id)
        if not isinstance(blocks, list):
            blocks_path = doc_dir / "blocks.json"
            blocks = (
                json.loads(blocks_path.read_text(encoding="utf-8"))
                if blocks_path.exists()
                else None
            )

        if blocks is not None:
            if markdown and any(
                not isinstance((block.get("metadata") or {}).get("line_start"), int)
                for block in blocks
            ):
                annotate_marker_blocks(markdown, blocks)
                self.repository.save_blocks(doc_id, blocks)
            segments = self._segments_from_blocks(manifest, blocks)
            backend = "marker"
        else:
            segments = self._segments_from_manifest(manifest)
            backend = self._infer_backend(manifest)

        if page is not None:
            segments = [segment for segment in segments if segment.page_number == page]

        if limit is not None:
            segments = segments[:limit]

        return DocumentSegmentation(
            doc_id=manifest.doc_id,
            filename=manifest.filename,
            title=manifest.title,
            page_count=manifest.page_count,
            source_backend=backend,
            reading_order_policy=self.reading_order_policy.version,
            segments=segments,
        )

    async def save_document_segmentation(
        self,
        doc_id: str,
        output_path: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Path:
        segmentation = await self.export_document_segmentation(
            doc_id,
            page=page,
            limit=limit,
        )
        doc_dir = self.repository.get_doc_dir(doc_id)
        target = resolve_document_output_path(
            doc_dir,
            output_path,
            default_name="segmentation.json",
            allowed_suffixes={".json"},
        )
        target.write_text(
            segmentation.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )
        return target

    def _segments_from_blocks(
        self,
        manifest: DocumentManifest,
        blocks: list[dict[str, object]],
    ) -> list[DocumentSegment]:
        ordered_blocks = list(enumerate(blocks))
        used_figure_ids: set[str] = set()
        used_table_ids: set[str] = set()

        segments: list[DocumentSegment] = []
        for index, block in ordered_blocks:
            page_number = self._coerce_int(block.get("page"), default=1)
            segment_type = self._normalize_segment_type(
                str(block.get("block_type") or "Text")
            )
            asset_id = ""
            if segment_type == "Picture":
                asset_id = self._match_asset_id(
                    block,
                    manifest.assets.figures,
                    used_figure_ids,
                )
            elif segment_type == "Table":
                asset_id = self._match_asset_id(
                    block,
                    manifest.assets.tables,
                    used_table_ids,
                )
            elif segment_type == "Section header":
                asset_id = self._match_section_asset(
                    manifest, str(block.get("text") or ""), page_number
                )

            left, top, width, height = self._bbox_to_rect(block.get("bbox"))
            line_start, line_end = self._resolve_block_lines(
                manifest,
                block,
                segment_type,
                asset_id,
            )
            segments.append(
                DocumentSegment(
                    segment_id=str(block.get("block_id") or f"segment_{index + 1}"),
                    segment_type=segment_type,
                    page_number=page_number,
                    left=left,
                    top=top,
                    width=width,
                    height=height,
                    text=str(block.get("text") or ""),
                    asset_id=asset_id,
                    reading_order=0,
                    line_start=line_start,
                    line_end=line_end,
                    section_hierarchy=self._section_path(
                        block.get("section_hierarchy")
                    ),
                    source_backend="marker",
                    metadata={
                        "original_block_type": str(block.get("block_type") or ""),
                        "source_block_id": str(block.get("block_id") or ""),
                        "source_order": self._block_source_order(block, index),
                    },
                )
            )
        return self.reading_order_policy.assign(segments)

    def _segments_from_manifest(
        self,
        manifest: DocumentManifest,
    ) -> list[DocumentSegment]:
        segments: list[DocumentSegment] = []

        source_order = 0
        for section in sorted(
            manifest.assets.sections, key=lambda item: (item.page, item.level, item.id)
        ):
            source_order += 1
            segments.append(
                DocumentSegment(
                    segment_id=section.id,
                    segment_type="Section header",
                    page_number=section.page or 1,
                    text=section.title,
                    asset_id=section.id,
                    reading_order=0,
                    line_start=section.start_line,
                    line_end=section.end_line,
                    section_hierarchy=[section.title],
                    source_backend=self._infer_backend(manifest),
                    metadata={"level": section.level, "source_order": source_order},
                )
            )

        for table in sorted(
            manifest.assets.tables,
            key=lambda item: (item.page, self._asset_sort_order(item), item.id),
        ):
            source_order = max(source_order + 1, self._asset_sort_order(table))
            segments.append(
                DocumentSegment(
                    segment_id=table.id,
                    segment_type="Table",
                    page_number=table.page or 1,
                    text=table.preview or table.caption,
                    asset_id=table.id,
                    reading_order=0,
                    line_start=table.line_start,
                    line_end=table.line_end,
                    source_backend=table.source,
                    metadata={
                        "rows": table.row_count,
                        "cols": table.col_count,
                        "source_order": source_order,
                        "source_block_id": table.source_block_id,
                        "line_source": table.line_source,
                    },
                )
            )

        for figure in sorted(
            manifest.assets.figures,
            key=lambda item: (item.page, self._asset_sort_order(item), item.id),
        ):
            source_order = max(source_order + 1, self._asset_sort_order(figure))
            segments.append(
                DocumentSegment(
                    segment_id=figure.id,
                    segment_type="Picture",
                    page_number=figure.page or 1,
                    text=figure.caption,
                    asset_id=figure.id,
                    reading_order=0,
                    line_start=figure.line_start,
                    line_end=figure.line_end,
                    source_backend=figure.source,
                    metadata={
                        "width": figure.width,
                        "height": figure.height,
                        "source_order": source_order,
                        "source_block_id": figure.source_block_id,
                        "line_source": figure.line_source,
                    },
                )
            )

        return self.reading_order_policy.assign(segments)

    def _match_asset_id(
        self,
        block: dict[str, object],
        assets: list[FigureAsset] | list[TableAsset],
        used_asset_ids: set[str],
    ) -> str:
        block_id = str(block.get("block_id") or "")
        page_number = self._coerce_int(block.get("page"), default=1)
        source_order = self._block_source_order(block, 0)
        normalized_text = _normalize_for_matching(str(block.get("text") or ""))

        for asset in assets:
            if asset.id in used_asset_ids:
                continue
            if getattr(asset, "source_block_id", "") == block_id:
                used_asset_ids.add(asset.id)
                return asset.id

        same_page_assets = [
            asset
            for asset in assets
            if asset.id not in used_asset_ids and asset.page == page_number
        ]
        if not same_page_assets:
            return ""

        for asset in same_page_assets:
            if self._asset_sort_order(asset) and self._asset_sort_order(asset) == int(
                source_order
            ):
                used_asset_ids.add(asset.id)
                return asset.id

        for asset in same_page_assets:
            asset_text = self._asset_match_text(asset)
            if asset_text and asset_text == normalized_text:
                used_asset_ids.add(asset.id)
                return asset.id

        best_asset = min(
            same_page_assets,
            key=lambda asset: (
                abs(self._asset_sort_order(asset) - source_order)
                if self._asset_sort_order(asset)
                else float("inf"),
                asset.id,
            ),
        )
        used_asset_ids.add(best_asset.id)
        return best_asset.id

    @staticmethod
    def _match_section_asset(
        manifest: DocumentManifest,
        text: str,
        page_number: int,
    ) -> str:
        normalized = text.strip().lower()
        for section in manifest.assets.sections:
            if (
                section.page == page_number
                and section.title.strip().lower() == normalized
            ):
                return section.id
        return ""

    @staticmethod
    def _asset_sort_order(asset: FigureAsset | TableAsset) -> int:
        raw_value = getattr(asset, "source_order", 0)
        return int(raw_value or 0)

    @staticmethod
    def _asset_match_text(asset: FigureAsset | TableAsset) -> str:
        if isinstance(asset, TableAsset):
            return _normalize_for_matching(
                asset.markdown or asset.preview or asset.caption
            )
        return _normalize_for_matching(asset.caption)

    @staticmethod
    def _block_source_order(block: dict[str, object], index: int) -> float:
        metadata = block.get("metadata")
        if isinstance(metadata, dict):
            source_order = metadata.get("source_order")
            if isinstance(source_order, (int, float)):
                return float(source_order)
        return float(index + 1)

    @staticmethod
    def _resolve_block_lines(
        manifest: DocumentManifest,
        block: dict[str, object],
        segment_type: str,
        asset_id: str,
    ) -> tuple[int | None, int | None]:
        metadata = SegmentationService._metadata_dict(block.get("metadata"))
        line_start = metadata.get("line_start")
        line_end = metadata.get("line_end")
        if isinstance(line_start, int) and isinstance(line_end, int):
            return (line_start, line_end)
        if segment_type == "Section header" and asset_id:
            section = manifest.assets.find_section(asset_id)
            if section is not None and section.start_line >= 0:
                return (section.start_line, section.end_line)
        if segment_type == "Table" and asset_id:
            table = manifest.assets.find_table(asset_id)
            if table is not None:
                return (table.line_start, table.line_end)
        if segment_type == "Picture" and asset_id:
            figure = manifest.assets.find_figure(asset_id)
            if figure is not None:
                return (figure.line_start, figure.line_end)
        return (None, None)

    @staticmethod
    def _bbox_to_rect(
        bbox: object,
    ) -> tuple[float | None, float | None, float | None, float | None]:
        if isinstance(bbox, list) and len(bbox) == 4:
            left = float(bbox[0])
            top = float(bbox[1])
            right = float(bbox[2])
            bottom = float(bbox[3])
            return (left, top, right - left, bottom - top)
        return (None, None, None, None)

    @staticmethod
    def _section_path(section_hierarchy: object) -> list[str]:
        if not isinstance(section_hierarchy, dict):
            return []
        return [
            str(title)
            for _, title in sorted(section_hierarchy.items(), key=lambda item: item[0])
            if str(title).strip()
        ]

    @staticmethod
    def _normalize_segment_type(block_type: str) -> str:
        normalized = block_type.strip().lower()
        mapping = {
            "caption": "Caption",
            "figure": "Picture",
            "picture": "Picture",
            "formula": "Formula",
            "equation": "Formula",
            "listitem": "List item",
            "list item": "List item",
            "footnote": "Footnote",
            "pagefooter": "Page footer",
            "page footer": "Page footer",
            "pageheader": "Page header",
            "page header": "Page header",
            "sectionheader": "Section header",
            "section header": "Section header",
            "table": "Table",
            "title": "Title",
            "text": "Text",
            "paragraph": "Text",
        }
        return mapping.get(normalized, block_type or "Text")

    @staticmethod
    def _infer_backend(manifest: DocumentManifest) -> str:
        if any(figure.source == "marker" for figure in manifest.assets.figures):
            return "marker"
        if any(table.source == "marker" for table in manifest.assets.tables):
            return "marker"
        return "pymupdf"

    @staticmethod
    def _metadata_dict(value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _coerce_int(value: object, *, default: int = 0) -> int:
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


def _normalize_for_matching(text: str) -> str:
    return " ".join(text.replace("`", " ").split()).strip().lower()
