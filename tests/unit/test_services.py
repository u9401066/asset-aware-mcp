"""
Unit Tests for Domain Layer - Services

Tests for ManifestGenerator and AssetExtractor.
"""

from __future__ import annotations

import pytest

from src.domain.services import AssetExtractor, ManifestGenerator


class TestManifestGenerator:
    """Tests for ManifestGenerator domain service."""

    @pytest.fixture
    def generator(self) -> ManifestGenerator:
        """Create a ManifestGenerator instance."""
        return ManifestGenerator()

    def test_generate_manifest(
        self, generator: ManifestGenerator, sample_markdown: str
    ):
        """Test generating a complete manifest."""
        manifest = generator.generate(
            doc_id="doc_test_abc123",
            filename="test.pdf",
            markdown=sample_markdown,
            figures=[],
            page_count=3,
            markdown_path="/data/doc_test/test_full.md",
            lightrag_entities=["Entity1", "Entity2"],
        )

        assert manifest.doc_id == "doc_test_abc123"
        assert manifest.filename == "test.pdf"
        assert manifest.page_count == 3
        assert len(manifest.lightrag_entities) == 2

    def test_parse_tables(self, generator: ManifestGenerator, sample_markdown: str):
        """Test table parsing from markdown."""
        tables = generator._parse_tables(sample_markdown)

        assert len(tables) == 1
        assert tables[0].id == "tab_1"
        assert tables[0].row_count == 3  # Header row + 2 data rows (separator excluded)
        assert tables[0].col_count == 3

    def test_parse_sections(self, generator: ManifestGenerator, sample_markdown: str):
        """Test section parsing from markdown."""
        sections = generator._parse_sections(sample_markdown)

        # Should find: Title, Introduction, Methods, Data Collection, Results, Statistical Analysis, Discussion
        titles = [s.title for s in sections]

        assert "Test Document Title" in titles
        assert "Introduction" in titles
        assert "Methods" in titles
        assert "Results" in titles
        assert "Discussion" in titles

    def test_detect_title(self, generator: ManifestGenerator, sample_markdown: str):
        """Test title detection from markdown."""
        title = generator._detect_title(sample_markdown)

        assert title == "Test Document Title"

    def test_toc_generation(self, generator: ManifestGenerator, sample_markdown: str):
        """Test table of contents generation."""
        manifest = generator.generate(
            doc_id="doc_test",
            filename="test.pdf",
            markdown=sample_markdown,
            figures=[],
            page_count=3,
            markdown_path="/test",
        )

        # TOC should contain only level 1-2 headings
        assert "Test Document Title" in manifest.toc
        assert "Introduction" in manifest.toc
        assert "Methods" in manifest.toc

    def test_page_tracking(self, generator: ManifestGenerator, sample_markdown: str):
        """Test that sections track page numbers correctly."""
        sections = generator._parse_sections(sample_markdown)

        # Introduction should be on page 1
        intro = next((s for s in sections if s.title == "Introduction"), None)
        assert intro is not None
        assert intro.page == 1

        # Methods should be on page 2
        methods = next((s for s in sections if s.title == "Methods"), None)
        assert methods is not None
        assert methods.page == 2


class TestAssetExtractor:
    """Tests for AssetExtractor domain service."""

    @pytest.fixture
    def extractor(self) -> AssetExtractor:
        """Create an AssetExtractor instance."""
        return AssetExtractor()

    def test_extract_section_content(
        self, extractor: AssetExtractor, sample_markdown: str
    ):
        """Test extracting section content."""
        from src.domain.entities import SectionAsset

        # Create a section that spans lines 5-10
        section = SectionAsset(
            id="sec_intro",
            title="Introduction",
            level=2,
            page=1,
            start_line=4,  # ## Introduction
            end_line=8,
            preview="",
        )

        content = extractor.extract_section_content(sample_markdown, section)

        assert "Introduction" in content
        assert "important information" in content

    def test_extract_table_by_id(self, extractor: AssetExtractor, sample_markdown: str):
        """Test extracting table by ID."""
        table_content = extractor.extract_table_by_id(sample_markdown, "tab_1")

        assert table_content is not None
        assert "Column A" in table_content
        assert "Value 1" in table_content

    def test_extract_nonexistent_table(
        self, extractor: AssetExtractor, sample_markdown: str
    ):
        """Test extracting non-existent table returns None."""
        table_content = extractor.extract_table_by_id(sample_markdown, "tab_999")

        assert table_content is None
