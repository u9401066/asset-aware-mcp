"""Helpers for mixed-format (PDF + DOCX/DOC/ODT/ODS) batch ingestion jobs.

Agents often hold a batch of heterogeneous document paths (some PDFs, some
Word docs, maybe a legacy .doc/.odt/.ods). `ingest_documents` only understands
PDFs, and `ingest_docx` only ingests one DOCX-family file at a time with no
job/progress tracking. This module lets `document(op="auto"/"ingest"/"import")`
route a mixed `file_paths` list through a single background job that:

- Classifies every path by extension and calls the correct existing ingester
  (PyMuPDF/Marker ETL for PDFs, DFM ingest with LibreOffice auto-conversion
  for DOCX/DOC/ODT/ODS) -- no new extraction logic, just routing.
- Isolates per-file failures (bad file, unsupported extension, ingest error)
  into `failed_files` so one broken input cannot abort the rest of the batch.
- Reports `[i/N] filename` progress after every file via the same
  `JobProgressReporter` used by conversion jobs, trackable with the existing
  `get_job_status(job_id)` tool -- no new public MCP tool needed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.application.document_service import DocumentService
    from src.application.docx_service import DocxService
    from src.application.job_service import JobProgressReporter

MixedIngestHandler = Callable[["JobProgressReporter"], Awaitable[dict[str, Any]]]

PDF_EXTENSIONS = frozenset({".pdf"})
DOCX_EXTENSIONS = frozenset({".docx", ".doc", ".odt", ".ods"})


def classify_document_path(file_path: str) -> str:
    """Classify a path as ``"pdf"``, ``"docx"``, or ``"unsupported"``."""
    suffix = Path(file_path).suffix.lower()
    if suffix in PDF_EXTENSIONS:
        return "pdf"
    if suffix in DOCX_EXTENSIONS:
        return "docx"
    return "unsupported"


def is_mixed_or_non_pdf_batch(file_paths: list[str]) -> bool:
    """True when the batch needs format-aware routing (not PDF-only).

    An all-PDF batch keeps using the existing `ingest_documents` path
    unchanged; anything else (any DOCX/DOC/ODT/ODS or unsupported path mixed
    in) routes through the mixed-batch handler in this module instead.
    """
    return any(classify_document_path(path) != "pdf" for path in file_paths)


def format_counts(file_paths: list[str]) -> dict[str, int]:
    """Count files per classified format, for a human-readable job summary."""
    counts: dict[str, int] = {}
    for path in file_paths:
        fmt = classify_document_path(path)
        counts[fmt] = counts.get(fmt, 0) + 1
    return counts


def build_mixed_ingest_handler(
    file_paths: list[str],
    *,
    document_service: DocumentService,
    docx_service: DocxService,
    use_marker: bool = False,
    ocr_enabled: bool = False,
    ocr_language: str = "eng",
    rotate_pages: bool = False,
    deskew: bool = False,
    marker_max_pages_per_chunk: int = 0,
    extract_figures: bool = True,
    index_knowledge_graph: bool = False,
    page_ranges: list[str] | None = None,
) -> MixedIngestHandler:
    """Build a `create_conversion_job` handler for a mixed PDF/DOCX batch.

    The returned handler's `result` dict deliberately reuses the same
    `documents` / `failed_files` / `warnings` keys that the PDF-only
    `_process_ingest_job` batch path already produces, so `get_job_status`
    renders it with zero changes to job-status rendering.
    """
    total = len(file_paths)

    async def handler(reporter: JobProgressReporter) -> dict[str, Any]:
        documents: list[dict[str, Any]] = []
        failed_files: list[dict[str, Any]] = []
        all_warnings: list[str] = []

        for index, file_path in enumerate(file_paths, start=1):
            filename = Path(file_path).name
            file_format = classify_document_path(file_path)
            await reporter.report(
                step=index,
                phase="Ingesting",
                message=f"[{index}/{total}] ({file_format}) {filename}",
            )

            try:
                if file_format == "pdf":
                    results = await document_service.ingest(
                        [file_path],
                        use_marker=use_marker,
                        ocr_enabled=ocr_enabled,
                        ocr_language=ocr_language,
                        rotate_pages=rotate_pages,
                        deskew=deskew,
                        marker_max_pages_per_chunk=marker_max_pages_per_chunk,
                        extract_figures=extract_figures,
                        index_knowledge_graph=index_knowledge_graph,
                        page_ranges=page_ranges,
                    )
                    result = results[0] if results else None
                    if result is not None and result.success:
                        documents.append(
                            {
                                "file": file_path,
                                "doc_id": result.doc_id,
                                "backend": result.backend,
                                "format": "pdf",
                                "warnings": list(result.warnings),
                            }
                        )
                        all_warnings.extend(result.warnings)
                    else:
                        error_msg = (
                            result.error
                            if result is not None and result.error
                            else "No result returned"
                        )
                        failed_files.append({"file": file_path, "error": error_msg})
                elif file_format == "docx":
                    docx_result = await docx_service.ingest_docx(file_path)
                    if docx_result.get("success"):
                        documents.append(
                            {
                                "file": file_path,
                                "doc_id": docx_result.get("doc_id", ""),
                                "backend": "docx",
                                "format": "docx",
                                "warnings": [],
                            }
                        )
                    else:
                        failed_files.append(
                            {
                                "file": file_path,
                                "error": docx_result.get(
                                    "error", "Unknown DOCX ingest error"
                                ),
                            }
                        )
                else:
                    suffix = Path(file_path).suffix or "(no extension)"
                    failed_files.append(
                        {
                            "file": file_path,
                            "error": (
                                f"Unsupported file type {suffix!r}. Supported: "
                                ".pdf, .docx, .doc, .odt, .ods."
                            ),
                        }
                    )
            except Exception as exc:
                # Isolate per-file failures so one bad input cannot abort the
                # rest of the batch or the job itself.
                failed_files.append({"file": file_path, "error": str(exc)})

        return {
            "success": True,
            "conversion": {
                "operation": "ingest_mixed_batch",
                "total": total,
                "succeeded": len(documents),
                "failed": len(failed_files),
            },
            "documents": documents,
            "failed_files": failed_files,
            "warnings": all_warnings,
        }

    return handler
