"""
Unit Tests for Domain Layer - Entities

Tests for DocumentManifest, DocumentAssets, and related entities.
"""

from __future__ import annotations

import pytest

from src.domain.entities import (
    DocumentAssets,
    DocumentManifest,
    FetchResult,
    FigureAsset,
    IngestResult,
    SectionAsset,
    TableAsset,
)
from src.domain.value_objects import AssetType


class TestTableAsset:
    """Tests for TableAsset entity."""

    def test_create_table_asset(self):
        """Test creating a TableAsset."""
        table = TableAsset(
            id="tab_1",
            page=2,
            caption="Table 1: Patient Demographics",
            preview="Age | Gender | BMI...",
            markdown="| Age | Gender | BMI |\n|-----|--------|-----|\n| 45  | M      | 25  |",
            row_count=2,
            col_count=3,
        )

        assert table.id == "tab_1"
        assert table.page == 2
        assert table.row_count == 2


class TestFigureAsset:
    """Tests for FigureAsset entity."""

    def test_create_figure_asset(self):
        """Test creating a FigureAsset."""
        figure = FigureAsset(
            id="fig_1_1",
            page=5,
            path="./data/doc_test/images/fig_1_1.png",
            ext="png",
            caption="Figure 1: Test",
            width=800,
            height=600,
        )

        assert figure.id == "fig_1_1"
        assert figure.page == 5
        assert figure.ext == "png"

    def test_get_media_type(self):
        """Test getting media type from figure."""
        figure = FigureAsset(
            id="fig_1_1",
            page=1,
            path="test.png",
            ext="png",
            caption="",
            width=100,
            height=100,
        )

        media_type = figure.get_media_type()
        assert media_type.value == "image/png"

    def test_to_base64_file_not_found(self):
        """Test that to_base64 raises error when file not found."""
        figure = FigureAsset(
            id="fig_1_1",
            page=1,
            path="nonexistent.png",
            ext="png",
            caption="",
            width=100,
            height=100,
        )

        with pytest.raises(FileNotFoundError):
            figure.to_base64()


class TestSectionAsset:
    """Tests for SectionAsset entity."""

    def test_create_section_asset(self):
        """Test creating a SectionAsset."""
        section = SectionAsset(
            id="sec_introduction",
            title="Introduction",
            level=1,
            page=1,
            start_line=10,
            end_line=50,
            preview="This study examines...",
        )

        assert section.id == "sec_introduction"
        assert section.level == 1


class TestDocumentAssets:
    """Tests for DocumentAssets aggregate."""

    @pytest.fixture
    def assets(self) -> DocumentAssets:
        """Create sample assets for testing."""
        return DocumentAssets(
            tables=[
                TableAsset(id="tab_1", page=2, caption="", preview="", markdown="| A | B |", row_count=2, col_count=2),
                TableAsset(id="tab_2", page=4, caption="", preview="", markdown="| C | D |", row_count=3, col_count=2),
            ],
            figures=[
                FigureAsset(id="fig_1_1", page=3, path="fig1.png", ext="png", caption="", width=100, height=100),
            ],
            sections=[
                SectionAsset(id="sec_intro", title="Introduction", level=1, page=1, start_line=0, end_line=20, preview=""),
                SectionAsset(id="sec_methods", title="Methods", level=1, page=2, start_line=21, end_line=50, preview=""),
            ],
        )

    def test_find_table(self, assets: DocumentAssets):
        """Test finding a table by ID."""
        table = assets.find_table("tab_1")
        assert table is not None
        assert table.page == 2

        assert assets.find_table("tab_999") is None

    def test_find_figure(self, assets: DocumentAssets):
        """Test finding a figure by ID."""
        figure = assets.find_figure("fig_1_1")
        assert figure is not None
        assert figure.page == 3

        assert assets.find_figure("fig_999") is None

    def test_find_section_by_id(self, assets: DocumentAssets):
        """Test finding a section by ID."""
        section = assets.find_section("sec_intro")
        assert section is not None
        assert section.title == "Introduction"

    def test_find_section_by_title(self, assets: DocumentAssets):
        """Test finding a section by title (case-insensitive)."""
        section = assets.find_section("METHODS")
        assert section is not None
        assert section.id == "sec_methods"

    def test_get_summary(self, assets: DocumentAssets):
        """Test getting asset counts."""
        summary = assets.get_summary()
        assert summary["tables"] == 2
        assert summary["figures"] == 1
        assert summary["sections"] == 2


class TestDocumentManifest:
    """Tests for DocumentManifest aggregate root."""

    def test_create_manifest(self, sample_manifest_dict):
        """Test creating a manifest from dict."""
        manifest = DocumentManifest.model_validate(sample_manifest_dict)

        assert manifest.doc_id == "doc_test_abc123"
        assert manifest.title == "Test Document Title"
        assert manifest.page_count == 3

    def test_manifest_asset_summary(self, sample_manifest_dict):
        """Test getting asset summary from manifest."""
        manifest = DocumentManifest.model_validate(sample_manifest_dict)

        summary = manifest.get_asset_summary()
        assert summary["tables"] == 1
        assert summary["sections"] == 2


class TestIngestResult:
    """Tests for IngestResult."""

    def test_success_result(self):
        """Test successful ingest result."""
        result = IngestResult(
            doc_id="doc_test_abc123",
            filename="test.pdf",
            title="Test Document",
            success=True,
            pages_processed=10,
            tables_found=3,
            figures_found=5,
            sections_found=8,
            processing_time_seconds=2.5,
        )

        assert result.success
        assert result.error is None

    def test_failure_result(self):
        """Test failed ingest result."""
        result = IngestResult(
            doc_id="",
            filename="missing.pdf",
            success=False,
            error="File not found",
        )

        assert not result.success
        assert result.error == "File not found"


class TestFetchResult:
    """Tests for FetchResult."""

    def test_text_fetch_result(self):
        """Test text content fetch result."""
        result = FetchResult(
            doc_id="doc_test",
            asset_type=AssetType.SECTION,
            asset_id="sec_intro",
            success=True,
            text_content="This is the introduction...",
            page=1,
        )

        mcp_content = result.to_mcp_content()
        assert mcp_content["type"] == "text"
        assert "introduction" in mcp_content["text"]

    def test_image_fetch_result(self):
        """Test image content fetch result."""
        result = FetchResult(
            doc_id="doc_test",
            asset_type=AssetType.FIGURE,
            asset_id="fig_1_1",
            success=True,
            image_base64="iVBORw0KGgo...",
            image_media_type="image/png",
            page=3,
            width=800,
            height=600,
        )

        mcp_content = result.to_mcp_content()
        assert mcp_content["type"] == "image"
        assert mcp_content["mimeType"] == "image/png"
