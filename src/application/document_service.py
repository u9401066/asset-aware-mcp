"""
Application Layer - Document Service

Use cases for document ingestion and management.
Supports multiple PDF backends for flexible extraction.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.domain.entities import (
    DocumentManifest,
    DocumentSummary,
    FigureAsset,
    IngestResult,
    SectionAsset,
    TableAsset,
)
from src.domain.repositories import (
    DocumentRepository,
    KnowledgeGraphInterface,
    PDFExtractorInterface,
)
from src.domain.services import ManifestGenerator
from src.domain.value_objects import DocId

if TYPE_CHECKING:
    from src.infrastructure.marker_adapter import MarkerPDFExtractor


class DocumentService:
    """
    Application service for document operations.

    Orchestrates the ETL pipeline:
    1. Extract text and images from PDF
    2. Generate document manifest
    3. Index in knowledge graph (optional)
    4. Save to repository

    Supports multiple PDF backends:
    - PyMuPDF (default, fast, no models)
    - Marker (optional, use_marker=True, produces blocks.json with bbox/section_hierarchy)
    """

    def __init__(
        self,
        repository: DocumentRepository,
        pdf_extractor: PDFExtractorInterface,
        knowledge_graph: KnowledgeGraphInterface | None = None,
        marker_extractor: MarkerPDFExtractor | None = None,
    ):
        """
        Initialize document service with dependencies.

        Args:
            repository: Document storage repository
            pdf_extractor: PDF extraction implementation (PyMuPDF)
            knowledge_graph: Optional knowledge graph for indexing
            marker_extractor: Optional Marker PDF extractor for structured parsing
        """
        self.repository = repository
        self.pdf_extractor = pdf_extractor
        self.knowledge_graph = knowledge_graph
        self.marker_extractor = marker_extractor
        self.manifest_generator = ManifestGenerator()

    async def ingest(
        self,
        file_paths: list[str],
        use_marker: bool = False,
    ) -> list[IngestResult]:
        """
        Ingest multiple PDF files.

        Args:
            file_paths: List of paths to PDF files
            use_marker: If True, use Marker for structured parsing (slower but richer)
                        - Produces blocks.json with bbox and section_hierarchy
                        - Better TOC and figure caption extraction
                        - Requires Marker models (~1GB first run)

        Returns:
            List of IngestResult for each file
        """
        results = []

        for file_path in file_paths:
            if use_marker and self.marker_extractor:
                result = await self._ingest_single_with_marker(file_path)
            else:
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

            # Step 3.5: Extract tables (Docling enhanced)
            tables = await self._extract_tables(path)

            # Step 4: Get page count
            page_count = self.pdf_extractor.get_page_count(path)

            # Step 5: Extract entities from knowledge graph (if available)
            entities = []
            if self.knowledge_graph and self.knowledge_graph.is_available:
                try:
                    # Index the document
                    await self.knowledge_graph.insert(doc_id.value, markdown)
                    # Extract entities
                    entities = await self.knowledge_graph.extract_entities(markdown)
                except Exception as e:
                    # Log but don't fail - LightRAG is optional
                    import logging

                    logging.warning(f"LightRAG indexing failed: {e}")

            # Step 6: Generate manifest
            manifest = self.manifest_generator.generate(
                doc_id=doc_id.value,
                filename=path.name,
                markdown=markdown,
                figures=figures,
                tables=tables,  # Pass Docling-extracted tables
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

    async def _ingest_single_with_marker(self, file_path: str) -> IngestResult:
        """
        Ingest a single PDF file using Marker for structured parsing.

        This provides richer structure than PyMuPDF:
        - blocks.json with bbox and section_hierarchy
        - Better TOC extraction
        - Figure caption association
        """
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

        if self.marker_extractor is None:
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error="Marker extractor not available",
            )

        try:
            # Generate unique doc_id
            doc_id = DocId.generate(path.stem, str(path.absolute()))

            # Step 1: Parse PDF with Marker (rich structure)
            parse_result = self.marker_extractor.parse(path)

            # Step 2: Save markdown
            markdown_path = self.repository.save_markdown(doc_id.value, parse_result.markdown)

            # Step 3: Save blocks.json (structured data)
            blocks_data = self._convert_blocks_to_json(parse_result.blocks)
            self._save_blocks_json(doc_id.value, blocks_data)

            # Step 4: Extract and save images from Marker result
            figures = await self._save_marker_images(doc_id.value, parse_result)

            # Step 5: Convert Marker blocks to TableAsset
            tables = self._extract_tables_from_blocks(parse_result.blocks)

            # Step 6: Convert TOC to SectionAsset
            sections = self._extract_sections_from_toc(parse_result.toc)

            # Step 7: Get page count
            page_count = parse_result.page_count or self.pdf_extractor.get_page_count(path)

            # Step 8: Index in knowledge graph (if available)
            entities = []
            if self.knowledge_graph and self.knowledge_graph.is_available:
                try:
                    await self.knowledge_graph.insert(doc_id.value, parse_result.markdown)
                    entities = await self.knowledge_graph.extract_entities(parse_result.markdown)
                except Exception as e:
                    import logging
                    logging.warning(f"LightRAG indexing failed: {e}")

            # Step 9: Generate manifest (with richer data)
            # Note: sections are parsed from markdown by ManifestGenerator
            manifest = self.manifest_generator.generate(
                doc_id=doc_id.value,
                filename=path.name,
                markdown=parse_result.markdown,
                figures=figures,
                tables=tables,
                page_count=page_count,
                markdown_path=str(markdown_path),
                lightrag_entities=entities,
            )

            # Step 10: Save manifest
            self.repository.save_manifest(manifest)

            processing_time = time.time() - start_time

            return IngestResult(
                doc_id=doc_id.value,
                filename=path.name,
                title=manifest.title or parse_result.metadata.get("title", ""),
                success=True,
                manifest=manifest,
                pages_processed=page_count,
                tables_found=len(tables),
                figures_found=len(figures),
                sections_found=len(sections),
                processing_time_seconds=processing_time,
                backend="marker",  # Indicate which backend was used
            )

        except Exception as e:
            import traceback
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=f"Marker parsing failed: {str(e)}\n{traceback.format_exc()}",
            )

    def _convert_blocks_to_json(self, blocks: list) -> list[dict]:
        """Convert MarkerBlock objects to JSON-serializable dicts."""
        return [
            {
                "block_id": b.block_id,
                "block_type": b.block_type,
                "page": b.page,
                "text": b.text[:500] if b.text else "",  # Truncate to avoid huge files
                "bbox": b.bbox,
                "polygon": b.polygon,
                "section_hierarchy": b.section_hierarchy,
                "metadata": b.metadata,
            }
            for b in blocks
        ]

    def _save_blocks_json(self, doc_id: str, blocks_data: list[dict]) -> Path:
        """Save blocks.json to repository."""
        # Get the document directory from repository
        doc_dir = self.repository.get_doc_dir(doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)

        blocks_path = doc_dir / "blocks.json"
        blocks_path.write_text(
            json.dumps(blocks_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return blocks_path

    @staticmethod
    def _get_image_dimensions(img_bytes: bytes) -> tuple[int, int]:
        """Read image dimensions from bytes using PIL."""
        try:
            import io

            from PIL import Image

            img = Image.open(io.BytesIO(img_bytes))
            return img.size  # (width, height)
        except Exception:
            return (0, 0)

    async def _save_marker_images(self, doc_id: str, parse_result: Any) -> list[FigureAsset]:
        """Save images from Marker parse result."""
        figures = []

        # Collect all Figure blocks for 1:1 matching with images
        figure_blocks = [
            block for block in parse_result.blocks
            if block.block_type == "Figure"
        ]

        for idx, (img_name, img_bytes) in enumerate(parse_result.images.items(), 1):
            ext = img_name.split(".")[-1] if "." in img_name else "png"
            fig_id = f"fig_{idx}"

            # Save image
            image_path = self.repository.save_image(
                doc_id=doc_id,
                image_id=fig_id,
                data=img_bytes,
                ext=ext,
            )

            # Match corresponding Figure block by index (1:1 mapping)
            page = 1
            caption = ""
            if idx - 1 < len(figure_blocks):
                matched_block = figure_blocks[idx - 1]
                page = matched_block.page
                caption = matched_block.metadata.get("caption", "")

            # Read actual image dimensions
            width, height = self._get_image_dimensions(img_bytes)

            figures.append(
                FigureAsset(
                    id=fig_id,
                    page=page,
                    path=str(image_path),
                    ext=ext,
                    width=width,
                    height=height,
                    caption=caption,
                    figure_type="",
                    source="marker",
                )
            )

        return figures

    @staticmethod
    def _parse_table_dimensions(markdown: str) -> tuple[int, int]:
        """Parse row_count and col_count from markdown table text."""
        if not markdown:
            return (0, 0)
        lines = [line.strip() for line in markdown.strip().splitlines() if line.strip()]
        # Filter out separator lines like |---|---|
        data_lines = [line for line in lines if not all(c in "-| :" for c in line)]
        row_count = len(data_lines)
        col_count = 0
        if data_lines:
            # Count columns from first data line
            col_count = data_lines[0].count("|") - 1
            if col_count < 0:
                col_count = 0
        return (row_count, col_count)

    def _extract_tables_from_blocks(self, blocks: list) -> list[TableAsset]:
        """Extract tables from Marker blocks."""
        tables = []
        table_idx = 0

        for block in blocks:
            if block.block_type == "Table":
                table_idx += 1
                row_count, col_count = self._parse_table_dimensions(block.text)
                tables.append(
                    TableAsset(
                        id=f"tab_{table_idx}",
                        page=block.page,
                        caption="",
                        preview=block.text[:100] if block.text else "",
                        markdown=block.text or "",
                        row_count=row_count,
                        col_count=col_count,
                        has_header=True,
                        source="marker",
                    )
                )

        return tables

    def _extract_sections_from_toc(self, toc: list[dict]) -> list[SectionAsset]:
        """Convert Marker TOC to SectionAsset list."""
        sections = []

        for idx, item in enumerate(toc, 1):
            sections.append(
                SectionAsset(
                    id=f"sec_{idx}",
                    title=item.get("title", ""),
                    level=item.get("level", 1),
                    page=item.get("page", 0),
                    start_line=0,
                    end_line=0,
                    preview="",
                )
            )

        return sections

    async def _extract_and_save_images(
        self, doc_id: str, pdf_path: Path
    ) -> list[FigureAsset]:
        """Extract images from PDF and save them."""
        figures = []

        raw_images = self.pdf_extractor.extract_images(pdf_path)

        # Detect source from extractor type
        source = "pymupdf"
        if hasattr(self.pdf_extractor, "config"):
            source = "docling"

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

            # Get caption from Docling if available
            caption = img_data.get("caption", "")

            figures.append(
                FigureAsset(
                    id=fig_id,
                    page=img_data["page"],
                    path=str(image_path),
                    ext=img_data["ext"],
                    width=img_data["width"],
                    height=img_data["height"],
                    caption=caption,
                    figure_type="",
                    source=source,
                )
            )

        return figures

    async def _extract_tables(self, pdf_path: Path) -> list[TableAsset]:
        """
        Extract tables from PDF.

        Supports:
        - PyMuPDF: find_tables() - heuristic, good for simple grid tables
        - Docling (optional): TableFormer - AI-based, better for complex tables
        """
        # Check if extractor supports table extraction
        if not hasattr(self.pdf_extractor, "extract_tables"):
            return []  # Will fall back to markdown parsing

        # Detect source from extractor type
        source = "pymupdf"
        if hasattr(self.pdf_extractor, "config"):
            source = "docling"

        try:
            raw_tables = self.pdf_extractor.extract_tables(pdf_path)

            tables: list[TableAsset] = []
            for tab_data in raw_tables:
                tables.append(
                    TableAsset(
                        id=tab_data.get("id", f"tab_{len(tables) + 1}"),
                        page=tab_data.get("page", 1),
                        caption=tab_data.get("caption", ""),
                        preview=tab_data.get("preview", ""),
                        markdown=tab_data.get("markdown", ""),
                        row_count=tab_data.get("row_count", 0),
                        col_count=tab_data.get("col_count", 0),
                        has_header=tab_data.get("has_header", True),
                        source=source,
                    )
                )
            return tables

        except Exception as e:
            import logging

            logging.warning(f"Table extraction failed: {e}")
            return []

    async def list_documents(self) -> list[DocumentSummary]:
        """List all processed documents."""
        return self.repository.list_documents()

    async def get_manifest(self, doc_id: str) -> DocumentManifest | None:
        """Get manifest for a specific document."""
        return self.repository.load_manifest(doc_id)

    async def document_exists(self, doc_id: str) -> bool:
        """Check if a document exists."""
        return self.repository.document_exists(doc_id)
