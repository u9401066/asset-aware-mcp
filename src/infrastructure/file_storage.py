"""
Infrastructure Layer - File Storage

Implementation of DocumentRepository using local filesystem.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.entities import DocumentManifest, DocumentSummary
from src.domain.repositories import DocumentRepository

from .config import settings

if TYPE_CHECKING:
    pass


class FileStorage(DocumentRepository):
    """
    File-based implementation of DocumentRepository.

    Stores documents in local filesystem with structure:
    data/
    └── {doc_id}/
        ├── {doc_id}_full.md
        ├── {doc_id}_manifest.json
        └── images/
            └── fig_1_1.png
    """

    def __init__(self, base_dir: Path | None = None):
        """
        Initialize file storage.

        Args:
            base_dir: Base directory for storage (default: settings.data_dir)
        """
        self.base_dir = base_dir or settings.data_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_doc_dir(self, doc_id: str) -> Path:
        """Get directory for a specific document."""
        doc_dir = self.base_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        return doc_dir

    def save_manifest(self, manifest: DocumentManifest) -> None:
        """Save document manifest as JSON."""
        doc_dir = self.get_doc_dir(manifest.doc_id)
        manifest_path = doc_dir / f"{manifest.doc_id}_manifest.json"

        # Update manifest path
        manifest.manifest_path = str(manifest_path)

        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    def load_manifest(self, doc_id: str) -> DocumentManifest | None:
        """Load document manifest by ID."""
        doc_dir = self.get_doc_dir(doc_id)
        manifest_path = doc_dir / f"{doc_id}_manifest.json"

        if not manifest_path.exists():
            return None

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return DocumentManifest.model_validate(data)
        except Exception:
            return None

    def save_markdown(self, doc_id: str, content: str) -> Path:
        """Save markdown content and return path."""
        doc_dir = self.get_doc_dir(doc_id)
        markdown_path = doc_dir / f"{doc_id}_full.md"
        markdown_path.write_text(content, encoding="utf-8")
        return markdown_path

    def load_markdown(self, doc_id: str) -> str | None:
        """Load markdown content by doc ID."""
        doc_dir = self.get_doc_dir(doc_id)
        markdown_path = doc_dir / f"{doc_id}_full.md"

        if not markdown_path.exists():
            return None

        return markdown_path.read_text(encoding="utf-8")

    def save_image(self, doc_id: str, image_id: str, data: bytes, ext: str) -> Path:
        """Save image and return path."""
        doc_dir = self.get_doc_dir(doc_id)
        images_dir = doc_dir / "images"
        images_dir.mkdir(exist_ok=True)

        image_path = images_dir / f"{image_id}.{ext}"
        image_path.write_bytes(data)
        return image_path

    def load_image(self, doc_id: str, image_id: str) -> bytes | None:
        """Load image bytes by ID."""
        doc_dir = self.get_doc_dir(doc_id)
        images_dir = doc_dir / "images"

        # Try common extensions
        for ext in ["png", "jpg", "jpeg", "gif", "webp"]:
            image_path = images_dir / f"{image_id}.{ext}"
            if image_path.exists():
                return image_path.read_bytes()

        return None

    def list_documents(self) -> list[DocumentSummary]:
        """List all processed documents."""
        documents = []

        for doc_dir in self.base_dir.iterdir():
            if not doc_dir.is_dir():
                continue

            # Skip special directories
            if doc_dir.name.startswith(".") or doc_dir.name == "lightrag_db":
                continue

            manifest = self.load_manifest(doc_dir.name)
            if manifest:
                asset_summary = manifest.get_asset_summary()
                documents.append(
                    DocumentSummary(
                        doc_id=manifest.doc_id,
                        filename=manifest.filename,
                        title=manifest.title,
                        page_count=manifest.page_count,
                        table_count=asset_summary.get("tables", 0),
                        figure_count=asset_summary.get("figures", 0),
                        section_count=asset_summary.get("sections", 0),
                        created_at=manifest.created_at,
                    )
                )

        return documents

    def document_exists(self, doc_id: str) -> bool:
        """Check if document exists."""
        manifest_path = self.base_dir / doc_id / f"{doc_id}_manifest.json"
        return manifest_path.exists()
