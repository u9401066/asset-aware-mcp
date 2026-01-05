"""
Unit Tests for Infrastructure Layer - File Storage

Tests for FileStorage repository implementation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.domain.entities import DocumentAssets, DocumentManifest
from src.infrastructure.file_storage import FileStorage


class TestFileStorage:
    """Tests for FileStorage repository."""

    @pytest.fixture
    def storage(self, temp_dir: Path) -> FileStorage:
        """Create FileStorage with temporary directory."""
        return FileStorage(base_dir=temp_dir)

    @pytest.fixture
    def sample_manifest(self) -> DocumentManifest:
        """Create a sample manifest for testing."""
        return DocumentManifest(
            doc_id="doc_test_abc123",
            filename="test.pdf",
            title="Test Document",
            toc=["Introduction", "Methods"],
            assets=DocumentAssets(),
            page_count=5,
            markdown_path="",
            manifest_path="",
        )

    def test_get_doc_dir(self, storage: FileStorage):
        """Test document directory creation."""
        doc_dir = storage.get_doc_dir("doc_test_abc123")

        assert doc_dir.exists()
        assert doc_dir.name == "doc_test_abc123"

    def test_save_and_load_manifest(self, storage: FileStorage, sample_manifest: DocumentManifest):
        """Test saving and loading manifest."""
        storage.save_manifest(sample_manifest)

        loaded = storage.load_manifest("doc_test_abc123")

        assert loaded is not None
        assert loaded.doc_id == "doc_test_abc123"
        assert loaded.title == "Test Document"
        assert loaded.page_count == 5

    def test_load_nonexistent_manifest(self, storage: FileStorage):
        """Test loading non-existent manifest returns None."""
        loaded = storage.load_manifest("doc_nonexistent")

        assert loaded is None

    def test_save_and_load_markdown(self, storage: FileStorage):
        """Test saving and loading markdown content."""
        content = "# Test Document\n\nThis is test content."

        path = storage.save_markdown("doc_test_abc123", content)

        assert path.exists()
        assert path.name == "doc_test_abc123_full.md"

        loaded = storage.load_markdown("doc_test_abc123")
        assert loaded == content

    def test_save_and_load_image(self, storage: FileStorage):
        """Test saving and loading image."""
        # Create a minimal PNG (1x1 pixel)
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 size
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xFF, 0xFF, 0x3F,
            0x00, 0x05, 0xFE, 0x02, 0xFE, 0xDC, 0xCC, 0x59,
            0xE7, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
            0x44, 0xAE, 0x42, 0x60, 0x82,
        ])

        path = storage.save_image("doc_test_abc123", "fig_1_1", png_data, "png")

        assert path.exists()
        assert path.parent.name == "images"

        loaded = storage.load_image("doc_test_abc123", "fig_1_1")
        assert loaded == png_data

    def test_list_documents(self, storage: FileStorage, sample_manifest: DocumentManifest):
        """Test listing all documents."""
        # Save a manifest
        storage.save_manifest(sample_manifest)

        documents = storage.list_documents()

        assert len(documents) == 1
        assert documents[0].doc_id == "doc_test_abc123"
        assert documents[0].title == "Test Document"

    def test_document_exists(self, storage: FileStorage, sample_manifest: DocumentManifest):
        """Test checking document existence."""
        assert not storage.document_exists("doc_test_abc123")

        storage.save_manifest(sample_manifest)

        assert storage.document_exists("doc_test_abc123")
