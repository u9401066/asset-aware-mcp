"""Page range and page-number remapping helpers for document ingestion."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

PageRange = tuple[int, int]

_PAGE_MARKER_RE = re.compile(r"<!-- Page (\d+) -->")


def format_page_ranges(page_ranges: list[PageRange] | tuple[PageRange, ...]) -> str:
    """Format normalized inclusive page ranges for logs and doc_id scopes."""
    parts = []
    for start_page, end_page in page_ranges:
        if start_page == end_page:
            parts.append(str(start_page))
        else:
            parts.append(f"{start_page}-{end_page}")
    return ",".join(parts)


def build_page_number_map(
    page_ranges: list[PageRange] | tuple[PageRange, ...],
) -> list[int]:
    """Expand normalized ranges into a sequential subset-to-original page map."""
    page_numbers: list[int] = []
    for start_page, end_page in page_ranges:
        page_numbers.extend(range(start_page, end_page + 1))
    return page_numbers


def normalize_page_ranges(
    page_ranges: list[str] | None,
    total_pages: int,
) -> tuple[PageRange, ...]:
    """Validate and merge user-supplied 1-indexed inclusive page ranges."""
    if not page_ranges:
        return ()

    normalized: list[PageRange] = []
    for raw_spec in page_ranges:
        spec = raw_spec.strip()
        if not spec:
            continue

        if "-" in spec:
            start_text, end_text = spec.split("-", 1)
            start_page = int(start_text)
            end_page = int(end_text)
        else:
            start_page = int(spec)
            end_page = start_page

        if start_page < 1 or end_page < 1:
            raise ValueError("Page numbers must be >= 1")
        if start_page > end_page:
            raise ValueError(f"Invalid page range: {spec}")
        if end_page > total_pages:
            raise ValueError(
                f"Page range {spec} exceeds total page count {total_pages}"
            )

        normalized.append((start_page, end_page))

    if not normalized:
        return ()

    normalized.sort()
    merged: list[PageRange] = [normalized[0]]
    for start_page, end_page in normalized[1:]:
        prev_start, prev_end = merged[-1]
        if start_page <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, end_page))
        else:
            merged.append((start_page, end_page))
    return tuple(merged)


def remap_page_number(page_number: int, page_map: list[int] | None) -> int:
    """Translate subset-local page numbers back to original PDF page numbers."""
    if not page_map or page_number < 1 or page_number > len(page_map):
        return page_number
    return page_map[page_number - 1]


def build_doc_id_unique_suffix(
    source_path: Path,
    page_ranges: list[PageRange] | tuple[PageRange, ...] | None = None,
) -> str:
    """Build a stable DocId uniqueness suffix that includes page scoping."""
    suffix = str(source_path.absolute())
    if page_ranges:
        suffix = f"{suffix}#pages={format_page_ranges(page_ranges)}"
    return suffix


def materialize_pdf_page_subset(
    source_path: Path,
    output_path: Path,
    page_ranges: list[PageRange] | tuple[PageRange, ...],
) -> Path:
    """Persist a subset PDF containing only the requested inclusive page ranges."""
    import pymupdf as fitz  # type: ignore[import-untyped]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    subset_pdf = fitz.open()
    try:
        with fitz.open(str(source_path)) as source_pdf:
            for start_page, end_page in page_ranges:
                subset_pdf.insert_pdf(
                    source_pdf,
                    from_page=start_page - 1,
                    to_page=end_page - 1,
                )
        subset_pdf.save(output_path)
    finally:
        subset_pdf.close()
    return output_path


def remap_markdown_page_markers(markdown: str, page_map: list[int] | None) -> str:
    """Rewrite subset-local markdown page markers to original PDF numbers."""
    if not page_map:
        return markdown

    marker_index = 0

    def replace_page_marker(match: re.Match[str]) -> str:
        nonlocal marker_index
        if marker_index >= len(page_map):
            return match.group(0)
        original_page = page_map[marker_index]
        marker_index += 1
        return f"<!-- Page {original_page} -->"

    return _PAGE_MARKER_RE.sub(replace_page_marker, markdown)


def remap_toc_pages(
    toc: list[tuple[int, str, int]],
    page_map: list[int] | None,
) -> list[tuple[int, str, int]]:
    """Translate PDF TOC page numbers from subset-local to original numbering."""
    if not page_map:
        return toc
    return [
        (level, title, remap_page_number(page_number, page_map))
        for level, title, page_number in toc
    ]
