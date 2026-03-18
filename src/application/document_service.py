"""
Application Layer - Document Service

Use cases for document ingestion and management.
Supports multiple PDF backends for flexible extraction.
"""

from __future__ import annotations

import inspect
import json
import re
import shutil
import time
from collections.abc import Awaitable, Callable
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
from src.domain.etl_profile import ETLProfile
from src.domain.line_spans import (
    MarkdownLineSpanIndex,
    annotate_marker_blocks,
    apply_asset_line_spans,
)
from src.domain.services import ManifestGenerator
from src.domain.value_objects import DocId

if TYPE_CHECKING:
    from src.domain.repositories import (
        DocumentRepository,
        KnowledgeGraphInterface,
        PDFExtractorInterface,
    )
    from src.infrastructure.marker_adapter import MarkerPDFExtractor
    from src.infrastructure.ocr_processor import OCRProcessor


ToolProgressCallback = Callable[[int, int, str, str], Awaitable[None] | None]


async def _invoke_progress_callback(
    callback: ToolProgressCallback | None,
    step: int,
    total_steps: int,
    phase: str,
    message: str,
) -> None:
    if callback is None:
        return

    result = callback(step, total_steps, phase, message)
    if inspect.isawaitable(result):
        await result


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
        profile: ETLProfile | None = None,
        ocr_processor: OCRProcessor | None = None,
    ):
        """
        Initialize document service with dependencies.

        Args:
            repository: Document storage repository
            pdf_extractor: PDF extraction implementation (PyMuPDF)
            knowledge_graph: Optional knowledge graph for indexing
            marker_extractor: Optional Marker PDF extractor for structured parsing
            profile: Optional ETL profile (auto-detected from pdf_extractor if not provided)
        """
        self.repository = repository
        self.pdf_extractor = pdf_extractor
        self.knowledge_graph = knowledge_graph
        self.marker_extractor = marker_extractor
        self.ocr_processor = ocr_processor

        # Resolve profile: explicit > from extractor > default
        if profile is not None:
            resolved_profile = profile
        elif hasattr(pdf_extractor, "profile"):
            resolved_profile = pdf_extractor.profile
        else:
            resolved_profile = ETLProfile.default()

        self.manifest_generator = ManifestGenerator(profile=resolved_profile)

    async def ingest(
        self,
        file_paths: list[str],
        use_marker: bool = False,
        progress_callback: ToolProgressCallback | None = None,
        *,
        ocr_enabled: bool = False,
        ocr_language: str = "eng",
        rotate_pages: bool = False,
        deskew: bool = False,
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
        base_steps = 9 if use_marker and self.marker_extractor else 8
        per_file_steps = base_steps + (1 if ocr_enabled else 0)
        total_steps = max(len(file_paths), 1) * per_file_steps

        for index, file_path in enumerate(file_paths):
            base_step = index * per_file_steps

            async def file_progress(
                step: int,
                inner_total_steps: int,
                phase: str,
                message: str,
                *,
                _base_step: int = base_step,
                _file_index: int = index,
            ) -> None:
                bounded_total = max(inner_total_steps, 1)
                mapped_step = _base_step + min(max(step, 0), bounded_total)
                await _invoke_progress_callback(
                    progress_callback,
                    mapped_step,
                    total_steps,
                    phase,
                    f"[{_file_index + 1}/{len(file_paths)}] {message}",
                )

            if use_marker and self.marker_extractor:
                result = await self._ingest_single_with_marker(
                    file_path,
                    progress_callback=file_progress,
                    ocr_enabled=ocr_enabled,
                    ocr_language=ocr_language,
                    rotate_pages=rotate_pages,
                    deskew=deskew,
                )
            else:
                result = await self._ingest_single(
                    file_path,
                    progress_callback=file_progress,
                    ocr_enabled=ocr_enabled,
                    ocr_language=ocr_language,
                    rotate_pages=rotate_pages,
                    deskew=deskew,
                )
            results.append(result)

        return results

    async def _ingest_single(
        self,
        file_path: str,
        progress_callback: ToolProgressCallback | None = None,
        *,
        ocr_enabled: bool = False,
        ocr_language: str = "eng",
        rotate_pages: bool = False,
        deskew: bool = False,
    ) -> IngestResult:
        """Ingest a single PDF file."""
        start_time = time.time()
        path = Path(file_path)
        total_steps = 9 if ocr_enabled else 8

        # Validate file exists
        if not path.exists():
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=f"File not found: {path}",
            )

        if path.suffix.lower() != ".pdf":
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=f"Not a PDF file: {path}",
            )

        # Validate PDF magic bytes (%PDF-)
        try:
            with path.open("rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                return IngestResult(
                    doc_id="",
                    filename=path.name,
                    success=False,
                    error="Invalid PDF: file does not start with %PDF- header",
                )
        except OSError as e:
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=f"Cannot read file: {e}",
            )

        try:
            # Generate unique doc_id
            await _invoke_progress_callback(
                progress_callback,
                1,
                total_steps,
                "Preparing",
                f"Preparing {path.name}",
            )
            doc_id = DocId.generate(path.stem, str(path.absolute()))
            self._save_original_pdf_copy(doc_id.value, path)

            active_pdf_path = path
            current_step = 2
            if ocr_enabled:
                await _invoke_progress_callback(
                    progress_callback,
                    current_step,
                    total_steps,
                    "OCR Preprocessing",
                    f"Running OCR preprocessing for {path.name}",
                )
                active_pdf_path = self._preprocess_pdf_with_ocr(
                    doc_id.value,
                    path,
                    language=ocr_language,
                    rotate_pages=rotate_pages,
                    deskew=deskew,
                )
                current_step += 1

            # Step 1: Extract text as markdown
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Extracting Text",
                f"Extracting text from {path.name}",
            )
            markdown = self.pdf_extractor.extract_text(active_pdf_path)
            current_step += 1

            # Step 2: Save markdown
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Saving Markdown",
                f"Saving markdown for {path.name}",
            )
            markdown_path = self.repository.save_markdown(doc_id.value, markdown)
            current_step += 1

            # Step 3: Extract and save images
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Extracting Figures",
                f"Extracting figures from {path.name}",
            )
            figures = await self._extract_and_save_images(doc_id.value, active_pdf_path)
            current_step += 1

            # Step 3.5: Extract tables (Docling enhanced)
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Extracting Tables",
                f"Extracting tables from {path.name}",
            )
            tables = await self._extract_tables(active_pdf_path)
            apply_asset_line_spans(MarkdownLineSpanIndex(markdown), figures, tables)
            current_step += 1

            # Step 4: Get page count
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Reading Metadata",
                f"Reading PDF metadata from {path.name}",
            )
            page_count = self.pdf_extractor.get_page_count(active_pdf_path)
            current_step += 1

            # Step 4.5: Get PDF built-in TOC and metadata title (if available)
            pdf_toc: list[tuple[int, str, int]] = []
            pdf_title = ""
            if hasattr(self.pdf_extractor, "get_toc"):
                pdf_toc = self.pdf_extractor.get_toc(active_pdf_path)
            if hasattr(self.pdf_extractor, "get_title"):
                pdf_title = self.pdf_extractor.get_title(active_pdf_path)

            # Step 5: Extract entities from knowledge graph (if available)
            entities = []
            if self.knowledge_graph and self.knowledge_graph.is_available:
                await _invoke_progress_callback(
                    progress_callback,
                    current_step,
                    total_steps,
                    "Indexing Knowledge Graph",
                    f"Indexing {path.name} into the knowledge graph",
                )
                try:
                    # Index the document
                    await self.knowledge_graph.insert(doc_id.value, markdown)
                    # Extract entities
                    entities = await self.knowledge_graph.extract_entities(markdown)
                except Exception:
                    # Log but don't fail - LightRAG is optional
                    import logging

                    logging.getLogger(__name__).warning(
                        "LightRAG indexing failed for %s", doc_id.value, exc_info=True
                    )
            else:
                await _invoke_progress_callback(
                    progress_callback,
                    current_step,
                    total_steps,
                    "Skipping Knowledge Graph",
                    f"Knowledge graph indexing skipped for {path.name}",
                )
            current_step += 1

            # Step 6: Generate manifest
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Generating Manifest",
                f"Generating manifest for {path.name}",
            )
            manifest = self.manifest_generator.generate(
                doc_id=doc_id.value,
                filename=path.name,
                markdown=markdown,
                figures=figures,
                tables=tables,  # Pass Docling-extracted tables
                page_count=page_count,
                markdown_path=str(markdown_path),
                lightrag_entities=entities,
                pdf_toc=pdf_toc,
                pdf_title=pdf_title,
            )

            # Step 7: Save manifest
            self.repository.save_manifest(manifest)
            await _invoke_progress_callback(
                progress_callback,
                total_steps,
                total_steps,
                "Completed",
                f"Finished processing {path.name}",
            )

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

    async def _ingest_single_with_marker(
        self,
        file_path: str,
        progress_callback: ToolProgressCallback | None = None,
        *,
        ocr_enabled: bool = False,
        ocr_language: str = "eng",
        rotate_pages: bool = False,
        deskew: bool = False,
    ) -> IngestResult:
        """
        Ingest a single PDF file using Marker for structured parsing.

        This provides richer structure than PyMuPDF:
        - blocks.json with bbox and section_hierarchy
        - Better TOC extraction
        - Figure caption association
        """
        start_time = time.time()
        path = Path(file_path)
        total_steps = 10 if ocr_enabled else 9

        # Validate file exists
        if not path.exists():
            return IngestResult(
                doc_id="",
                filename=path.name,
                success=False,
                error=f"File not found: {path}",
            )

        if path.suffix.lower() != ".pdf":
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
            await _invoke_progress_callback(
                progress_callback,
                1,
                total_steps,
                "Preparing",
                f"Preparing {path.name}",
            )
            doc_id = DocId.generate(path.stem, str(path.absolute()))
            self._save_original_pdf_copy(doc_id.value, path)

            active_pdf_path = path
            current_step = 2
            if ocr_enabled:
                await _invoke_progress_callback(
                    progress_callback,
                    current_step,
                    total_steps,
                    "OCR Preprocessing",
                    f"Running OCR preprocessing for {path.name}",
                )
                active_pdf_path = self._preprocess_pdf_with_ocr(
                    doc_id.value,
                    path,
                    language=ocr_language,
                    rotate_pages=rotate_pages,
                    deskew=deskew,
                )
                current_step += 1

            # Step 1: Parse PDF with Marker (rich structure)
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Parsing Structure",
                f"Parsing structure from {path.name} with Marker",
            )
            parse_result = self.marker_extractor.parse(active_pdf_path)
            current_step += 1

            # Step 2: Save markdown
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Saving Markdown",
                f"Saving markdown for {path.name}",
            )
            line_span_index = annotate_marker_blocks(
                parse_result.markdown,
                parse_result.blocks,
            )
            markdown_path = self.repository.save_markdown(
                doc_id.value, parse_result.markdown
            )
            current_step += 1

            # Step 3: Save blocks.json (structured data)
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Saving Blocks",
                f"Saving structured blocks for {path.name}",
            )
            blocks_data = self._convert_blocks_to_json(parse_result.blocks)
            self._save_blocks_json(doc_id.value, blocks_data)
            current_step += 1

            # Step 4: Extract and save images from Marker result
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Extracting Figures",
                f"Extracting figures from {path.name}",
            )
            figures = await self._save_marker_images(doc_id.value, parse_result)
            current_step += 1

            # Step 5: Convert Marker blocks to TableAsset
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Extracting Tables",
                f"Extracting tables from {path.name}",
            )
            tables = self._extract_tables_from_blocks(parse_result.blocks)
            current_step += 1

            # Step 6: Convert TOC to SectionAsset
            await _invoke_progress_callback(
                progress_callback,
                current_step,
                total_steps,
                "Building Sections",
                f"Building section tree for {path.name}",
            )
            sections = self._extract_sections_from_toc(
                parse_result.toc,
                parse_result.markdown,
            )
            apply_asset_line_spans(
                line_span_index,
                figures,
                tables,
                blocks=parse_result.blocks,
                sections=sections,
            )
            current_step += 1

            # Step 7: Get page count
            page_count = parse_result.page_count or self.pdf_extractor.get_page_count(
                active_pdf_path
            )

            # Step 8: Index in knowledge graph (if available)
            entities = []
            if self.knowledge_graph and self.knowledge_graph.is_available:
                await _invoke_progress_callback(
                    progress_callback,
                    current_step,
                    total_steps,
                    "Indexing Knowledge Graph",
                    f"Indexing {path.name} into the knowledge graph",
                )
                try:
                    await self.knowledge_graph.insert(
                        doc_id.value, parse_result.markdown
                    )
                    entities = await self.knowledge_graph.extract_entities(
                        parse_result.markdown
                    )
                except Exception as e:
                    import logging

                    logging.warning(f"LightRAG indexing failed: {e}")
            else:
                await _invoke_progress_callback(
                    progress_callback,
                    current_step,
                    total_steps,
                    "Skipping Knowledge Graph",
                    f"Knowledge graph indexing skipped for {path.name}",
                )
            current_step += 1

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
                sections=sections,
            )

            # Step 10: Save manifest
            self.repository.save_manifest(manifest)
            await _invoke_progress_callback(
                progress_callback,
                total_steps,
                total_steps,
                "Completed",
                f"Finished processing {path.name}",
            )

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
                error=f"Marker parsing failed: {e!s}\n{traceback.format_exc()}",
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

    def _save_original_pdf_copy(self, doc_id: str, source_path: Path) -> None:
        """Persist the original PDF for overlay inspection and downstream tooling."""
        doc_dir = self.repository.get_doc_dir(doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        target = doc_dir / "original.pdf"
        shutil.copy2(source_path, target)

    def _preprocess_pdf_with_ocr(
        self,
        doc_id: str,
        source_path: Path,
        *,
        language: str,
        rotate_pages: bool,
        deskew: bool,
    ) -> Path:
        if self.ocr_processor is None:
            raise RuntimeError(
                "OCR preprocessing requested, but OCR processor is not configured."
            )

        doc_dir = self.repository.get_doc_dir(doc_id)
        target = doc_dir / "ocr_processed.pdf"
        result = self.ocr_processor.preprocess_pdf(
            source_path,
            target,
            language=language,
            rotate_pages=rotate_pages,
            deskew=deskew,
        )
        return result.output_path

    @staticmethod
    def _get_image_dimensions(img_bytes: bytes) -> tuple[int, int]:
        """Read image dimensions from bytes using PIL."""
        try:
            import io

            from PIL import Image

            img = Image.open(io.BytesIO(img_bytes))
            size: tuple[int, int] = img.size  # (width, height)
            return size
        except Exception:  # PIL can raise various errors
            return (0, 0)

    async def _save_marker_images(
        self, doc_id: str, parse_result: Any
    ) -> list[FigureAsset]:
        """Save images from Marker parse result."""
        figures = []

        # Collect all Figure blocks for 1:1 matching with images
        figure_blocks = [
            block for block in parse_result.blocks if block.block_type == "Figure"
        ]

        for idx, (img_name, img_bytes) in enumerate(parse_result.images.items(), 1):
            ext = img_name.split(".")[-1] if "." in img_name else "png"
            fig_id = f"fig_{idx}"
            matched_block = (
                figure_blocks[idx - 1] if idx - 1 < len(figure_blocks) else None
            )

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
            if matched_block is not None:
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
                    source_block_id=matched_block.block_id if matched_block else "",
                    source_order=int(matched_block.metadata.get("source_order") or 0)
                    if matched_block
                    else 0,
                    line_start=int(matched_block.metadata.get("line_start"))
                    if matched_block
                    and isinstance(matched_block.metadata.get("line_start"), int)
                    else None,
                    line_end=int(matched_block.metadata.get("line_end"))
                    if matched_block
                    and isinstance(matched_block.metadata.get("line_end"), int)
                    else None,
                    line_source=str(
                        matched_block.metadata.get("line_match_strategy") or ""
                    )
                    if matched_block
                    else "",
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
                        source_block_id=block.block_id,
                        source_order=int(block.metadata.get("source_order") or 0),
                        line_start=int(block.metadata.get("line_start"))
                        if isinstance(block.metadata.get("line_start"), int)
                        else None,
                        line_end=int(block.metadata.get("line_end"))
                        if isinstance(block.metadata.get("line_end"), int)
                        else None,
                        line_source=str(
                            block.metadata.get("line_match_strategy") or ""
                        ),
                    )
                )

        return tables

    def _extract_sections_from_toc(
        self,
        toc: list[dict],
        markdown: str,
    ) -> list[SectionAsset]:
        """Convert Marker TOC to SectionAsset list."""
        sections = []
        existing_ids: set[str] = set()
        line_index = MarkdownLineSpanIndex(markdown)

        for idx, item in enumerate(toc, 1):
            title = item.get("title", "")
            base_id = f"sec_{idx}"
            sec_id = base_id
            if sec_id in existing_ids:
                counter = 2
                while f"{base_id}_{counter}" in existing_ids:
                    counter += 1
                sec_id = f"{base_id}_{counter}"
            section_span = line_index.find_section_span(
                title,
                page_hint=item.get("page", 0) or None,
            )
            sections.append(
                SectionAsset(
                    id=sec_id,
                    title=title,
                    level=item.get("level", 1),
                    page=item.get("page", 0),
                    start_line=section_span.start_line if section_span else 0,
                    end_line=section_span.end_line if section_span else 0,
                    preview=(
                        line_index.extract_preview(
                            section_span.start_line,
                            section_span.end_line,
                        )
                        if section_span is not None
                        else ""
                    ),
                )
            )
            existing_ids.add(sec_id)

        return sections

    async def _extract_and_save_images(
        self, doc_id: str, pdf_path: Path
    ) -> list[FigureAsset]:
        """Extract images from PDF, filter small icons, and associate captions."""
        figures = []

        raw_images = self.pdf_extractor.extract_images(pdf_path)

        # Detect source from extractor type
        source = "pymupdf"
        if hasattr(self.pdf_extractor, "config"):
            source = "docling"

        # Extract figure captions for association
        page_captions: dict[int, list[dict]] = {}
        if hasattr(self.pdf_extractor, "extract_figure_captions"):
            page_captions = self.pdf_extractor.extract_figure_captions(pdf_path)

        # Track which captions have been used (per page)
        used_captions: dict[int, set[int]] = {}

        for img_data in raw_images:
            w = img_data["width"]
            h = img_data["height"]

            # Filter small images (icons, logos, decorations)
            min_px = 50
            if hasattr(self.pdf_extractor, "profile"):
                min_px = self.pdf_extractor.profile.filters.min_figure_px
            elif hasattr(self.pdf_extractor, "_MIN_FIGURE_PX"):
                min_px = self.pdf_extractor._MIN_FIGURE_PX
            if w < min_px or h < min_px:
                continue

            # Generate figure ID: fig_{page}_{index}
            fig_id = f"fig_{img_data['page']}_{img_data['index_on_page']}"

            # Save image
            image_path = self.repository.save_image(
                doc_id=doc_id,
                image_id=fig_id,
                data=img_data["image_bytes"],
                ext=img_data["ext"],
            )

            # Associate caption: pick next unused caption on same page
            caption = img_data.get("caption", "")
            if not caption:
                page_num = img_data["page"]
                caps = page_captions.get(page_num, [])
                if page_num not in used_captions:
                    used_captions[page_num] = set()
                for idx, cap in enumerate(caps):
                    if idx not in used_captions[page_num]:
                        caption = cap["caption"]
                        used_captions[page_num].add(idx)
                        break

            figures.append(
                FigureAsset(
                    id=fig_id,
                    page=img_data["page"],
                    path=str(image_path),
                    ext=img_data["ext"],
                    width=w,
                    height=h,
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

    async def delete_document(self, doc_id: str) -> dict[str, Any]:
        """Delete a stored PDF document and its local artifacts."""
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            return {"success": False, "error": f"Document not found: {doc_id}"}

        deleted = self.repository.delete_document(doc_id)
        if not deleted:
            return {
                "success": False,
                "error": f"Failed to delete document directory for {doc_id}",
            }

        warnings: list[str] = []
        if self.knowledge_graph and self.knowledge_graph.is_available:
            warnings.append(
                "Knowledge graph entries were not removed; only local document artifacts were deleted."
            )

        return {
            "success": True,
            "doc_id": doc_id,
            "filename": manifest.filename,
            "warnings": warnings,
        }

    async def convert_pdf_to_docx(
        self,
        doc_id: str,
        output_path: str | None = None,
        *,
        mode: str = "content",
    ) -> dict[str, Any]:
        """
        Convert an ingested PDF document to DOCX.

        Supported modes:
        - ``content``: rebuild a readable DOCX from extracted markdown and figures.
        - ``fidelity``: currently unsupported because PDF ETL is not layout-reversible.
        """
        if mode != "content":
            return {
                "success": False,
                "error": (
                    "PDF → DOCX currently supports content mode only. "
                    "Layout-fidelity reconstruction is not available."
                ),
            }

        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            return {"success": False, "error": f"Document not found: {doc_id}"}

        markdown = self.repository.load_markdown(doc_id)
        if markdown is None:
            return {
                "success": False,
                "error": f"Markdown content not found for {doc_id}",
            }

        doc_dir = self.repository.get_doc_dir(doc_id)
        out_path = (
            Path(output_path)
            if output_path is not None
            else doc_dir / "converted_from_pdf.docx"
        )

        try:
            self._build_docx_from_markdown(markdown, manifest, out_path)
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {
            "success": True,
            "doc_id": doc_id,
            "output_path": str(out_path),
            "mode": mode,
            "figures_embedded": len(manifest.assets.figures),
            "tables_found": len(manifest.assets.tables),
        }

    def _build_docx_from_markdown(
        self,
        markdown: str,
        manifest: DocumentManifest,
        output_path: Path,
    ) -> None:
        """Render extracted markdown into a readable DOCX document."""
        from docx import Document
        from docx.enum.text import WD_BREAK
        from docx.shared import Cm

        document = Document()
        if manifest.title:
            document.add_heading(manifest.title, level=0)
            document.core_properties.title = manifest.title

        lines = markdown.splitlines()
        index = 0
        while index < len(lines):
            raw_line = lines[index].rstrip()
            stripped = raw_line.strip()

            if not stripped:
                index += 1
                continue

            if stripped.startswith("<!--") and stripped.endswith("-->"):
                if stripped.lower().startswith("<!-- page") and document.paragraphs:
                    document.paragraphs[-1].add_run().add_break(WD_BREAK.PAGE)
                index += 1
                continue

            if stripped.startswith("#"):
                level = min(len(stripped) - len(stripped.lstrip("#")), 9)
                document.add_heading(stripped[level:].strip(), level=level)
                index += 1
                continue

            if self._is_table_start(lines, index):
                index = self._append_markdown_table(document, lines, index)
                continue

            if self._is_list_item(stripped):
                index = self._append_markdown_list(document, lines, index)
                continue

            paragraph_lines = [stripped]
            index += 1
            while index < len(lines):
                next_line = lines[index].strip()
                if (
                    not next_line
                    or next_line.startswith(("<!--", "#"))
                    or self._is_list_item(next_line)
                    or self._is_table_start(lines, index)
                ):
                    break
                paragraph_lines.append(next_line)
                index += 1

            document.add_paragraph(" ".join(paragraph_lines))

        if manifest.assets.figures:
            document.add_page_break()
            document.add_heading("Extracted Figures", level=1)
            for figure in manifest.assets.figures:
                if figure.caption:
                    document.add_paragraph(figure.caption)
                figure_path = Path(figure.path)
                if figure_path.exists():
                    with figure_path.open("rb"):
                        document.add_picture(str(figure_path), width=Cm(15))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        document.save(str(output_path))

    @staticmethod
    def _is_list_item(line: str) -> bool:
        return bool(re.match(r"^([-*+]\s+|\d+[.)]\s+)", line))

    @staticmethod
    def _is_table_start(lines: list[str], index: int) -> bool:
        if index + 1 >= len(lines):
            return False
        header = lines[index].strip()
        separator = lines[index + 1].strip()
        return (
            header.startswith("|")
            and header.endswith("|")
            and separator.startswith("|")
            and separator.endswith("|")
            and set(separator.replace("|", "").replace(" ", "")) <= {"-", ":"}
        )

    @staticmethod
    def _split_markdown_row(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    def _append_markdown_table(
        self, document: Any, lines: list[str], index: int
    ) -> int:
        header_cells = self._split_markdown_row(lines[index])
        index += 2  # Skip header + separator

        rows: list[list[str]] = []
        while index < len(lines):
            current = lines[index].strip()
            if not (current.startswith("|") and current.endswith("|")):
                break
            rows.append(self._split_markdown_row(current))
            index += 1

        table = document.add_table(rows=1, cols=len(header_cells))
        table.style = "Table Grid"
        for col_index, value in enumerate(header_cells):
            table.rows[0].cells[col_index].text = value

        for row in rows:
            cells = table.add_row().cells
            for col_index, value in enumerate(row[: len(header_cells)]):
                cells[col_index].text = value

        return index

    def _append_markdown_list(self, document: Any, lines: list[str], index: int) -> int:
        while index < len(lines):
            stripped = lines[index].strip()
            if not self._is_list_item(stripped):
                break
            style = (
                "List Number" if re.match(r"^\d+[.)]\s+", stripped) else "List Bullet"
            )
            text = re.sub(r"^([-*+]\s+|\d+[.)]\s+)", "", stripped)
            document.add_paragraph(text, style=style)
            index += 1
        return index
