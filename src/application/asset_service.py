"""
Application Layer - Asset Service

Use cases for fetching document assets.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from src.domain.entities import FetchResult
from src.domain.image_processor import DEFAULT_MAX_SIZE, process_image
from src.domain.repositories import DocumentRepository
from src.domain.services import AssetExtractor
from src.domain.value_objects import AssetType

if TYPE_CHECKING:
    pass


class AssetService:
    """
    Application service for asset retrieval.

    Provides precise data fetching:
    - Tables (markdown)
    - Figures (base64 with smart resizing)
    - Sections (text content)
    - Full text
    """

    def __init__(self, repository: DocumentRepository):
        """
        Initialize asset service.

        Args:
            repository: Document storage repository
        """
        self.repository = repository
        self.asset_extractor = AssetExtractor()

    async def fetch_asset(
        self,
        doc_id: str,
        asset_type: str,
        asset_id: str,
        max_size: int | None = None,
    ) -> FetchResult:
        """
        Fetch a specific asset from a document.

        Args:
            doc_id: Document identifier
            asset_type: Type of asset ("table", "figure", "section", "full_text")
            asset_id: Asset identifier (e.g., "tab_1", "fig_1_1", "sec_introduction")
            max_size: For figures - max longest edge in pixels
                      Default 1024, set to 0 for original size

        Returns:
            FetchResult with content or error
        """
        # Validate asset type
        try:
            atype = AssetType(asset_type)
        except ValueError:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.FULL_TEXT,  # Default
                asset_id=asset_id,
                success=False,
                error=f"Invalid asset type: {asset_type}",
            )

        # Check document exists
        if not self.repository.document_exists(doc_id):
            return FetchResult(
                doc_id=doc_id,
                asset_type=atype,
                asset_id=asset_id,
                success=False,
                error=f"Document not found: {doc_id}",
            )

        # Route to specific handler
        if atype == AssetType.TABLE:
            return await self._fetch_table(doc_id, asset_id)
        elif atype == AssetType.FIGURE:
            return await self._fetch_figure(doc_id, asset_id, max_size)
        elif atype == AssetType.SECTION:
            return await self._fetch_section(doc_id, asset_id)
        elif atype == AssetType.FULL_TEXT:
            return await self._fetch_full_text(doc_id)
        else:
            return FetchResult(
                doc_id=doc_id,
                asset_type=atype,
                asset_id=asset_id,
                success=False,
                error=f"Unsupported asset type: {asset_type}",
            )

    async def _fetch_table(self, doc_id: str, table_id: str) -> FetchResult:
        """Fetch a table by ID."""
        manifest = self.repository.load_manifest(doc_id)
        if not manifest:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.TABLE,
                asset_id=table_id,
                success=False,
                error="Manifest not found",
            )

        # Find table in manifest
        table = manifest.assets.find_table(table_id)
        if not table:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.TABLE,
                asset_id=table_id,
                success=False,
                error=f"Table not found: {table_id}",
            )

        return FetchResult(
            doc_id=doc_id,
            asset_type=AssetType.TABLE,
            asset_id=table_id,
            success=True,
            text_content=table.markdown,
            page=table.page,
        )

    async def _fetch_figure(
        self,
        doc_id: str,
        figure_id: str,
        max_size: int | None = None,
    ) -> FetchResult:
        """
        Fetch a figure by ID as base64.

        Smart resizing:
        - Default: 1024px longest edge (good for most VLMs)
        - Custom: specify max_size (e.g., 512 for smaller models)
        - Original: set max_size=0

        Args:
            doc_id: Document ID
            figure_id: Figure ID (e.g., "fig_1_1")
            max_size: Max longest edge in pixels (default 1024, 0=original)
        """
        manifest = self.repository.load_manifest(doc_id)
        if not manifest:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.FIGURE,
                asset_id=figure_id,
                success=False,
                error="Manifest not found",
            )

        # Find figure in manifest
        figure = manifest.assets.find_figure(figure_id)
        if not figure:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.FIGURE,
                asset_id=figure_id,
                success=False,
                error=f"Figure not found: {figure_id}",
            )

        # Load and process image
        try:
            image_path = Path(figure.path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {figure.path}")

            with open(image_path, "rb") as f:
                original_bytes = f.read()

            # Use default or custom max_size
            target_size = max_size if max_size is not None else DEFAULT_MAX_SIZE

            # Process image (resize + compress)
            result = process_image(original_bytes, max_size=target_size)

            # Build info text
            info = f"Page {figure.page}"
            if figure.caption:
                info += f" | {figure.caption}"
            if result.resized:
                info += f" | Resized: {result.original_width}x{result.original_height} → {result.width}x{result.height}"
                info += f" | {result.size_reduction_percent:.0f}% smaller"

            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.FIGURE,
                asset_id=figure_id,
                success=True,
                image_base64=result.base64,
                image_media_type="image/jpeg",
                page=figure.page,
                width=result.width,
                height=result.height,
                text_content=info,
            )

        except FileNotFoundError as e:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.FIGURE,
                asset_id=figure_id,
                success=False,
                error=str(e),
            )
        except ImportError:
            # PIL not installed - return original
            try:
                image_base64 = figure.to_base64()
                return FetchResult(
                    doc_id=doc_id,
                    asset_type=AssetType.FIGURE,
                    asset_id=figure_id,
                    success=True,
                    image_base64=image_base64,
                    image_media_type=figure.get_media_type().value,
                    page=figure.page,
                    width=figure.width,
                    height=figure.height,
                    text_content=f"Page {figure.page} (unprocessed - PIL not available)",
                )
            except Exception as e:
                return FetchResult(
                    doc_id=doc_id,
                    asset_type=AssetType.FIGURE,
                    asset_id=figure_id,
                    success=False,
                    error=str(e),
                )

    async def _fetch_section(self, doc_id: str, section_id: str) -> FetchResult:
        """Fetch a section by ID or title."""
        manifest = self.repository.load_manifest(doc_id)
        if not manifest:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.SECTION,
                asset_id=section_id,
                success=False,
                error="Manifest not found",
            )

        # Find section in manifest
        section = manifest.assets.find_section(section_id)
        if not section:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.SECTION,
                asset_id=section_id,
                success=False,
                error=f"Section not found: {section_id}",
            )

        # Load markdown and extract section content
        markdown = self.repository.load_markdown(doc_id)
        if not markdown:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.SECTION,
                asset_id=section_id,
                success=False,
                error="Markdown file not found",
            )

        content = self.asset_extractor.extract_section_content(markdown, section)

        return FetchResult(
            doc_id=doc_id,
            asset_type=AssetType.SECTION,
            asset_id=section_id,
            success=True,
            text_content=content,
            page=section.page,
        )

    async def _fetch_full_text(self, doc_id: str) -> FetchResult:
        """Fetch full document text."""
        markdown = self.repository.load_markdown(doc_id)
        if not markdown:
            return FetchResult(
                doc_id=doc_id,
                asset_type=AssetType.FULL_TEXT,
                asset_id="full",
                success=False,
                error="Markdown file not found",
            )

        return FetchResult(
            doc_id=doc_id,
            asset_type=AssetType.FULL_TEXT,
            asset_id="full",
            success=True,
            text_content=markdown,
        )
