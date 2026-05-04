"""Unit tests for explicit reading order policy and segmentation integration."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from src.application.segmentation_service import SegmentationService
from src.domain.entities import (
    DocumentAssets,
    DocumentManifest,
    FigureAsset,
    SectionAsset,
    TableAsset,
)
from src.domain.reading_order import ReadingOrderPolicy
from src.domain.segmentation import DocumentSegment


class TestReadingOrderPolicy:
    """Tests for the explicit reading order policy."""

    def test_caption_is_anchored_after_nearby_picture(self) -> None:
        policy = ReadingOrderPolicy()
        segments = [
            DocumentSegment(
                segment_id="fig_1",
                segment_type="Picture",
                page_number=1,
                left=100,
                top=100,
                width=200,
                height=120,
                metadata={"source_order": 10},
            ),
            DocumentSegment(
                segment_id="cap_1",
                segment_type="Caption",
                page_number=1,
                left=110,
                top=240,
                width=180,
                height=20,
                text="Figure 1. Example",
                metadata={"source_order": 5},
            ),
        ]

        ordered = policy.assign(segments)

        assert ordered[0].segment_id == "fig_1"
        assert ordered[1].segment_id == "cap_1"
        assert (
            ordered[1].metadata["reading_order_reason"] == "caption-near-picture:fig_1"
        )

    def test_footnote_moves_to_page_end(self) -> None:
        policy = ReadingOrderPolicy()
        segments = [
            DocumentSegment(
                segment_id="txt_1",
                segment_type="Text",
                page_number=1,
                top=120,
                left=90,
                width=300,
                height=40,
                metadata={"source_order": 2},
            ),
            DocumentSegment(
                segment_id="fn_1",
                segment_type="Footnote",
                page_number=1,
                top=760,
                left=80,
                width=320,
                height=30,
                metadata={"source_order": 1},
            ),
        ]

        ordered = policy.assign(segments)

        assert ordered[0].segment_id == "txt_1"
        assert ordered[1].segment_id == "fn_1"
        assert ordered[1].metadata["reading_order_reason"] == "bottom-of-page"


class TestSegmentationServiceReadingOrder:
    """Integration tests for segmentation export with reading order policy."""

    async def test_export_document_segmentation_applies_policy_to_blocks(
        self, temp_dir
    ) -> None:
        manifest = DocumentManifest(
            doc_id="doc_test",
            filename="test.pdf",
            title="Test",
            page_count=1,
            markdown_path="workspace/test.md",
            assets=DocumentAssets(
                figures=[
                    FigureAsset(
                        id="fig_1",
                        page=1,
                        path="workspace/fig.png",
                        ext="png",
                        caption="Figure 1",
                        width=100,
                        height=100,
                        source="marker",
                    )
                ],
                tables=[],
                sections=[],
            ),
        )

        (temp_dir / "doc_test_full.md").write_text(
            "Some intro\n\nFigure 1. A caption\n",
            encoding="utf-8",
        )

        blocks = [
            {
                "block_id": "blk_pic",
                "block_type": "Figure",
                "page": 1,
                "text": "",
                "bbox": [100, 100, 280, 220],
                "section_hierarchy": {},
                "metadata": {"source_order": 9},
            },
            {
                "block_id": "blk_cap",
                "block_type": "Caption",
                "page": 1,
                "text": "Figure 1. A caption",
                "bbox": [110, 230, 290, 255],
                "section_hierarchy": {},
                "metadata": {"source_order": 3},
            },
        ]

        (temp_dir / "blocks.json").write_text(json.dumps(blocks), encoding="utf-8")

        repository = MagicMock()
        repository.load_manifest.return_value = manifest
        repository.get_doc_dir.return_value = temp_dir
        repository.load_markdown.return_value = (
            temp_dir / "doc_test_full.md"
        ).read_text(encoding="utf-8")

        service = SegmentationService(repository=repository)
        segmentation = await service.export_document_segmentation("doc_test")

        assert segmentation.reading_order_policy == "explicit-reading-order-v1"
        assert [segment.segment_id for segment in segmentation.segments] == [
            "blk_pic",
            "blk_cap",
        ]
        assert (
            segmentation.segments[1].metadata["reading_order_reason"]
            == "caption-near-picture:blk_pic"
        )
        assert segmentation.segments[1].line_start is not None

    async def test_blocks_metadata_can_identify_pymupdf_source_backend(
        self, temp_dir
    ) -> None:
        manifest = DocumentManifest(
            doc_id="doc_test",
            filename="test.pdf",
            title="Test",
            page_count=1,
            markdown_path="workspace/test.md",
            assets=DocumentAssets(figures=[], tables=[], sections=[]),
        )
        blocks = [
            {
                "block_id": "md_txt_1",
                "block_type": "Text",
                "page": 1,
                "text": "PyMuPDF paragraph",
                "bbox": [],
                "section_hierarchy": {},
                "metadata": {
                    "line_start": 0,
                    "line_end": 1,
                    "source_backend": "pymupdf",
                    "source_order": 1,
                },
            }
        ]
        (temp_dir / "blocks.json").write_text(json.dumps(blocks), encoding="utf-8")

        repository = MagicMock()
        repository.load_manifest.return_value = manifest
        repository.get_doc_dir.return_value = temp_dir
        repository.load_markdown.return_value = "PyMuPDF paragraph\n"

        service = SegmentationService(repository=repository)
        segmentation = await service.export_document_segmentation("doc_test")

        assert segmentation.source_backend == "pymupdf"
        assert segmentation.segments[0].source_backend == "pymupdf"

    async def test_manifest_fallback_segments_also_get_policy(self, temp_dir) -> None:
        manifest = DocumentManifest(
            doc_id="doc_test",
            filename="test.pdf",
            title="Test",
            page_count=2,
            markdown_path="workspace/test.md",
            assets=DocumentAssets(
                sections=[
                    SectionAsset(
                        id="sec_intro",
                        title="Introduction",
                        level=1,
                        page=1,
                        start_line=1,
                        end_line=10,
                        preview="",
                    )
                ],
                tables=[
                    TableAsset(
                        id="tab_1",
                        page=2,
                        caption="Table 1",
                        preview="abc",
                        markdown="|A|",
                        row_count=1,
                        col_count=1,
                        source="pymupdf",
                    )
                ],
                figures=[],
            ),
        )

        repository = MagicMock()
        repository.load_manifest.return_value = manifest
        repository.get_doc_dir.return_value = temp_dir
        repository.load_markdown.return_value = "# Introduction\nBody\n"

        service = SegmentationService(repository=repository)
        segmentation = await service.export_document_segmentation("doc_test")

        assert segmentation.reading_order_policy == "explicit-reading-order-v1"
        assert all(
            segment.metadata["reading_order_policy"] == "explicit-reading-order-v1"
            for segment in segmentation.segments
        )
        section_segment = next(
            segment
            for segment in segmentation.segments
            if segment.segment_id == "sec_intro"
        )
        assert section_segment.line_start == 1
        assert section_segment.line_end == 10

    async def test_manifest_table_segment_keeps_line_anchor(self, temp_dir) -> None:
        manifest = DocumentManifest(
            doc_id="doc_test",
            filename="test.pdf",
            title="Test",
            page_count=1,
            markdown_path="workspace/test.md",
            assets=DocumentAssets(
                tables=[
                    TableAsset(
                        id="tab_1",
                        page=1,
                        caption="",
                        preview="| A | B |",
                        markdown="| A | B |\n| --- | --- |\n| 1 | 2 |",
                        row_count=2,
                        col_count=2,
                        line_start=2,
                        line_end=5,
                        line_source="markdown-table",
                    )
                ],
                figures=[],
                sections=[],
            ),
        )
        (temp_dir / "doc_test_full.md").write_text(
            "# Title\n\n| A | B |\n| --- | --- |\n| 1 | 2 |\n",
            encoding="utf-8",
        )

        repository = MagicMock()
        repository.load_manifest.return_value = manifest
        repository.get_doc_dir.return_value = temp_dir
        repository.load_markdown.return_value = (
            temp_dir / "doc_test_full.md"
        ).read_text(encoding="utf-8")

        service = SegmentationService(repository=repository)
        segmentation = await service.export_document_segmentation("doc_test")

        table_segment = next(
            segment
            for segment in segmentation.segments
            if segment.segment_id == "tab_1"
        )
        assert table_segment.line_start == 2
        assert table_segment.line_end is not None

    async def test_block_matching_prefers_source_block_identity_over_same_page_order(
        self, temp_dir
    ) -> None:
        manifest = DocumentManifest(
            doc_id="doc_test",
            filename="test.pdf",
            title="Test",
            page_count=1,
            markdown_path="workspace/test.md",
            assets=DocumentAssets(
                figures=[
                    FigureAsset(
                        id="fig_1",
                        page=1,
                        path="workspace/fig1.png",
                        ext="png",
                        caption="Figure A",
                        width=100,
                        height=100,
                        source="marker",
                        source_block_id="blk_pic_b",
                        source_order=20,
                    ),
                    FigureAsset(
                        id="fig_2",
                        page=1,
                        path="workspace/fig2.png",
                        ext="png",
                        caption="Figure B",
                        width=100,
                        height=100,
                        source="marker",
                        source_block_id="blk_pic_a",
                        source_order=10,
                    ),
                ],
                tables=[],
                sections=[],
            ),
        )
        blocks = [
            {
                "block_id": "blk_pic_a",
                "block_type": "Figure",
                "page": 1,
                "text": "",
                "bbox": [10, 10, 20, 20],
                "section_hierarchy": {},
                "metadata": {"source_order": 10},
            },
            {
                "block_id": "blk_pic_b",
                "block_type": "Figure",
                "page": 1,
                "text": "",
                "bbox": [30, 30, 40, 40],
                "section_hierarchy": {},
                "metadata": {"source_order": 20},
            },
        ]
        (temp_dir / "blocks.json").write_text(json.dumps(blocks), encoding="utf-8")

        repository = MagicMock()
        repository.load_manifest.return_value = manifest
        repository.get_doc_dir.return_value = temp_dir
        repository.load_markdown.return_value = ""

        service = SegmentationService(repository=repository)
        segmentation = await service.export_document_segmentation("doc_test")

        asset_ids = [segment.asset_id for segment in segmentation.segments]
        assert asset_ids == ["fig_2", "fig_1"]
