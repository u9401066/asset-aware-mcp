"""
Application Layer - Document Service

Use cases for document ingestion and management.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.entities import (
    DocumentManifest,
    DocumentSummary,
    FigureAsset,
    IngestResult,
)
from src.domain.repositories import (
    DocumentRepository,
    KnowledgeGraphInterface,
    PDFExtractorInterface,
)
from src.domain.services import ManifestGenerator
from src.domain.value_objects import DocId

if TYPE_CHECKING:
    pass


class DocumentService:
    """
    Application service for document operations.

    Orchestrates the ETL pipeline:
    1. Extract text and images from PDF
    2. Generate document manifest
    3. Index in knowledge graph (optional)
    4. Save to repository
    """

    def __init__(
        self,
        repository: DocumentRepository,
        pdf_extractor: PDFExtractorInterface,
        knowledge_graph: KnowledgeGraphInterface | None = None,
    ):
        """
        Initialize document service with dependencies.

        Args:
            repository: Document storage repository
            pdf_extractor: PDF extraction implementation
            knowledge_graph: Optional knowledge graph for indexing
        """
        self.repository = repository
        self.pdf_extractor = pdf_extractor
        self.knowledge_graph = knowledge_graph
        self.manifest_generator = ManifestGenerator()

    async def ingest(self, file_paths: list[str]) -> list[IngestResult]:
        """
        Ingest multiple PDF files.

        Args:
            file_paths: List of paths to PDF files

        Returns:
            List of IngestResult for each file
        """
        results = []

        for file_path in file_paths:
            result = await self._ingest_single(file_path)
            results.append(result)

        return results

    async def _ingest_single(self, file_path: str) -> IngestResult:
        """Ingest a single PDF file."""
        start_time = time.time()
        path = Path(file_path)

        # Validate file exists
        if not path.exists():
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=f"File not found: {path}",
            )

        if not path.suffix.lower() == ".pdf":
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=f"Not a PDF file: {path}",
            )

        try:
            # Generate unique doc_id
            doc_id = DocId.generate(path.stem, str(path.absolute()))

            # Step 1: Extract text as markdown
            markdown = self.pdf_extractor.extract_text(path)

            # Step 2: Save markdown
            markdown_path = self.repository.save_markdown(doc_id.value, markdown)

            # Step 3: Extract and save images
            figures = await self._extract_and_save_images(doc_id.value, path)

            # Step 4: Get page count
            page_count = self.pdf_extractor.get_page_count(path)

            # Step 5: Extract entities from knowledge graph (if available)
            entities = []
            lightrag_error = None
            if self.knowledge_graph and self.knowledge_graph.is_available:
                try:
                    # Index the document
                    await self.knowledge_graph.insert(doc_id.value, markdown)
                    # Extract entities
                    entities = await self.knowledge_graph.extract_entities(markdown)
                except Exception as e:
                    lightrag_error = str(e)
                    # Log but don't fail - LightRAG is optional
                    import logging
                    logging.warning(f"LightRAG indexing failed: {e}")

            # Step 6: Generate manifest
            manifest = self.manifest_generator.generate(
                doc_id=doc_id.value,
                filename=path.name,
                markdown=markdown,
                figures=figures,
                page_count=page_count,
                markdown_path=str(markdown_path),
                lightrag_entities=entities,
            )

            # Step 7: Save manifest
            self.repository.save_manifest(manifest)

            processing_time = time.time() - start_time

            return IngestResult(
                doc_id=doc_id.value,
                filename=path.name,
                title=manifest.title,
                success=True,
                manifest=manifest,
                pages_processed=page_count,
                tables_found=len(manifest.assets.tables),
                figures_found=len(manifest.assets.figures),
                sections_found=len(manifest.assets.sections),
                processing_time_seconds=processing_time,
            )

        except Exception as e:
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=str(e),
            )

    async def _extract_and_save_images(
        self,
        doc_id: str,
        pdf_path: Path
    ) -> list[FigureAsset]:
        """Extract images from PDF and save them."""
        figures = []

        raw_images = self.pdf_extractor.extract_images(pdf_path)

        for img_data in raw_images:
            # Generate figure ID: fig_{page}_{index}
            fig_id = f"fig_{img_data['page']}_{img_data['index_on_page']}"

            # Save image
            image_path = self.repository.save_image(
                doc_id=doc_id,
                image_id=fig_id,
                data=img_data["image_bytes"],
                ext=img_data["ext"],
            )

            figures.append(FigureAsset(
                id=fig_id,
                page=img_data["page"],
                path=str(image_path),
                ext=img_data["ext"],
                width=img_data["width"],
                height=img_data["height"],
                caption="",  # Caption detection TODO
            ))

        return figures

    async def list_documents(self) -> list[DocumentSummary]:
        """List all processed documents."""
        return self.repository.list_documents()

    async def get_manifest(self, doc_id: str) -> DocumentManifest | None:
        """Get manifest for a specific document."""
        return self.repository.load_manifest(doc_id)

    async def document_exists(self, doc_id: str) -> bool:
        """Check if a document exists."""
        return self.repository.document_exists(doc_id)
