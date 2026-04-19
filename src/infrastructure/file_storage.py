"""
Infrastructure Layer - File Storage

Implementation of DocumentRepository using local filesystem.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path  # noqa: TC003
from typing import Any

from src.domain.entities import DocumentManifest, DocumentSummary
from src.domain.repositories import DocumentRepository

from .config import settings
from .encoding_guard import read_text_file, write_utf8_text

logger = logging.getLogger(__name__)


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

        write_utf8_text(
            manifest_path, manifest.model_dump_json(indent=2), hint=str(manifest_path)
        )

    def load_manifest(self, doc_id: str) -> DocumentManifest | None:
        """Load document manifest by ID."""
        doc_dir = self.get_doc_dir(doc_id)
        manifest_path = doc_dir / f"{doc_id}_manifest.json"

        if not manifest_path.exists():
            return None

        try:
            data = json.loads(read_text_file(manifest_path, hint=str(manifest_path)))
            return DocumentManifest.model_validate(data)
        except Exception:
            return None

    def save_markdown(self, doc_id: str, content: str) -> Path:
        """Save markdown content and return path."""
        doc_dir = self.get_doc_dir(doc_id)
        markdown_path = doc_dir / f"{doc_id}_full.md"
        write_utf8_text(markdown_path, content, hint=str(markdown_path))
        return markdown_path

    def load_markdown(self, doc_id: str) -> str | None:
        """Load markdown content by doc ID."""
        doc_dir = self.get_doc_dir(doc_id)
        markdown_path = doc_dir / f"{doc_id}_full.md"

        if not markdown_path.exists():
            return None

        return read_text_file(markdown_path, hint=str(markdown_path))

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

        # Special directories that should not be listed as documents
        skip_dirs = {"lightrag_db", "jobs", "tables"}

        for doc_dir in self.base_dir.iterdir():
            if not doc_dir.is_dir():
                continue

            # Skip special directories
            if doc_dir.name.startswith(".") or doc_dir.name in skip_dirs:
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
                        text_quality_status=manifest.text_quality_status,
                        ocr_recommended=manifest.ocr_recommended,
                        created_at=manifest.created_at,
                    )
                )

        return documents

    def document_exists(self, doc_id: str) -> bool:
        """Check if document exists."""
        manifest_path = self.base_dir / doc_id / f"{doc_id}_manifest.json"
        return manifest_path.exists()

    def delete_document(self, doc_id: str) -> bool:
        """Delete a stored document directory and all of its artifacts."""
        doc_dir = self.base_dir / doc_id
        if not doc_dir.exists() or not doc_dir.is_dir():
            return False

        shutil.rmtree(doc_dir, ignore_errors=True)
        return not doc_dir.exists()

    def list_docx_documents(self) -> list[dict[str, Any]]:
        """List all DOCX/DFM documents managed by the repository."""
        documents: list[dict[str, Any]] = []

        skip_dirs = {"lightrag_db", "jobs", "tables"}

        for doc_dir in self.base_dir.iterdir():
            if not doc_dir.is_dir():
                continue

            if doc_dir.name.startswith(".") or doc_dir.name in skip_dirs:
                continue

            ir_path = doc_dir / "ir.json"
            original_path = doc_dir / "original.docx"
            if not ir_path.exists() or not original_path.exists():
                continue

            try:
                ir_data = json.loads(read_text_file(ir_path, hint=str(ir_path)))
            except Exception:
                logger.warning("Failed to parse ir.json for %s", doc_dir.name)
                continue

            blocks = ir_data.get("blocks", [])
            block_types: dict[str, int] = {}
            for block in blocks:
                block_type = str(block.get("block_type", "unknown"))
                block_types[block_type] = block_types.get(block_type, 0) + 1

            documents.append(
                {
                    "doc_id": ir_data.get("doc_id", doc_dir.name),
                    "filename": ir_data.get("source_filename", original_path.name),
                    "source_path": ir_data.get("source_path", str(original_path)),
                    "total_blocks": len(blocks),
                    "block_types": block_types,
                    "created_at": ir_data.get("created_at", ""),
                    "updated_at": ir_data.get("updated_at", ""),
                    "has_output_docx": (doc_dir / "output.docx").exists(),
                    "has_output_pdf": (doc_dir / "output.pdf").exists(),
                }
            )

        documents.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return documents
