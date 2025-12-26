"""
Domain Layer - Entities

Core business objects with identity.
"""

from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .value_objects import AssetType, ImageMediaType

# ============================================================================
# Asset Entities
# ============================================================================


class TableAsset(BaseModel):
    """Table asset extracted from document."""

    id: str = Field(..., description="Unique table ID, e.g., 'tab_1'")
    page: int = Field(..., description="Page number (1-indexed)")
    caption: str = Field("", description="Table caption if detected")
    preview: str = Field("", description="First 100 chars of table content")
    markdown: str = Field("", description="Full table in Markdown format")
    row_count: int = Field(0, description="Number of rows")
    col_count: int = Field(0, description="Number of columns")

    # Enhanced fields from Docling
    has_header: bool = Field(True, description="Whether table has header row")
    source: str = Field("pymupdf", description="Extraction source: docling/pymupdf")


class FigureAsset(BaseModel):
    """Figure/image asset extracted from document."""

    id: str = Field(..., description="Unique figure ID, e.g., 'fig_1_1'")
    page: int = Field(..., description="Page number (1-indexed)")
    path: str = Field(..., description="Local file path to the image")
    ext: str = Field("png", description="Image extension (png, jpg, etc.)")
    caption: str = Field("", description="Figure caption if detected")
    width: int = Field(0, description="Image width in pixels")
    height: int = Field(0, description="Image height in pixels")

    # Enhanced fields from Docling
    figure_type: str = Field("", description="Figure type: chart/diagram/photo/etc.")
    source: str = Field("pymupdf", description="Extraction source: docling/pymupdf")

    def to_base64(self) -> str:
        """Convert image to base64 string."""
        img_path = Path(self.path)
        if not img_path.exists():
            raise FileNotFoundError(f"Image not found: {self.path}")

        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def get_media_type(self) -> ImageMediaType:
        """Get MIME type for the image."""
        return ImageMediaType.from_extension(self.ext)

    def get_size_kb(self) -> float:
        """Get file size in KB."""
        img_path = Path(self.path)
        if img_path.exists():
            return img_path.stat().st_size / 1024
        return 0.0


class SectionAsset(BaseModel):
    """Section/heading asset extracted from document."""

    id: str = Field(..., description="Unique section ID, e.g., 'sec_introduction'")
    title: str = Field(..., description="Section heading text")
    level: int = Field(1, description="Heading level (1=H1, 2=H2, etc.)")
    page: int = Field(0, description="Starting page number")
    start_line: int = Field(0, description="Start line in markdown file")
    end_line: int = Field(0, description="End line in markdown file")
    preview: str = Field("", description="First 200 chars of section content")


# ============================================================================
# Aggregate: Document Assets
# ============================================================================


class DocumentAssets(BaseModel):
    """All assets in a document (Aggregate)."""

    tables: list[TableAsset] = Field(default_factory=list)
    figures: list[FigureAsset] = Field(default_factory=list)
    sections: list[SectionAsset] = Field(default_factory=list)

    def find_table(self, table_id: str) -> TableAsset | None:
        """Find a table by ID."""
        for table in self.tables:
            if table.id == table_id:
                return table
        return None

    def find_figure(self, figure_id: str) -> FigureAsset | None:
        """Find a figure by ID."""
        for figure in self.figures:
            if figure.id == figure_id:
                return figure
        return None

    def find_section(self, section_id_or_title: str) -> SectionAsset | None:
        """Find a section by ID or title (case-insensitive)."""
        search = section_id_or_title.lower()
        for section in self.sections:
            if section.id.lower() == search or section.title.lower() == search:
                return section
        return None

    def get_summary(self) -> dict[str, int]:
        """Get count of each asset type."""
        return {
            "tables": len(self.tables),
            "figures": len(self.figures),
            "sections": len(self.sections),
        }


# ============================================================================
# Aggregate Root: Document Manifest
# ============================================================================


class DocumentManifest(BaseModel):
    """
    Document Manifest - The Map for AI Agent.

    This is the Aggregate Root that contains all information
    about a processed document.
    """

    doc_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original PDF filename")
    title: str = Field("", description="Document title if detected")

    # Table of Contents
    toc: list[str] = Field(default_factory=list, description="List of section headings")

    # Assets (embedded aggregate)
    assets: DocumentAssets = Field(default_factory=DocumentAssets)

    # LightRAG enrichment
    lightrag_entities: list[str] = Field(
        default_factory=list, description="Top entities extracted by LightRAG"
    )

    # Metadata
    page_count: int = Field(0, description="Total number of pages")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @property
    def ingested_at(self) -> datetime:
        """Alias for created_at."""
        return self.created_at

    # File paths
    markdown_path: str = Field("", description="Path to full markdown file")
    manifest_path: str = Field("", description="Path to this manifest JSON")

    def get_asset_summary(self) -> dict[str, int]:
        """Get count of each asset type."""
        return self.assets.get_summary()


# ============================================================================
# Result Objects (for use case responses)
# ============================================================================


class IngestResult(BaseModel):
    """Result of document ingestion."""

    doc_id: str
    filename: str
    title: str = ""
    success: bool = True
    error: str | None = None
    manifest: DocumentManifest | None = None

    # Processing stats
    pages_processed: int = 0
    tables_found: int = 0
    figures_found: int = 0
    sections_found: int = 0
    processing_time_seconds: float = 0.0


class FetchResult(BaseModel):
    """Result of fetching an asset."""

    doc_id: str
    asset_type: AssetType
    asset_id: str
    success: bool = True
    error: str | None = None

    # Content (one of these will be populated)
    text_content: str | None = None
    image_base64: str | None = None
    image_media_type: str | None = None

    # Metadata for verification
    page: int | None = None
    width: int | None = None
    height: int | None = None

    def to_mcp_content(self) -> dict[str, Any]:
        """Convert to MCP-compatible content format."""
        if self.image_base64:
            return {
                "type": "image",
                "data": self.image_base64,
                "mimeType": self.image_media_type or "image/png",
            }
        else:
            return {
                "type": "text",
                "text": self.text_content or "",
            }


class DocumentSummary(BaseModel):
    """Summary of a document for listing."""

    doc_id: str
    filename: str
    title: str = ""
    page_count: int = 0
    table_count: int = 0
    figure_count: int = 0
    section_count: int = 0
    created_at: datetime = Field(default_factory=datetime.now)

    @property
    def ingested_at(self) -> datetime:
        """Alias for created_at."""
        return self.created_at
