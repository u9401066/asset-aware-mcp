from __future__ import annotations

from src.domain.line_spans import MarkdownLineSpanIndex, annotate_marker_blocks


def test_line_index_prefers_page_and_section_for_repeated_sentence() -> None:
    markdown = """<!-- Page 1 -->

# Intro

Repeated sentence appears here.

<!-- Page 2 -->

# Methods

Repeated sentence appears here.
Unique methods detail follows.
"""

    index = MarkdownLineSpanIndex(markdown)
    span = index.align_text(
        "Repeated sentence appears here. Unique methods detail follows.",
        page_hint=2,
        section_titles=["Methods"],
    )

    assert span is not None
    assert span.page_number == 2
    assert span.strategy == "page-section"
    assert span.start_line == 10


def test_annotate_marker_blocks_persists_line_metadata() -> None:
    markdown = """<!-- Page 1 -->

# Results

This finding repeats twice.
This finding repeats twice.
But this block has a unique suffix.
"""
    blocks = [
        {
            "block_id": "blk_1",
            "block_type": "Text",
            "page": 1,
            "text": "This finding repeats twice. But this block has a unique suffix.",
            "section_hierarchy": {"1": "Results"},
            "metadata": {"source_order": 1},
        }
    ]

    annotate_marker_blocks(markdown, blocks)

    metadata = blocks[0]["metadata"]
    assert metadata["line_start"] == 4
    assert metadata["line_end"] == 7
    assert metadata["line_match_strategy"] == "page-section"
