"""Build OpenDataloader-inspired PDF audit artifacts without new MCP tools."""

from __future__ import annotations

import json
import logging
import os
from collections import Counter
from datetime import datetime
from typing import TYPE_CHECKING, Any

from src.application.output_paths import resolve_document_output_path
from src.application.segmentation_service import (
    DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES,
    SEGMENTATION_SOURCE_LOAD_MAX_BYTES_ENV,
)

PDF_REPORT_GENERATOR = "asset-aware-mcp"
SEGMENTATION_COVERAGE_REPORT_VERSION = "segmentation-coverage-v1"
PDF_REPORT_MAX_BYTES_ENV = "ASSET_AWARE_PDF_REPORT_MAX_BYTES"
DEFAULT_PDF_REPORT_MAX_BYTES = 2 * 1024 * 1024
CORE_DOCUMENT_ARTIFACT_NAMES = {
    "blocks.json",
    "citation_index.jsonl",
    "citation_index.status.json",
    "segmentation.json",
}
PDF_REPORT_ARTIFACT_NAMES = {
    "ai_safety_report.json",
    "native_structure.json",
    "segmentation_coverage.json",
    "accessibility_report.json",
}

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path


class PdfArtifactReportService:
    """Create document-scoped safety, structure, and coverage JSON artifacts."""

    def __init__(self, repository: Any, pdf_extractor: Any):
        self.repository = repository
        self.pdf_extractor = pdf_extractor

    def build_and_save_ai_safety_report(
        self,
        doc_id: str,
        *,
        output_path: str | None = None,
        source_pdf_path: Path | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        manifest, doc_dir, pdf_path = self._load_manifest_and_pdf(
            doc_id, source_pdf_path
        )
        if hasattr(self.pdf_extractor, "audit_ai_safety"):
            try:
                report = dict(self.pdf_extractor.audit_ai_safety(pdf_path))
            except Exception as exc:
                logger.warning(
                    "PDF AI safety audit failed for %s",
                    doc_id,
                    exc_info=True,
                )
                report = self._unavailable_report("pdf-ai-safety-v1", str(exc))
        else:
            report = self._unavailable_report(
                "pdf-ai-safety-v1",
                "PDF extractor does not expose audit_ai_safety",
            )
        report.update(self._document_metadata(manifest, pdf_path))
        target = self._write_report(
            doc_dir,
            output_path,
            default_name="ai_safety_report.json",
            report=report,
        )
        return target, report

    def build_and_save_native_structure_report(
        self,
        doc_id: str,
        *,
        output_path: str | None = None,
        source_pdf_path: Path | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        manifest, doc_dir, pdf_path = self._load_manifest_and_pdf(
            doc_id, source_pdf_path
        )
        if hasattr(self.pdf_extractor, "extract_native_structure"):
            try:
                report = dict(self.pdf_extractor.extract_native_structure(pdf_path))
            except Exception as exc:
                logger.warning(
                    "Native PDF structure extraction failed for %s",
                    doc_id,
                    exc_info=True,
                )
                report = self._unavailable_report("pdf-native-structure-v1", str(exc))
        else:
            report = self._unavailable_report(
                "pdf-native-structure-v1",
                "PDF extractor does not expose extract_native_structure",
            )
        report.setdefault("status", "ok")
        report.update(self._document_metadata(manifest, pdf_path))
        target = self._write_report(
            doc_dir,
            output_path,
            default_name="native_structure.json",
            report=report,
        )
        return target, report

    async def build_and_save_segmentation_coverage_report(
        self,
        doc_id: str,
        segmentation_service: Any,
        *,
        output_path: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            raise ValueError(f"Document not found: {doc_id}")
        doc_dir = self.repository.get_doc_dir(doc_id)
        segmentation = await segmentation_service.export_document_segmentation(doc_id)
        report = self._build_segmentation_coverage_report(
            manifest,
            doc_dir,
            segmentation,
        )
        target = self._write_report(
            doc_dir,
            output_path,
            default_name="segmentation_coverage.json",
            report=report,
        )
        return target, report

    async def build_and_save_accessibility_report(
        self,
        doc_id: str,
        segmentation_service: Any,
        *,
        output_path: str | None = None,
    ) -> tuple[Path, dict[str, Any]]:
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            raise ValueError(f"Document not found: {doc_id}")
        doc_dir = self.repository.get_doc_dir(doc_id)
        segmentation = await segmentation_service.export_document_segmentation(doc_id)
        report = self._build_accessibility_report(manifest, doc_dir, segmentation)
        target = self._write_report(
            doc_dir,
            output_path,
            default_name="accessibility_report.json",
            report=report,
        )
        return target, report

    def _load_manifest_and_pdf(
        self,
        doc_id: str,
        source_pdf_path: Path | None,
    ) -> tuple[Any, Path, Path]:
        manifest = self.repository.load_manifest(doc_id)
        if manifest is None:
            raise ValueError(f"Document not found: {doc_id}")
        doc_dir = self.repository.get_doc_dir(doc_id)
        pdf_path = source_pdf_path or self._default_pdf_path(doc_dir)
        if not pdf_path.exists():
            raise ValueError(f"Source PDF artifact not found: {pdf_path}")
        return manifest, doc_dir, pdf_path

    @staticmethod
    def _default_pdf_path(doc_dir: Path) -> Path:
        for name in ("selected_pages.pdf", "ocr_processed.pdf", "original.pdf"):
            candidate = doc_dir / name
            if candidate.exists():
                return candidate
        return doc_dir / "original.pdf"

    @staticmethod
    def _document_metadata(manifest: Any, pdf_path: Path) -> dict[str, Any]:
        return {
            "doc_id": manifest.doc_id,
            "filename": manifest.filename,
            "title": manifest.title,
            "source_pdf_sha256": manifest.source_pdf_sha256,
            "analyzed_pdf_sha256": _sha256_file(pdf_path),
            "selected_page_map": list(manifest.selected_page_map or []),
            "analyzed_pdf_path": str(pdf_path),
            "generated_at": datetime.now().isoformat(),
            "generator": PDF_REPORT_GENERATOR,
        }

    @staticmethod
    def _unavailable_report(schema_version: str, reason: str) -> dict[str, Any]:
        return {
            "schema_version": schema_version,
            "status": "unavailable",
            "summary": {"issue_count": 0},
            "issues": [],
            "reason": reason,
        }

    def _build_segmentation_coverage_report(
        self,
        manifest: Any,
        doc_dir: Path,
        segmentation: Any,
    ) -> dict[str, Any]:
        segments = list(segmentation.segments)
        total = len(segments)
        has_bbox = [
            segment
            for segment in segments
            if segment.left is not None
            and segment.top is not None
            and segment.width is not None
            and segment.height is not None
        ]
        has_line = [
            segment
            for segment in segments
            if segment.line_start is not None and segment.line_end is not None
        ]
        has_char = [
            segment
            for segment in segments
            if segment.char_start is not None and segment.char_end is not None
        ]
        has_byte = [
            segment
            for segment in segments
            if segment.byte_start is not None and segment.byte_end is not None
        ]
        linked_assets = [segment for segment in segments if segment.asset_id]
        type_counts = Counter(str(segment.segment_type) for segment in segments)
        page_counts = Counter(int(segment.page_number) for segment in segments)
        reading_order_gap_pages = self._reading_order_gap_pages(segments)
        artifact_status = self._artifact_status(doc_dir, segmentation)

        metrics = {
            "segment_count": total,
            "page_count": int(segmentation.page_count or manifest.page_count or 0),
            "pages_with_segments": sorted(page_counts),
            "segment_counts_by_page": {
                str(page): count for page, count in sorted(page_counts.items())
            },
            "segment_counts_by_type": dict(sorted(type_counts.items())),
            "bbox_coverage_ratio": self._ratio(len(has_bbox), total),
            "line_span_coverage_ratio": self._ratio(len(has_line), total),
            "char_span_coverage_ratio": self._ratio(len(has_char), total),
            "byte_span_coverage_ratio": self._ratio(len(has_byte), total),
            "asset_link_coverage_ratio": self._ratio(len(linked_assets), total),
            "reading_order_gap_pages": reading_order_gap_pages,
        }
        issues = self._coverage_issues(total, metrics, artifact_status)
        return {
            "schema_version": SEGMENTATION_COVERAGE_REPORT_VERSION,
            "status": "warning" if issues else "ok",
            "doc_id": manifest.doc_id,
            "filename": manifest.filename,
            "title": manifest.title,
            "source_backend": segmentation.source_backend,
            "reading_order_policy": segmentation.reading_order_policy,
            "source_revision_id": segmentation.source_revision_id,
            "locator_version": segmentation.locator_version,
            "locator_source_sha256": segmentation.locator_source_sha256,
            "generated_at": datetime.now().isoformat(),
            "generator": PDF_REPORT_GENERATOR,
            "metrics": metrics,
            "artifacts": artifact_status,
            "issues": issues,
        }

    def _build_accessibility_report(
        self,
        manifest: Any,
        doc_dir: Path,
        segmentation: Any,
    ) -> dict[str, Any]:
        figures = list(manifest.assets.figures)
        tables = list(manifest.assets.tables)
        sections = list(manifest.assets.sections)
        segments = list(segmentation.segments)
        figure_captioned = [figure for figure in figures if figure.caption.strip()]
        figure_bbox = [figure for figure in figures if figure.figure_bbox]
        figure_caption_bbox = [figure for figure in figures if figure.caption_bbox]
        table_captioned = [table for table in tables if table.caption.strip()]
        line_segments = [
            segment
            for segment in segments
            if segment.line_start is not None and segment.line_end is not None
        ]
        text_segments = [segment for segment in segments if segment.text.strip()]
        asset_segments = [segment for segment in segments if segment.asset_id]
        metrics = {
            "figure_count": len(figures),
            "figures_with_caption": len(figure_captioned),
            "figure_caption_coverage_ratio": self._ratio(
                len(figure_captioned), len(figures)
            ),
            "figures_with_bbox": len(figure_bbox),
            "figure_bbox_coverage_ratio": self._ratio(len(figure_bbox), len(figures)),
            "figures_with_caption_bbox": len(figure_caption_bbox),
            "figure_caption_bbox_coverage_ratio": self._ratio(
                len(figure_caption_bbox), len(figures)
            ),
            "table_count": len(tables),
            "tables_with_caption": len(table_captioned),
            "table_caption_coverage_ratio": self._ratio(
                len(table_captioned), len(tables)
            ),
            "section_count": len(sections),
            "segment_count": len(segments),
            "segments_with_text": len(text_segments),
            "segments_with_line_span": len(line_segments),
            "line_span_coverage_ratio": self._ratio(len(line_segments), len(segments)),
            "segments_with_asset_link": len(asset_segments),
            "asset_link_coverage_ratio": self._ratio(
                len(asset_segments), len(segments)
            ),
            "reading_order_gap_pages": self._reading_order_gap_pages(segments),
        }
        issues = self._accessibility_issues(metrics)
        return {
            "schema_version": "pdf-accessibility-v1",
            "status": "warning" if issues else "ok",
            "doc_id": manifest.doc_id,
            "filename": manifest.filename,
            "title": manifest.title,
            "source_revision_id": segmentation.source_revision_id,
            "locator_version": segmentation.locator_version,
            "locator_source_sha256": segmentation.locator_source_sha256,
            "source_pdf_sha256": manifest.source_pdf_sha256,
            "generated_at": datetime.now().isoformat(),
            "generator": PDF_REPORT_GENERATOR,
            "metrics": metrics,
            "artifacts": self._artifact_status(doc_dir, segmentation),
            "issues": issues,
        }

    @staticmethod
    def _ratio(value: int, total: int) -> float:
        if total <= 0:
            return 0.0
        return round(value / total, 4)

    @staticmethod
    def _reading_order_gap_pages(segments: list[Any]) -> list[int]:
        by_page: dict[int, list[int]] = {}
        for segment in segments:
            by_page.setdefault(int(segment.page_number), []).append(
                int(segment.reading_order or 0)
            )
        gap_pages: list[int] = []
        for page, orders in by_page.items():
            ordered = sorted(order for order in orders if order > 0)
            if ordered and ordered != list(range(1, len(ordered) + 1)):
                gap_pages.append(page)
        return sorted(gap_pages)

    @staticmethod
    def _coverage_issues(
        total: int,
        metrics: dict[str, Any],
        artifact_status: dict[str, Any],
    ) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if total == 0:
            issues.append({"severity": "warning", "reason": "no_segments"})
        if metrics["bbox_coverage_ratio"] < 0.5 and total:
            issues.append({"severity": "info", "reason": "low_bbox_coverage"})
        if metrics["line_span_coverage_ratio"] < 0.5 and total:
            issues.append({"severity": "info", "reason": "low_line_span_coverage"})
        if metrics["reading_order_gap_pages"]:
            issues.append({"severity": "warning", "reason": "reading_order_gaps"})
        if artifact_status.get("blocks_status") == "skipped_large":
            issues.append({"severity": "info", "reason": "blocks_skipped_large"})
        return issues

    @staticmethod
    def _accessibility_issues(metrics: dict[str, Any]) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        if metrics["figure_count"] and metrics["figure_caption_coverage_ratio"] < 1.0:
            issues.append({"severity": "warning", "reason": "missing_figure_captions"})
        if metrics["figure_count"] and metrics["figure_bbox_coverage_ratio"] < 1.0:
            issues.append({"severity": "info", "reason": "missing_figure_bbox"})
        if (
            metrics["figure_count"]
            and metrics["figure_caption_bbox_coverage_ratio"] < 1.0
        ):
            issues.append({"severity": "info", "reason": "missing_caption_bbox"})
        if metrics["table_count"] and metrics["table_caption_coverage_ratio"] < 1.0:
            issues.append({"severity": "warning", "reason": "missing_table_captions"})
        if metrics["segment_count"] and metrics["line_span_coverage_ratio"] < 0.8:
            issues.append({"severity": "info", "reason": "low_line_span_coverage"})
        if metrics["reading_order_gap_pages"]:
            issues.append({"severity": "warning", "reason": "reading_order_gaps"})
        return issues

    @staticmethod
    def _artifact_status(doc_dir: Path, segmentation: Any) -> dict[str, Any]:
        blocks_path = doc_dir / "blocks.json"
        markdown_path = doc_dir / f"{segmentation.doc_id}_full.md"
        max_bytes = _segmentation_max_bytes()
        blocks_status = "missing"
        blocks_bytes = 0
        if blocks_path.exists():
            blocks_bytes = blocks_path.stat().st_size
            blocks_status = (
                "skipped_large"
                if max_bytes > 0 and blocks_bytes > max_bytes
                else "loaded"
            )
        return {
            "blocks_path": str(blocks_path),
            "blocks_status": blocks_status,
            "blocks_bytes": blocks_bytes,
            "markdown_path": str(markdown_path),
            "markdown_exists": markdown_path.exists(),
            "source_load_max_bytes": max_bytes,
        }

    @staticmethod
    def _write_report(
        doc_dir: Path,
        output_path: str | None,
        *,
        default_name: str,
        report: dict[str, Any],
    ) -> Path:
        target = resolve_document_output_path(
            doc_dir,
            output_path,
            default_name=default_name,
            allowed_suffixes={".json"},
            reserved_names=_reserved_report_names(doc_dir.name, default_name),
        )
        target.write_text(_bounded_json_dump(report), encoding="utf-8")
        return target


def _reserved_report_names(doc_id: str, default_name: str) -> set[str]:
    reserved = set(CORE_DOCUMENT_ARTIFACT_NAMES)
    reserved.add(f"{doc_id}_manifest.json")
    reserved.update(PDF_REPORT_ARTIFACT_NAMES - {default_name})
    return reserved


def _segmentation_max_bytes() -> int:
    raw = os.environ.get(SEGMENTATION_SOURCE_LOAD_MAX_BYTES_ENV, "").strip()
    if not raw:
        return DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES
    try:
        return max(0, int(raw))
    except ValueError:
        return DEFAULT_SEGMENTATION_SOURCE_LOAD_MAX_BYTES


def _pdf_report_max_bytes() -> int:
    raw = os.environ.get(PDF_REPORT_MAX_BYTES_ENV, "").strip()
    if not raw:
        return DEFAULT_PDF_REPORT_MAX_BYTES
    try:
        return max(1024, int(raw))
    except ValueError:
        return DEFAULT_PDF_REPORT_MAX_BYTES


def _bounded_json_dump(report: dict[str, Any]) -> str:
    max_bytes = _pdf_report_max_bytes()
    bounded, truncated = _prebound_report_lists(report, keep=50)
    bounded = _truncate_long_strings(bounded, max_chars=4096)
    if truncated:
        bounded["truncated"] = True
    payload = json.dumps(bounded, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) <= max_bytes:
        return payload

    bounded, _truncated = _prebound_report_lists(report, keep=10)
    bounded["truncated"] = True
    bounded = _truncate_long_strings(bounded, max_chars=512)
    payload = json.dumps(bounded, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) <= max_bytes:
        return payload

    minimal = _minimal_report(report)
    payload = json.dumps(minimal, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) <= max_bytes:
        return payload

    tiny = _tiny_report(report)
    payload = json.dumps(tiny, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) <= max_bytes:
        return payload

    tiny = _truncate_long_strings(tiny, max_chars=96)
    payload = json.dumps(tiny, ensure_ascii=False, indent=2)
    if len(payload.encode("utf-8")) <= max_bytes:
        return payload

    return json.dumps(
        {
            "truncated": True,
            "summary": {"truncated": True, "reason": "max_report_bytes"},
        },
        ensure_ascii=False,
        indent=2,
    )


def _prebound_report_lists(
    report: dict[str, Any],
    *,
    keep: int,
) -> tuple[dict[str, Any], bool]:
    bounded: dict[str, Any] = {}
    truncated = False
    for key, value in report.items():
        if (
            key in {"issues", "pages", "outline"}
            and isinstance(value, list)
            and len(value) > keep
        ):
            bounded[f"{key}_omitted"] = len(value) - keep
            bounded[key] = value[:keep]
            truncated = True
            continue
        bounded[key] = value
    return bounded, truncated


def _truncate_report_lists(report: dict[str, Any], *, keep: int) -> dict[str, Any]:
    bounded, _truncated = _prebound_report_lists(report, keep=keep)
    return bounded


def _truncate_long_strings(value: Any, *, max_chars: int) -> Any:
    if isinstance(value, str):
        if len(value) <= max_chars:
            return value
        import hashlib

        return {
            "truncated": True,
            "chars": len(value),
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "preview": value[:max_chars],
        }
    if isinstance(value, list):
        return [_truncate_long_strings(item, max_chars=max_chars) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _truncate_long_strings(item, max_chars=max_chars)
            for key, item in value.items()
        }
    return value


def _minimal_report(report: dict[str, Any]) -> dict[str, Any]:
    keep_keys = (
        "schema_version",
        "status",
        "doc_id",
        "filename",
        "title",
        "source_pdf_sha256",
        "analyzed_pdf_sha256",
        "selected_page_map",
        "generated_at",
        "generator",
        "summary",
        "metrics",
    )
    minimal = {key: report[key] for key in keep_keys if key in report}
    minimal["truncated"] = True
    minimal["truncated_reason"] = "max_report_bytes"
    truncated = _truncate_long_strings(minimal, max_chars=256)
    return truncated if isinstance(truncated, dict) else minimal


def _tiny_report(report: dict[str, Any]) -> dict[str, Any]:
    keep_keys = (
        "schema_version",
        "status",
        "doc_id",
        "filename",
        "generated_at",
        "generator",
    )
    tiny = {key: report[key] for key in keep_keys if key in report}
    tiny["truncated"] = True
    tiny["truncated_reason"] = "max_report_bytes"
    tiny["summary"] = {"truncated": True, "reason": "max_report_bytes"}
    return tiny


def _sha256_file(path: Path) -> str:
    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()
