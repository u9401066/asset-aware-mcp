"""Synthetic PDF truth and rendering shared by SDK and real-agent evaluations."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf as fitz

COLUMNS = ("Sample", "Count", "Reading", "Unit", "Flag")
TOOLS = (
    "document",
    "document_asset",
    "get_job_status",
    "table_manage",
    "table_data",
    "table_cite",
)
PAGE_ROWS = (
    (
        ("A101", "007", "-0.50", "mg/L", "OK"),
        ("A102", "12", "1,234.50", "mg/L", "HIGH"),
    ),
    (
        ("B201", "003", "0", "µg/mL", "ZERO"),
        ("B202", "18", "12.5%", "%", "REVIEW"),
        ("B203", "9", "<0.01", "mg/L", "LOW"),
    ),
    (("C301", "001", "N/A", "mg/L", "MISSING"), ("C302", "20", "2.00", "mg/L", "OK")),
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_rows() -> list[dict[str, str]]:
    return [dict(zip(COLUMNS, row, strict=True)) for page in PAGE_ROWS for row in page]


def _table_page(document: fitz.Document, index: int) -> fitz.Page:
    page = document.new_page(width=612, height=792)
    page.insert_text(
        (45, 65), f"Synthetic laboratory inventory - sheet {index + 1}", fontsize=16
    )
    page.insert_text(
        (45, 90),
        "Test data only. Preserve displayed values and units exactly.",
        fontsize=11,
    )
    rows = (COLUMNS, *PAGE_ROWS[index])
    xs = (45, 145, 225, 355, 465, 567)
    for row_index in range(len(rows) + 1):
        y = 140 + row_index * 45
        page.draw_line((xs[0], y), (xs[-1], y))
    for x in xs:
        page.draw_line((x, 140), (x, 140 + len(rows) * 45))
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            page.insert_text(
                (xs[column_index] + 8, 169 + row_index * 45), value, fontsize=12
            )
    page.insert_text(
        (45, 380),
        "Source transcription and later edits must remain distinguishable.",
        fontsize=10,
    )
    return page


def build_pdf(path: Path, mode: str = "mixed") -> None:
    """Render digital, scanned or mixed pages; scans have no hidden text layer."""
    if mode not in {"digital", "scanned", "mixed"}:
        raise ValueError(f"Unknown fixture mode: {mode}")
    with fitz.open() as source, fitz.open() as result:
        for index in range(len(PAGE_ROWS)):
            page = _table_page(source, index)
            raster = mode == "scanned" or (mode == "mixed" and index > 0)
            if raster:
                target = result.new_page(width=612, height=792)
                target.insert_image(
                    target.rect,
                    stream=page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png"),
                )
            else:
                result.insert_pdf(source, from_page=index, to_page=index)
            if index == 2:
                result[-1].set_cropbox(fitz.Rect(20, 30, 592, 762))
                result[-1].set_rotation(90)
        result.save(path)


def server_environment(data_dir: Path) -> dict[str, str]:
    """Explicit isolated stores and positive production process boundaries."""
    return {
        "DATA_DIR": str(data_dir),
        "TABLE_OUTPUT_DIR": str(data_dir / "tables"),
        "ENABLE_LIGHTRAG": "false",
        "ETL_ENGINE": "pymupdf",
        "ASSET_AWARE_MCP_TOOL_SURFACE": "balanced",
        "ASSET_AWARE_DISABLE_DOTENV": "true",
        "PYMUPDF_TEXT_DOCUMENT_TIMEOUT_SECONDS": "30",
        "PYMUPDF_IMAGE_DOCUMENT_TIMEOUT_SECONDS": "25",
        "PYMUPDF_FAST_IMAGE_DOCUMENT_TIMEOUT_SECONDS": "90",
        "PYMUPDF_TABLE_DOCUMENT_TIMEOUT_SECONDS": "25",
        "PYMUPDF_CAPTION_DOCUMENT_TIMEOUT_SECONDS": "20",
        "PYMUPDF_SAFETY_AUDIT_DOCUMENT_TIMEOUT_SECONDS": "20",
        "PYMUPDF_NATIVE_STRUCTURE_DOCUMENT_TIMEOUT_SECONDS": "10",
        "PYMUPDF_TABLE_TIMEOUT_SECONDS": "4",
        "PYMUPDF_IMAGE_TIMEOUT_SECONDS": "3",
        "PYMUPDF_ENABLE_VECTOR_IMAGES": "true",
        "PYMUPDF_ENABLE_REGION_IMAGES": "true",
        "PYMUPDF_FIGURE_CROP_ZOOM": "2",
        "PYTHONIOENCODING": "utf-8",
    }
