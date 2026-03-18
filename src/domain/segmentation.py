"""Domain models for a unified document segmentation schema."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentSegment(BaseModel):
    """A normalized document segment derived from blocks and manifest assets."""

    segment_id: str = Field(..., description="Stable segment identifier")
    segment_type: str = Field(
        ..., description="Normalized type, e.g. Text/Table/Picture"
    )
    page_number: int = Field(..., description="1-indexed page number")
    left: float | None = Field(None, description="Left coordinate in page space")
    top: float | None = Field(None, description="Top coordinate in page space")
    width: float | None = Field(None, description="Segment width")
    height: float | None = Field(None, description="Segment height")
    text: str = Field("", description="Segment text content")
    asset_id: str = Field("", description="Linked asset identifier if available")
    reading_order: int = Field(0, description="Reading order within the page")
    line_start: int | None = Field(None, description="0-based start line in markdown")
    line_end: int | None = Field(None, description="0-based end line in markdown")
    section_hierarchy: list[str] = Field(
        default_factory=list,
        description="Section hierarchy path for the segment",
    )
    source_backend: str = Field("", description="Source backend, e.g. pymupdf/marker")
    metadata: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict,
        description="Additional segment metadata",
    )


class DocumentSegmentation(BaseModel):
    """Unified segmentation schema for downstream tools and clients."""

    doc_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    title: str = Field("", description="Detected title")
    page_count: int = Field(0, description="Total number of pages")
    source_backend: str = Field("", description="Primary extraction backend")
    reading_order_policy: str = Field("", description="Reading order policy version")
    generated_at: datetime = Field(default_factory=datetime.now)
    segments: list[DocumentSegment] = Field(default_factory=list)

    def page_count_summary(self) -> dict[int, int]:
        """Return segment counts by page."""
        counts: dict[int, int] = {}
        for segment in self.segments:
            counts[segment.page_number] = counts.get(segment.page_number, 0) + 1
        return counts
