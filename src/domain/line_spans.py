"""Utilities for mapping extracted content back to markdown line spans."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Sequence

    from src.domain.entities import FigureAsset, SectionAsset, TableAsset


class BlockLike(Protocol):
    block_id: str
    block_type: str
    page: int
    text: str
    section_hierarchy: dict[str, str]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class LineSpan:
    start_line: int
    end_line: int
    page_number: int
    strategy: str
    section_title: str = ""
    confidence: float = 0.0


@dataclass(frozen=True)
class ParsedSection:
    title: str
    normalized_title: str
    level: int
    start_line: int
    end_line: int
    page_number: int


class MarkdownLineSpanIndex:
    """Page-aware and section-aware text matcher for markdown line spans."""

    def __init__(self, markdown: str):
        self.markdown = markdown
        self.lines = markdown.splitlines()
        self.normalized_lines = [
            self.normalize_for_matching(line) for line in self.lines
        ]
        self.page_ranges = self._build_page_ranges()
        self.sections = self._parse_sections()
        self.scope_cursors: dict[tuple[int, str], int] = {}

    def align_text(
        self,
        text: str,
        *,
        page_hint: int | None = None,
        section_titles: list[str] | None = None,
        block_type: str = "Text",
    ) -> LineSpan | None:
        snippets = self._snippets(text, block_type=block_type)
        if not snippets:
            return None

        normalized_section_titles = [
            self.normalize_for_matching(title)
            for title in (section_titles or [])
            if self.normalize_for_matching(title)
        ]
        page = page_hint or 1

        for range_start, range_end, section_key, strategy in self._candidate_ranges(
            page, normalized_section_titles
        ):
            cursor_key = (page, section_key)
            search_start = max(
                range_start, self.scope_cursors.get(cursor_key, range_start)
            )
            resolved = self._search_range(snippets, search_start, range_end)
            if resolved is None and search_start > range_start:
                resolved = self._search_range(snippets, range_start, search_start)
            if resolved is None:
                continue
            start_line, end_line = resolved
            self.scope_cursors[cursor_key] = end_line
            section_title = ""
            section = self.find_containing_section(start_line, end_line)
            if section is not None:
                section_title = section.title
            confidence = (
                0.95
                if strategy == "page-section"
                else 0.85
                if strategy == "page"
                else 0.65
            )
            return LineSpan(
                start_line=start_line,
                end_line=end_line,
                page_number=page,
                strategy=strategy,
                section_title=section_title,
                confidence=confidence,
            )

        return None

    def find_section_span(
        self,
        title: str,
        *,
        page_hint: int | None = None,
    ) -> ParsedSection | None:
        normalized = self.normalize_for_matching(title)
        candidates = [
            section
            for section in self.sections
            if section.normalized_title == normalized
        ]
        if page_hint is not None:
            page_candidates = [
                section for section in candidates if section.page_number == page_hint
            ]
            if page_candidates:
                candidates = page_candidates
        if not candidates:
            return None
        return min(candidates, key=lambda section: (section.level, section.start_line))

    def find_containing_section(
        self,
        start_line: int,
        end_line: int,
    ) -> ParsedSection | None:
        containing = [
            section
            for section in self.sections
            if section.start_line <= start_line and end_line <= section.end_line
        ]
        if not containing:
            return None
        return max(containing, key=lambda section: (section.level, section.start_line))

    def extract_preview(
        self, start_line: int, end_line: int, *, max_chars: int = 200
    ) -> str:
        preview_lines = [
            line.strip()
            for line in self.lines[start_line:end_line]
            if line.strip() and not line.strip().startswith("<!--")
        ]
        return " ".join(preview_lines)[:max_chars]

    def _candidate_ranges(
        self,
        page_number: int,
        normalized_section_titles: list[str],
    ) -> list[tuple[int, int, str, str]]:
        page_start, page_end = self.page_ranges.get(page_number, (0, len(self.lines)))
        ranges: list[tuple[int, int, str, str]] = []

        for title in reversed(normalized_section_titles):
            section = next(
                (
                    item
                    for item in self.sections
                    if item.normalized_title == title
                    and item.page_number == page_number
                ),
                None,
            )
            if section is not None:
                ranges.append(
                    (
                        max(page_start, section.start_line),
                        min(page_end, section.end_line),
                        title,
                        "page-section",
                    )
                )
                break

        ranges.append((page_start, page_end, "__page__", "page"))
        if page_number != 1 or page_start != 0 or page_end != len(self.lines):
            ranges.append((0, len(self.lines), "__document__", "document"))
        return ranges

    def _search_range(
        self,
        snippets: list[str],
        start: int,
        end: int,
    ) -> tuple[int, int] | None:
        if start >= end:
            return None

        primary = snippets[0]
        for line_index in range(start, end):
            if primary not in self.normalized_lines[line_index]:
                continue
            window_text = self.normalized_lines[line_index]
            window_end = line_index + 1
            while window_end < min(end, line_index + 12):
                if all(snippet in window_text for snippet in snippets):
                    return (line_index, window_end)
                window_text = (
                    f"{window_text} {self.normalized_lines[window_end]}".strip()
                )
                window_end += 1
            if all(snippet in window_text for snippet in snippets):
                return (line_index, min(window_end, end))
        return None

    def _build_page_ranges(self) -> dict[int, tuple[int, int]]:
        markers: list[tuple[int, int]] = []
        for index, line in enumerate(self.lines):
            match = re.search(r"<!-- Page (\d+) -->", line)
            if match:
                markers.append((int(match.group(1)), index))

        if not markers:
            return {1: (0, len(self.lines))}

        ranges: dict[int, tuple[int, int]] = {}
        for marker_index, (page, line_index) in enumerate(markers):
            start_line = line_index + 1
            end_line = (
                markers[marker_index + 1][1]
                if marker_index + 1 < len(markers)
                else len(self.lines)
            )
            ranges[page] = (start_line, end_line)
        return ranges

    def _parse_sections(self) -> list[ParsedSection]:
        sections: list[ParsedSection] = []
        current_page = 1

        for index, line in enumerate(self.lines):
            page_match = re.search(r"<!-- Page (\d+) -->", line)
            if page_match:
                current_page = int(page_match.group(1))
                continue

            header_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if not header_match:
                continue

            title = header_match.group(2).strip()
            normalized_title = self.normalize_for_matching(title)
            if not normalized_title:
                continue

            level = len(header_match.group(1))
            end_line = len(self.lines)
            for next_index in range(index + 1, len(self.lines)):
                next_header = re.match(r"^(#{1,6})\s+", self.lines[next_index])
                if next_header and len(next_header.group(1)) <= level:
                    end_line = next_index
                    break

            sections.append(
                ParsedSection(
                    title=title,
                    normalized_title=normalized_title,
                    level=level,
                    start_line=index,
                    end_line=end_line,
                    page_number=current_page,
                )
            )

        return sections

    def _snippets(self, text: str, *, block_type: str) -> list[str]:
        normalized = self.normalize_for_matching(text)
        if not normalized:
            return []

        if block_type.lower() == "table" or "|" in text:
            table_lines = [
                self.normalize_for_matching(line)
                for line in text.splitlines()
                if self.normalize_for_matching(line)
            ]
            return table_lines[:3] or [normalized[:160]]

        pieces = [
            piece.strip()
            for piece in re.split(r"(?<=[.!?])\s+", normalized)
            if piece.strip()
        ]
        snippets = [piece[:160] for piece in pieces[:3] if len(piece) >= 8]
        if snippets:
            return snippets
        return [normalized[:160]]

    @staticmethod
    def normalize_for_matching(text: str) -> str:
        cleaned = re.sub(r"<!--.*?-->", " ", text)
        cleaned = cleaned.replace("`", " ")
        cleaned = re.sub(r"[_*#>-]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.strip().lower()


def annotate_marker_blocks(
    markdown: str, blocks: Sequence[BlockLike | dict[str, Any]]
) -> MarkdownLineSpanIndex:
    """Annotate Marker blocks with persisted markdown line spans."""
    index = MarkdownLineSpanIndex(markdown)
    ordered_blocks = sorted(blocks, key=_block_sort_key)

    for block in ordered_blocks:
        text = _block_text(block)
        if not text.strip():
            continue
        section_titles = list(_block_section_hierarchy(block).values())
        span = index.align_text(
            text,
            page_hint=_block_page(block),
            section_titles=section_titles,
            block_type=_block_type(block),
        )
        if span is None:
            continue
        metadata = _block_metadata(block)
        metadata["line_start"] = span.start_line
        metadata["line_end"] = span.end_line
        metadata["line_match_strategy"] = span.strategy
        metadata["line_match_confidence"] = span.confidence
        if span.section_title:
            metadata["matched_section_title"] = span.section_title

    return index


def apply_asset_line_spans(
    index: MarkdownLineSpanIndex,
    figures: list[FigureAsset],
    tables: list[TableAsset],
    *,
    blocks: Sequence[BlockLike | dict[str, Any]] | None = None,
    sections: list[SectionAsset] | None = None,
) -> None:
    """Propagate line spans from markdown and block annotations to asset entities."""
    block_map = {
        _block_id(block): block for block in (blocks or []) if _block_id(block)
    }
    caption_blocks_by_page: dict[int, list[BlockLike | dict[str, Any]]] = {}
    for block in blocks or []:
        if _block_type(block).lower() != "caption":
            continue
        caption_blocks_by_page.setdefault(_block_page(block), []).append(block)

    for caption_blocks in caption_blocks_by_page.values():
        caption_blocks.sort(key=_block_sort_key)

    for table in tables:
        span = (
            _span_from_block(block_map.get(table.source_block_id))
            if table.source_block_id
            else None
        )
        if span is None:
            span = index.align_text(
                table.markdown or table.preview or table.caption,
                page_hint=table.page,
                block_type="Table",
            )
        _apply_asset_span(table, span, sections=sections or [])

    for figure in figures:
        span = (
            _span_from_block(block_map.get(figure.source_block_id))
            if figure.source_block_id
            else None
        )
        if span is None and figure.caption:
            span = index.align_text(
                figure.caption,
                page_hint=figure.page,
                block_type="Caption",
            )
        if span is None and figure.source_block_id:
            span = _nearest_caption_span(
                block_map.get(figure.source_block_id),
                caption_blocks_by_page.get(figure.page, []),
            )
        _apply_asset_span(figure, span, sections=sections or [])


def _apply_asset_span(
    asset: FigureAsset | TableAsset,
    span: LineSpan | None,
    *,
    sections: list[SectionAsset],
) -> None:
    if span is None:
        return
    asset.line_start = span.start_line
    asset.line_end = span.end_line
    asset.line_source = span.strategy
    for section in sections:
        if section.start_line <= span.start_line and span.end_line <= section.end_line:
            asset.section_id = section.id
            asset.section_title = section.title


def _nearest_caption_span(
    block: BlockLike | dict[str, Any] | None,
    caption_blocks: Sequence[BlockLike | dict[str, Any]],
) -> LineSpan | None:
    if block is None:
        return None
    block_order = _block_source_order(block)
    candidate = min(
        caption_blocks,
        key=lambda item: abs(_block_source_order(item) - block_order),
        default=None,
    )
    return _span_from_block(candidate)


def _span_from_block(block: BlockLike | dict[str, Any] | None) -> LineSpan | None:
    if block is None:
        return None
    metadata = _block_metadata(block)
    start_line = metadata.get("line_start")
    end_line = metadata.get("line_end")
    if not isinstance(start_line, int) or not isinstance(end_line, int):
        return None
    return LineSpan(
        start_line=start_line,
        end_line=end_line,
        page_number=_block_page(block),
        strategy=str(metadata.get("line_match_strategy") or "block"),
        section_title=str(metadata.get("matched_section_title") or ""),
        confidence=float(metadata.get("line_match_confidence") or 0.0),
    )


def _block_sort_key(block: BlockLike | dict[str, Any]) -> tuple[int, float, str]:
    return (_block_page(block), _block_source_order(block), _block_id(block))


def _block_id(block: BlockLike | dict[str, Any]) -> str:
    if isinstance(block, dict):
        return str(block.get("block_id") or "")
    return str(getattr(block, "block_id", "") or "")


def _block_type(block: BlockLike | dict[str, Any]) -> str:
    if isinstance(block, dict):
        return str(block.get("block_type") or "")
    return str(getattr(block, "block_type", "") or "")


def _block_page(block: BlockLike | dict[str, Any]) -> int:
    if isinstance(block, dict):
        return int(block.get("page") or 1)
    return int(getattr(block, "page", 1) or 1)


def _block_text(block: BlockLike | dict[str, Any]) -> str:
    if isinstance(block, dict):
        return str(block.get("text") or "")
    return str(getattr(block, "text", "") or "")


def _block_section_hierarchy(block: BlockLike | dict[str, Any]) -> dict[str, str]:
    if isinstance(block, dict):
        section_hierarchy = block.get("section_hierarchy")
    else:
        section_hierarchy = getattr(block, "section_hierarchy", {})
    return section_hierarchy if isinstance(section_hierarchy, dict) else {}


def _block_metadata(block: BlockLike | dict[str, Any]) -> dict[str, Any]:
    if isinstance(block, dict):
        metadata = block.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            block["metadata"] = metadata
        return metadata

    metadata = getattr(block, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        block.metadata = metadata
    return metadata


def _block_source_order(block: BlockLike | dict[str, Any]) -> float:
    metadata = _block_metadata(block)
    raw_value = metadata.get("source_order")
    if isinstance(raw_value, (int, float)):
        return float(raw_value)
    return 0.0
