"""
Domain Layer - Repository Interfaces

Abstract interfaces for data persistence.
Domain layer defines WHAT data operations are needed,
Infrastructure layer provides HOW they are implemented.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entities import DocumentManifest, DocumentSummary


class DocumentRepository(ABC):
    """
    Abstract repository for document storage.

    Infrastructure layer will implement this with FileStorage.
    """

    @abstractmethod
    def save_manifest(self, manifest: DocumentManifest) -> None:
        """Save document manifest."""
        ...

    @abstractmethod
    def load_manifest(self, doc_id: str) -> DocumentManifest | None:
        """Load document manifest by ID."""
        ...

    @abstractmethod
    def save_markdown(self, doc_id: str, content: str) -> Path:
        """Save markdown content and return path."""
        ...

    @abstractmethod
    def load_markdown(self, doc_id: str) -> str | None:
        """Load markdown content by doc ID."""
        ...

    @abstractmethod
    def save_image(self, doc_id: str, image_id: str, data: bytes, ext: str) -> Path:
        """Save image and return path."""
        ...

    @abstractmethod
    def load_image(self, doc_id: str, image_id: str) -> bytes | None:
        """Load image bytes by ID."""
        ...

    @abstractmethod
    def list_documents(self) -> list[DocumentSummary]:
        """List all processed documents."""
        ...

    @abstractmethod
    def document_exists(self, doc_id: str) -> bool:
        """Check if document exists."""
        ...

    @abstractmethod
    def get_doc_dir(self, doc_id: str) -> Path:
        """Get directory path for a document."""
        ...


class PDFExtractorInterface(ABC):
    """
    Abstract interface for PDF extraction.

    Infrastructure layer will implement with PyMuPDF or Mistral OCR.
    """

    @abstractmethod
    def extract_text(self, pdf_path: Path) -> str:
        """Extract text from PDF as markdown."""
        ...

    @abstractmethod
    def extract_images(self, pdf_path: Path) -> list[dict]:
        """
        Extract images from PDF.

        Returns list of dicts with:
        - page: int (1-indexed)
        - image_bytes: bytes
        - ext: str
        - width: int
        - height: int
        """
        ...

    @abstractmethod
    def get_page_count(self, pdf_path: Path) -> int:
        """Get total page count."""
        ...


class KnowledgeGraphInterface(ABC):
    """
    Abstract interface for knowledge graph operations.

    Infrastructure layer will implement with LightRAG.
    """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if knowledge graph is properly configured and available."""
        ...

    @abstractmethod
    async def insert(self, doc_id: str, text: str) -> None:
        """Insert text into knowledge graph."""
        ...

    @abstractmethod
    async def query(self, query: str, mode: str = "hybrid") -> str:
        """Query the knowledge graph."""
        ...

    @abstractmethod
    async def extract_entities(self, text: str, limit: int = 5) -> list[str]:
        """Extract top entities from text."""
        ...
