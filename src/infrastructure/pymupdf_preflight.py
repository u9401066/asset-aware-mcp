"""Process-isolated PyMuPDF preflight and extraction routing."""

from __future__ import annotations

import hashlib
import math
import multiprocessing
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Literal, cast

import pymupdf as fitz  # type: ignore[import-untyped]

from src.domain.pdf_preflight import (
    OCRReason,
    PageContentClass,
    PDFClassificationCounts,
    PDFInspectorIdentity,
    PDFPageLocator,
    PDFPageMetrics,
    PDFPagePreflight,
    PDFPreflightError,
    PDFPreflightErrorCode,
    PDFPreflightReport,
    PDFSourceIdentity,
    RecommendedPDFEngine,
)
from src.domain.repositories import PDFPreflightInterface

DEFAULT_PREFLIGHT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_FILE_BYTES = 256 * 1024 * 1024
DEFAULT_MAX_PAGES = 2_000
DEFAULT_MAX_LAYOUT_ITEMS_PER_PAGE = 100_000
DEFAULT_WORKER_MEMORY_BYTES = 1536 * 1024 * 1024

NATIVE_TEXT_MIN_CHARACTERS = 60
NATIVE_TEXT_MIN_WORDS = 5
NATIVE_TEXT_WORD_ASSIST_CHARACTERS = 30
SIGNIFICANT_VISUAL_COVERAGE = 0.18
IMAGE_DOMINANT_COVERAGE = 0.45
SCANNED_PAGE_COVERAGE = 0.72
MIN_VECTOR_DRAWINGS_FOR_VISUAL = 4
_HASH_CHUNK_SIZE = 1024 * 1024


def _preflight_worker(
    pdf_path: str,
    connection: Any,
    options: dict[str, int],
) -> None:
    """Inspect one PDF in an isolated child and return JSON-safe data."""
    try:
        _apply_worker_memory_limit(options["worker_memory_bytes"])
        inspector = PyMuPDFPreflightInspector(
            timeout_seconds=0,
            max_file_bytes=options["max_file_bytes"],
            max_pages=options["max_pages"],
            max_layout_items_per_page=options["max_layout_items_per_page"],
            worker_memory_bytes=0,
        )
        report = inspector._inspect_direct(Path(pdf_path))
        connection.send(("ok", report.model_dump(mode="json")))
    except PDFPreflightError as exc:
        connection.send(("error", exc.code, _bounded_message(str(exc))))
    except MemoryError:
        connection.send(
            (
                "error",
                "worker_failed",
                "PDF preflight exceeded its worker memory budget",
            )
        )
    except Exception as exc:  # pragma: no cover - defensive worker boundary
        connection.send(
            (
                "error",
                "parse_failed",
                _bounded_message(f"PDF preflight failed: {exc}"),
            )
        )
    finally:
        connection.close()


def _apply_worker_memory_limit(max_bytes: int) -> None:
    """Best-effort address-space cap on Linux; wall time remains cross-platform."""
    if max_bytes <= 0 or not sys.platform.startswith("linux"):
        return
    try:
        import resource

        _soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        target = max_bytes if hard == resource.RLIM_INFINITY else min(max_bytes, hard)
        resource.setrlimit(resource.RLIMIT_AS, (target, hard))
    except (ImportError, OSError, ValueError):
        # Process isolation, timeout, input-size and page caps still apply.
        return


def _bounded_message(message: str, limit: int = 500) -> str:
    normalized = " ".join(message.split())
    return normalized[:limit] or "PDF preflight failed"


class PyMuPDFPreflightInspector(PDFPreflightInterface):
    """Classify pages and recommend extraction routes without mutating a PDF.

    The public ``inspect`` method is process-isolated by default. Tests and
    trusted in-process callers may set ``timeout_seconds=0`` to use the same
    deterministic implementation directly.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = DEFAULT_PREFLIGHT_TIMEOUT_SECONDS,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_pages: int = DEFAULT_MAX_PAGES,
        max_layout_items_per_page: int = DEFAULT_MAX_LAYOUT_ITEMS_PER_PAGE,
        worker_memory_bytes: int = DEFAULT_WORKER_MEMORY_BYTES,
    ) -> None:
        if timeout_seconds < 0:
            raise ValueError("timeout_seconds must be >= 0")
        if max_file_bytes <= 0:
            raise ValueError("max_file_bytes must be > 0")
        if max_pages <= 0:
            raise ValueError("max_pages must be > 0")
        if max_layout_items_per_page <= 0:
            raise ValueError("max_layout_items_per_page must be > 0")
        if worker_memory_bytes < 0:
            raise ValueError("worker_memory_bytes must be >= 0")

        self.timeout_seconds = timeout_seconds
        self.max_file_bytes = max_file_bytes
        self.max_pages = max_pages
        self.max_layout_items_per_page = max_layout_items_per_page
        self.worker_memory_bytes = worker_memory_bytes

    def inspect(self, pdf_path: Path) -> PDFPreflightReport:
        """Inspect ``pdf_path`` with bounded work and a stable output schema."""
        path = Path(pdf_path)
        self._validate_source(path)
        if self.timeout_seconds == 0:
            return self._inspect_direct(path)

        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        process = context.Process(
            target=_preflight_worker,
            args=(
                str(path),
                sender,
                {
                    "max_file_bytes": self.max_file_bytes,
                    "max_pages": self.max_pages,
                    "max_layout_items_per_page": self.max_layout_items_per_page,
                    "worker_memory_bytes": self.worker_memory_bytes,
                },
            ),
            daemon=True,
        )
        process.start()
        sender.close()
        try:
            if not receiver.poll(self.timeout_seconds):
                self._stop_process(process)
                raise PDFPreflightError(
                    "timeout",
                    f"PDF preflight exceeded {self.timeout_seconds:.1f} seconds",
                )
            try:
                payload = receiver.recv()
            except EOFError as exc:
                self._stop_process(process)
                raise PDFPreflightError(
                    "worker_failed", "PDF preflight worker exited without a result"
                ) from exc
        finally:
            receiver.close()

        process.join(1.0)
        if process.is_alive():
            self._stop_process(process)

        if not isinstance(payload, tuple) or not payload:
            raise PDFPreflightError(
                "worker_failed", "PDF preflight worker returned an invalid result"
            )
        if payload[0] == "ok" and len(payload) == 2:
            try:
                return PDFPreflightReport.model_validate(payload[1])
            except Exception as exc:
                raise PDFPreflightError(
                    "worker_failed", "PDF preflight worker returned an invalid schema"
                ) from exc
        if payload[0] == "error" and len(payload) == 3:
            code = payload[1]
            if not isinstance(code, str):
                code = "worker_failed"
            raise PDFPreflightError(
                _coerce_error_code(code),
                str(payload[2]),
            )
        raise PDFPreflightError(
            "worker_failed", "PDF preflight worker returned an invalid result"
        )

    @staticmethod
    def _stop_process(process: Any) -> None:
        if process.is_alive():
            process.terminate()
        process.join(1.0)
        if process.is_alive() and hasattr(process, "kill"):
            process.kill()
            process.join(1.0)

    def _inspect_direct(self, pdf_path: Path) -> PDFPreflightReport:
        initial_stat = self._validate_source(pdf_path)
        source_sha256 = _sha256_file(pdf_path)
        pages: list[PDFPagePreflight] = []

        try:
            document = fitz.open(str(pdf_path))
        except Exception as exc:
            raise PDFPreflightError(
                "invalid_pdf", f"PyMuPDF could not open the PDF: {exc}"
            ) from exc

        try:
            if document.needs_pass:
                raise PDFPreflightError(
                    "encrypted_pdf",
                    "Encrypted PDFs require decryption before preflight",
                )
            page_count = len(document)
            if page_count < 1:
                raise PDFPreflightError("invalid_pdf", "PDF contains no pages")
            if page_count > self.max_pages:
                raise PDFPreflightError(
                    "page_limit_exceeded",
                    f"PDF has {page_count} pages; safety limit is {self.max_pages}",
                )

            for page_index in range(page_count):
                pages.append(self._inspect_page(document[page_index], page_index + 1))
        except PDFPreflightError:
            raise
        except Exception as exc:
            raise PDFPreflightError(
                "parse_failed", f"PyMuPDF could not inspect the PDF: {exc}"
            ) from exc
        finally:
            document.close()

        final_stat = self._validate_source(pdf_path)
        final_sha256 = _sha256_file(pdf_path)
        if _stat_identity(initial_stat) != _stat_identity(final_stat):
            raise PDFPreflightError(
                "source_changed", "PDF changed while preflight was running"
            )
        if source_sha256 != final_sha256:
            raise PDFPreflightError(
                "source_changed", "PDF bytes changed while preflight was running"
            )

        counts = Counter(page.classification for page in pages)
        ocr_pages = [page.locator.page_number for page in pages if page.ocr_recommended]
        return PDFPreflightReport(
            source=PDFSourceIdentity(
                filename=pdf_path.name,
                size_bytes=initial_stat.st_size,
                sha256=source_sha256,
            ),
            inspector=PDFInspectorIdentity(
                backend_version=str(getattr(fitz, "VersionBind", "unknown"))
            ),
            page_count=len(pages),
            classification_counts=PDFClassificationCounts(
                native=counts["native"],
                sparse=counts["sparse"],
                image=counts["image"],
                scanned=counts["scanned"],
                hybrid=counts["hybrid"],
            ),
            ocr_recommended=bool(ocr_pages),
            ocr_pages=ocr_pages,
            recommended_engine=_document_engine(pages),
            pages=pages,
        )

    def _validate_source(self, pdf_path: Path) -> Any:
        try:
            source_stat = pdf_path.stat()
        except FileNotFoundError as exc:
            raise PDFPreflightError(
                "file_not_found", f"PDF file not found: {pdf_path}"
            ) from exc
        except OSError as exc:
            raise PDFPreflightError(
                "invalid_pdf", f"Cannot read PDF metadata: {exc}"
            ) from exc
        if not pdf_path.is_file():
            raise PDFPreflightError("not_a_file", f"Not a file: {pdf_path}")
        if source_stat.st_size > self.max_file_bytes:
            raise PDFPreflightError(
                "file_too_large",
                (
                    f"PDF is {source_stat.st_size} bytes; safety limit is "
                    f"{self.max_file_bytes} bytes"
                ),
            )
        try:
            with pdf_path.open("rb") as handle:
                header = handle.read(5)
        except OSError as exc:
            raise PDFPreflightError("invalid_pdf", f"Cannot read PDF: {exc}") from exc
        if header != b"%PDF-":
            raise PDFPreflightError(
                "invalid_pdf", "Invalid PDF: missing leading %PDF- signature"
            )
        return source_stat

    def _inspect_page(self, page: fitz.Page, page_number: int) -> PDFPagePreflight:
        page_width = float(page.cropbox.width)
        page_height = float(page.cropbox.height)
        if page_width <= 0 or page_height <= 0:
            raise PDFPreflightError(
                "parse_failed", f"Page {page_number} has invalid dimensions"
            )
        page_rect = fitz.Rect(0.0, 0.0, page_width, page_height)

        words = page.get_text("words", sort=False)
        image_info = page.get_image_info(hashes=False, xrefs=False)
        drawings = page.get_drawings()
        for label, items in (
            ("text words", words),
            ("raster images", image_info),
            ("vector drawings", drawings),
        ):
            if len(items) > self.max_layout_items_per_page:
                raise PDFPreflightError(
                    "parse_failed",
                    (
                        f"Page {page_number} has {len(items)} {label}; "
                        f"safety limit is {self.max_layout_items_per_page}"
                    ),
                )

        text_values = [
            str(word[4]) for word in words if len(word) > 4 and str(word[4]).strip()
        ]
        text = " ".join(text_values)
        text_characters = sum(1 for char in text if not char.isspace())
        text_block_count = len(
            {
                int(word[5])
                for word in words
                if len(word) > 5 and isinstance(word[5], (int, float))
            }
        )

        word_rects = _valid_rects(
            [_clipped_rect(word[:4], page_rect) for word in words]
        )
        image_rects = _valid_rects(
            [
                _clipped_rect(info.get("bbox"), page_rect)
                for info in image_info
                if isinstance(info, dict)
            ]
        )
        drawing_rects = _valid_rects(
            [
                _clipped_rect(drawing.get("rect"), page_rect)
                for drawing in drawings
                if isinstance(drawing, dict)
            ]
        )

        page_area = page_width * page_height
        image_areas = [rect.get_area() for rect in image_rects]
        largest_image_coverage = (
            min(1.0, max(image_areas) / page_area) if image_areas else 0.0
        )
        image_coverage = min(1.0, sum(image_areas) / page_area)
        garbled = _suspected_garbled_text(text)
        has_native_text = not garbled and (
            text_characters >= NATIVE_TEXT_MIN_CHARACTERS
            or (
                text_characters >= NATIVE_TEXT_WORD_ASSIST_CHARACTERS
                and len(text_values) >= NATIVE_TEXT_MIN_WORDS
            )
        )
        has_text = text_characters > 0
        has_visual = (
            largest_image_coverage >= SIGNIFICANT_VISUAL_COVERAGE
            or len(drawing_rects) >= MIN_VECTOR_DRAWINGS_FOR_VISUAL
        )

        classification = _classify_page(
            has_native_text=has_native_text,
            has_text=has_text,
            has_visual=has_visual,
            largest_image_coverage=largest_image_coverage,
        )
        ocr_reasons = _ocr_reasons(
            classification=classification,
            has_native_text=has_native_text,
            has_text=has_text,
            garbled=garbled,
            image_count=len(image_rects),
            drawing_count=len(drawing_rects),
            largest_image_coverage=largest_image_coverage,
        )
        ocr_recommended = bool(ocr_reasons)
        recommended_engine = _page_engine(classification, ocr_recommended, ocr_reasons)
        content_bbox = _union_bbox(word_rects + image_rects + drawing_rects)

        normalized_content_bbox: tuple[float, float, float, float] | None = None
        if content_bbox is not None:
            normalized_content_bbox = (
                _round(content_bbox[0]),
                _round(content_bbox[1]),
                _round(content_bbox[2]),
                _round(content_bbox[3]),
            )

        return PDFPagePreflight(
            locator=PDFPageLocator(
                page_number=page_number,
                page_bbox=(0.0, 0.0, _round(page_width), _round(page_height)),
                content_bbox=normalized_content_bbox,
                rotation_degrees=_normalize_rotation(page.rotation),
            ),
            classification=classification,
            metrics=PDFPageMetrics(
                text_characters=text_characters,
                word_count=len(text_values),
                text_block_count=text_block_count,
                raster_image_count=len(image_rects),
                vector_drawing_count=len(drawing_rects),
                raster_image_coverage_ratio=_round(image_coverage, 6),
                largest_raster_image_coverage_ratio=_round(largest_image_coverage, 6),
            ),
            ocr_recommended=ocr_recommended,
            ocr_reasons=ocr_reasons,
            recommended_engine=recommended_engine,
        )


def _classify_page(
    *,
    has_native_text: bool,
    has_text: bool,
    has_visual: bool,
    largest_image_coverage: float,
) -> PageContentClass:
    if has_native_text and has_visual:
        return "hybrid"
    if not has_native_text and largest_image_coverage >= SCANNED_PAGE_COVERAGE:
        return "scanned"
    if has_text and has_visual:
        return "hybrid"
    if has_visual:
        return "image"
    if has_native_text:
        return "native"
    return "sparse"


def _ocr_reasons(
    *,
    classification: PageContentClass,
    has_native_text: bool,
    has_text: bool,
    garbled: bool,
    image_count: int,
    drawing_count: int,
    largest_image_coverage: float,
) -> list[OCRReason]:
    reasons: list[OCRReason] = []
    if garbled:
        reasons.append("suspected_garbled_text")

    if classification == "sparse":
        if has_text:
            reasons.append("sparse_text")
        return reasons

    if classification in {"image", "scanned", "hybrid"} and not has_native_text:
        reasons.append("sparse_text" if has_text else "no_text")
        if largest_image_coverage >= IMAGE_DOMINANT_COVERAGE:
            reasons.append("image_dominant")
        if classification == "scanned":
            reasons.append("suspected_scanned_page")
        if image_count == 0 and drawing_count >= MIN_VECTOR_DRAWINGS_FOR_VISUAL:
            reasons.append("vector_only")
    return _deduplicate(reasons)


def _page_engine(
    classification: PageContentClass,
    ocr_recommended: bool,
    reasons: list[OCRReason],
) -> RecommendedPDFEngine:
    if classification == "hybrid" or "vector_only" in reasons:
        return "docling"
    if ocr_recommended:
        return "pymupdf+ocr"
    return "pymupdf"


def _document_engine(pages: list[PDFPagePreflight]) -> RecommendedPDFEngine:
    recommendations = {page.recommended_engine for page in pages}
    if "docling" in recommendations:
        return "docling"
    if "pymupdf+ocr" in recommendations:
        return "pymupdf+ocr"
    return "pymupdf"


def _suspected_garbled_text(text: str) -> bool:
    characters = [char for char in text if not char.isspace()]
    if len(characters) < 8:
        return False
    suspicious = 0
    for char in characters:
        category = unicodedata.category(char)
        if char == "\ufffd" or category in {"Cc", "Co", "Cs"}:
            suspicious += 1
    return suspicious / len(characters) >= 0.20


def _clipped_rect(value: Any, page_rect: fitz.Rect) -> fitz.Rect | None:
    try:
        rect = fitz.Rect(value)
    except Exception:
        return None
    if not all(math.isfinite(item) for item in (rect.x0, rect.y0, rect.x1, rect.y1)):
        return None
    rect.normalize()
    clipped = rect & page_rect
    if clipped.is_empty or clipped.is_infinite or clipped.get_area() <= 0:
        return None
    return clipped


def _valid_rects(rects: list[fitz.Rect | None]) -> list[fitz.Rect]:
    return [rect for rect in rects if rect is not None]


def _union_bbox(rects: list[fitz.Rect]) -> tuple[float, float, float, float] | None:
    if not rects:
        return None
    return (
        min(rect.x0 for rect in rects),
        min(rect.y0 for rect in rects),
        max(rect.x1 for rect in rects),
        max(rect.y1 for rect in rects),
    )


def _deduplicate(values: list[OCRReason]) -> list[OCRReason]:
    return list(dict.fromkeys(values))


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _normalize_rotation(value: Any) -> Literal[0, 90, 180, 270]:
    normalized = int(value) % 360
    if normalized not in {0, 90, 180, 270}:
        normalized = 0
    return cast("Literal[0, 90, 180, 270]", normalized)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(_HASH_CHUNK_SIZE):
                digest.update(chunk)
    except OSError as exc:
        raise PDFPreflightError("invalid_pdf", f"Cannot hash PDF: {exc}") from exc
    return digest.hexdigest()


def _stat_identity(source_stat: Any) -> tuple[int, int, int, int]:
    return (
        int(source_stat.st_dev),
        int(source_stat.st_ino),
        int(source_stat.st_size),
        int(source_stat.st_mtime_ns),
    )


def _coerce_error_code(value: str) -> PDFPreflightErrorCode:
    allowed = {
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
    }
    if value in allowed:
        return cast("PDFPreflightErrorCode", value)
    return "worker_failed"
