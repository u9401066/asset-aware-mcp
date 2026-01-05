"""
Unit Tests for Domain Layer - Value Objects

Tests for DocId, AssetType, and ImageMediaType.
"""

from __future__ import annotations

import pytest

from src.domain.value_objects import AssetType, DocId, ImageMediaType


class TestDocId:
    """Tests for DocId value object."""

    def test_valid_doc_id(self):
        """Test creating a valid DocId."""
        doc_id = DocId("doc_test_abc123")
        assert doc_id.value == "doc_test_abc123"
        assert str(doc_id) == "doc_test_abc123"

    def test_invalid_doc_id_empty(self):
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid doc_id format"):
            DocId("")

    def test_invalid_doc_id_no_prefix(self):
        """Test that ID without 'doc_' prefix raises ValueError."""
        with pytest.raises(ValueError, match="Invalid doc_id format"):
            DocId("test_abc123")

    def test_invalid_doc_id_uppercase(self):
        """Test that uppercase characters raise ValueError."""
        with pytest.raises(ValueError, match="Invalid doc_id format"):
            DocId("doc_TEST_abc123")

    def test_generate_from_filename(self):
        """Test generating DocId from filename."""
        doc_id = DocId.generate("Study_Report.pdf", "unique_path")
        assert doc_id.value.startswith("doc_study_report_pdf")

    def test_equality(self):
        """Test DocId equality comparison."""
        doc1 = DocId("doc_test_abc123")
        doc2 = DocId("doc_test_abc123")
        doc3 = DocId("doc_other_xyz789")

        assert doc1 == doc2
        assert doc1 != doc3
        assert doc1 == "doc_test_abc123"

    def test_hash(self):
        """Test that DocId is hashable."""
        doc_id = DocId("doc_test_abc123")
        doc_set = {doc_id}
        assert doc_id in doc_set


class TestAssetType:
    """Tests for AssetType enum."""

    def test_asset_types_exist(self):
        """Test that all asset types are defined."""
        assert AssetType.TABLE.value == "table"
        assert AssetType.FIGURE.value == "figure"
        assert AssetType.SECTION.value == "section"
        assert AssetType.FULL_TEXT.value == "full_text"

    def test_from_string(self):
        """Test creating AssetType from string."""
        assert AssetType("table") == AssetType.TABLE
        assert AssetType("figure") == AssetType.FIGURE


class TestImageMediaType:
    """Tests for ImageMediaType enum."""

    def test_from_extension_png(self):
        """Test PNG extension mapping."""
        assert ImageMediaType.from_extension("png") == ImageMediaType.PNG
        assert ImageMediaType.PNG.value == "image/png"

    def test_from_extension_jpg(self):
        """Test JPEG extension mapping."""
        assert ImageMediaType.from_extension("jpg") == ImageMediaType.JPEG
        assert ImageMediaType.from_extension("jpeg") == ImageMediaType.JPEG

    def test_from_extension_unknown(self):
        """Test unknown extension defaults to PNG."""
        assert ImageMediaType.from_extension("xyz") == ImageMediaType.PNG

    def test_from_extension_case_insensitive(self):
        """Test that extension lookup is case-insensitive."""
        assert ImageMediaType.from_extension("PNG") == ImageMediaType.PNG
        assert ImageMediaType.from_extension("JPG") == ImageMediaType.JPEG
