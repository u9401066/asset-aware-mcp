"""Build citation-ready block artifacts from markdown and manifest assets."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from src.domain.line_spans import MarkdownLineSpanIndex

if TYPE_CHECKING:
    from src.domain.entities import DocumentManifest


def build_markdown_blocks(
    markdown: str,
    manifest: DocumentManifest,
    *,
    source_backend: str = "pymupdf",
) -> list[dict[str, Any]]:
    """Synthesize searchable blocks from markdown plus final manifest assets."""
    index = MarkdownLineSpanIndex(markdown)
    lines = markdown.splitlines()
    section_lookup = {section.start_line: section for section in index.sections}
    blocks: list[dict[str, Any]] = []
    block_order = 0
    text_counter = 0
    current_page = 1
    line_index = 0
    asset_line_ranges = _asset_line_ranges(manifest, len(lines))
    asset_lines = {
        line_number
        for start_line, end_line in asset_line_ranges
        for line_number in range(start_line, end_line)
    }

    while line_index < len(lines):
        if line_index in asset_lines:
            line_index = _next_uncovered_line(line_index, asset_line_ranges)
            continue

        raw_line = lines[line_index]
        page_match = re.search(r"<!-- Page (\d+) -->", raw_line)
        if page_match:
            current_page = int(page_match.group(1))
            line_index += 1
            continue

        stripped = raw_line.strip()
        if not stripped:
            line_index += 1
            continue

        section = section_lookup.get(line_index)
        if section is not None:
            block_order += 1
            blocks.append(
                _make_block_dict(
                    block_id=f"md_sec_{len(blocks) + 1}",
                    block_type="SectionHeader",
                    page=current_page,
                    text=section.title,
                    line_start=section.start_line,
                    line_end=min(section.start_line + 1, len(lines)),
                    section_hierarchy=_section_hierarchy_for_line(
                        index.sections,
                        section.start_line,
                    ),
                    source_order=block_order,
                    source_backend=source_backend,
                )
            )
            line_index += 1
            continue

        start_line = line_index
        paragraph_lines: list[str] = []
        while line_index < len(lines):
            candidate = lines[line_index]
            if re.search(r"<!-- Page (\d+) -->", candidate):
                break
            if not candidate.strip():
                break
            if line_index in section_lookup:
                break
            if line_index in asset_lines:
                break
            paragraph_lines.append(candidate.strip())
            line_index += 1

        paragraph_text = "\n".join(paragraph_lines).strip()
        if paragraph_text:
            block_order += 1
            text_counter += 1
            blocks.append(
                _make_block_dict(
                    block_id=f"md_txt_{text_counter}",
                    block_type="Text",
                    page=current_page,
                    text=paragraph_text,
                    line_start=start_line,
                    line_end=line_index,
                    section_hierarchy=_section_hierarchy_for_line(
                        index.sections,
                        start_line,
                    ),
                    source_order=block_order,
                    source_backend=source_backend,
                )
            )

        if line_index == start_line:
            line_index += 1

    for table in sorted(
        manifest.assets.tables,
        key=lambda item: (item.page, item.line_start or 0, item.id),
    ):
        if table.line_start is None or table.line_end is None:
            continue
        block_order += 1
        blocks.append(
            _make_block_dict(
                block_id=table.source_block_id or f"asset_{table.id}",
                block_type="Table",
                page=table.page,
                text=table.markdown or table.preview or table.caption,
                line_start=table.line_start,
                line_end=table.line_end,
                section_hierarchy=_section_hierarchy_for_line(
                    index.sections,
                    table.line_start,
                ),
                source_order=max(block_order, table.source_order or 0),
                source_backend=source_backend,
            )
        )

    for figure in sorted(
        manifest.assets.figures,
        key=lambda item: (item.page, item.line_start or 0, item.id),
    ):
        if figure.line_start is None or figure.line_end is None:
            continue
        block_order += 1
        blocks.append(
            _make_block_dict(
                block_id=figure.source_block_id or f"asset_{figure.id}",
                block_type="Figure",
                page=figure.page,
                text=figure.caption or figure.id,
                line_start=figure.line_start,
                line_end=figure.line_end,
                section_hierarchy=_section_hierarchy_for_line(
                    index.sections,
                    figure.line_start,
                ),
                source_order=max(block_order, figure.source_order or 0),
                source_backend=source_backend,
            )
        )

    blocks.sort(
        key=lambda item: (
            int(item.get("page") or 0),
            int(((item.get("metadata") or {}).get("line_start")) or 0),
            float(((item.get("metadata") or {}).get("source_order")) or 0),
            str(item.get("block_id") or ""),
        )
    )
    return blocks


def _asset_line_ranges(
    manifest: DocumentManifest,
    total_lines: int,
) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    assets: list[Any] = []
    assets.extend(manifest.assets.tables)
    assets.extend(manifest.assets.figures)
    for asset in assets:
        if asset.line_start is None or asset.line_end is None:
            continue
        start_line = max(0, int(asset.line_start))
        end_line = min(total_lines, int(asset.line_end))
        if end_line <= start_line:
            end_line = min(total_lines, start_line + 1)
        if start_line < total_lines:
            ranges.append((start_line, end_line))
    ranges.sort()
    return ranges


def _next_uncovered_line(
    line_index: int,
    ranges: list[tuple[int, int]],
) -> int:
    next_line = line_index + 1
    for start_line, end_line in ranges:
        if start_line <= line_index < end_line:
            next_line = max(next_line, end_line)
    return next_line


def _make_block_dict(
    *,
    block_id: str,
    block_type: str,
    page: int,
    text: str,
    line_start: int,
    line_end: int,
    section_hierarchy: dict[str, str],
    source_order: int,
    source_backend: str,
) -> dict[str, Any]:
    return {
        "block_id": block_id,
        "block_type": block_type,
        "page": int(page or 1),
        "text": text,
        "bbox": [],
        "polygon": [],
        "section_hierarchy": section_hierarchy,
        "metadata": {
            "line_start": line_start,
            "line_end": line_end,
            "line_match_strategy": "markdown-struct",
            "line_match_confidence": 1.0,
            "source_backend": source_backend,
            "source_order": source_order,
        },
    }


def _section_hierarchy_for_line(
    sections: list[Any],
    line_number: int,
) -> dict[str, str]:
    containing = [
        section
        for section in sections
        if section.start_line <= line_number < section.end_line
    ]
    containing.sort(key=lambda section: (section.level, section.start_line))
    return {
        str(index + 1): str(section.title)
        for index, section in enumerate(containing)
        if str(section.title).strip()
    }
