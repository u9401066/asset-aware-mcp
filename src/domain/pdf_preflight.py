"""Stable domain schema for PDF preflight and extraction routing."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PDF_PREFLIGHT_SCHEMA_VERSION: Literal["pdf-preflight-v1"] = "pdf-preflight-v1"

PageContentClass = Literal["native", "sparse", "image", "scanned", "hybrid"]
OCRReason = Literal[
    "no_text",
    "sparse_text",
    "image_dominant",
    "suspected_scanned_page",
    "suspected_garbled_text",
    "vector_only",
]
RecommendedPDFEngine = Literal["pymupdf", "pymupdf+ocr", "docling"]
PDFPreflightErrorCode = Literal[
    "file_not_found",
    "not_a_file",
    "invalid_pdf",
    "file_too_large",
    "encrypted_pdf",
    "page_limit_exceeded",
    "source_changed",
    "timeout",
    "parse_failed",
    "worker_failed",
]


class _StableModel(BaseModel):
    """Reject accidental schema expansion and keep reports immutable."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PDFCoordinateSystem(_StableModel):
    """Coordinate contract shared by every page locator in the report."""

    origin: Literal["top-left"] = "top-left"
    units: Literal["pdf-points"] = "pdf-points"
    page_number_base: Literal[1] = 1
    bbox_format: Literal["x0,y0,x1,y1"] = "x0,y0,x1,y1"
    x_axis: Literal["right"] = "right"
    y_axis: Literal["down"] = "down"
    rotation_basis: Literal["unrotated-cropbox"] = "unrotated-cropbox"


class PDFSourceIdentity(_StableModel):
    """Content-addressed identity of the exact source inspected."""

    filename: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class PDFInspectorIdentity(_StableModel):
    """Inspector implementation and backend version."""

    name: Literal["asset-aware-pymupdf-preflight"] = "asset-aware-pymupdf-preflight"
    backend: Literal["pymupdf"] = "pymupdf"
    backend_version: str


class PDFPageLocator(_StableModel):
    """A 1-based locator in top-left, unrotated crop-box page space."""

    page_number: int = Field(ge=1)
    page_bbox: tuple[float, float, float, float]
    content_bbox: tuple[float, float, float, float] | None = None
    rotation_degrees: Literal[0, 90, 180, 270] = 0

    @model_validator(mode="after")
    def validate_bounds(self) -> PDFPageLocator:
        """Reject non-finite, inverted, or off-page locator coordinates."""
        x0, y0, x1, y1 = self.page_bbox
        if not all(math.isfinite(value) for value in self.page_bbox):
            raise ValueError("page_bbox must contain finite coordinates")
        if x0 != 0.0 or y0 != 0.0 or x1 <= x0 or y1 <= y0:
            raise ValueError("page_bbox must be a positive top-left page rectangle")
        if self.content_bbox is None:
            return self
        cx0, cy0, cx1, cy1 = self.content_bbox
        if not all(math.isfinite(value) for value in self.content_bbox):
            raise ValueError("content_bbox must contain finite coordinates")
        if not (x0 <= cx0 < cx1 <= x1 and y0 <= cy0 < cy1 <= y1):
            raise ValueError("content_bbox must be contained by page_bbox")
        return self


class PDFPageMetrics(_StableModel):
    """Bounded signals used by the deterministic routing heuristic."""

    text_characters: int = Field(ge=0)
    word_count: int = Field(ge=0)
    text_block_count: int = Field(ge=0)
    raster_image_count: int = Field(ge=0)
    vector_drawing_count: int = Field(ge=0)
    raster_image_coverage_ratio: float = Field(ge=0.0, le=1.0)
    largest_raster_image_coverage_ratio: float = Field(ge=0.0, le=1.0)


class PDFPagePreflight(_StableModel):
    """Classification and extraction route for one source page."""

    locator: PDFPageLocator
    classification: PageContentClass
    metrics: PDFPageMetrics
    ocr_recommended: bool
    ocr_reasons: list[OCRReason] = Field(default_factory=list)
    recommended_engine: RecommendedPDFEngine

    @model_validator(mode="after")
    def validate_ocr_decision(self) -> PDFPagePreflight:
        """Keep the OCR decision and its evidence consistent."""
        if self.ocr_recommended != bool(self.ocr_reasons):
            raise ValueError(
                "ocr_recommended must match whether ocr_reasons are present"
            )
        return self


class PDFClassificationCounts(_StableModel):
    """Complete page-class histogram with stable keys."""

    native: int = Field(0, ge=0)
    sparse: int = Field(0, ge=0)
    image: int = Field(0, ge=0)
    scanned: int = Field(0, ge=0)
    hybrid: int = Field(0, ge=0)


class PDFPreflightReport(_StableModel):
    """Successful document-level preflight result."""

    schema_version: Literal["pdf-preflight-v1"] = PDF_PREFLIGHT_SCHEMA_VERSION
    status: Literal["ok"] = "ok"
    source: PDFSourceIdentity
    inspector: PDFInspectorIdentity
    coordinate_system: PDFCoordinateSystem = Field(default_factory=PDFCoordinateSystem)
    page_count: int = Field(ge=1)
    classification_counts: PDFClassificationCounts
    ocr_recommended: bool
    ocr_pages: list[int] = Field(default_factory=list)
    recommended_engine: RecommendedPDFEngine
    pages: list[PDFPagePreflight]

    @model_validator(mode="after")
    def validate_document_invariants(self) -> PDFPreflightReport:
        """Ensure aggregates cannot drift from their normalized page records."""
        if len(self.pages) != self.page_count:
            raise ValueError("page_count must equal the number of page records")
        page_numbers = [page.locator.page_number for page in self.pages]
        if page_numbers != list(range(1, self.page_count + 1)):
            raise ValueError("page locators must be sequential and 1-based")
        expected_ocr_pages = [
            page.locator.page_number for page in self.pages if page.ocr_recommended
        ]
        if self.ocr_pages != expected_ocr_pages:
            raise ValueError("ocr_pages must match page-level OCR decisions")
        if self.ocr_recommended != bool(expected_ocr_pages):
            raise ValueError("document OCR decision must match ocr_pages")
        expected_counts = {
            label: sum(page.classification == label for page in self.pages)
            for label in ("native", "sparse", "image", "scanned", "hybrid")
        }
        if self.classification_counts.model_dump() != expected_counts:
            raise ValueError("classification_counts must match page classifications")
        return self


class PDFPreflightFailure(_StableModel):
    """Stable presentation-safe error payload for a failed preflight."""

    schema_version: Literal["pdf-preflight-v1"] = PDF_PREFLIGHT_SCHEMA_VERSION
    status: Literal["error"] = "error"
    error_code: PDFPreflightErrorCode
    message: str


class PDFPreflightError(RuntimeError):
    """Typed failure raised by PDF preflight implementations."""

    def __init__(self, code: PDFPreflightErrorCode, message: str):
        super().__init__(message)
        self.code = code

    def as_failure(self) -> PDFPreflightFailure:
        """Convert the exception into the stable external error schema."""
        return PDFPreflightFailure(error_code=self.code, message=str(self))
