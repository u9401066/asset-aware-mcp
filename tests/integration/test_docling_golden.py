"""Integration: real Docling parse on bundled PDFs (skipped if backend absent).

Guards against self-reported quality claims. Unlike the mocked unit tests in
``tests/infrastructure/test_docling_bridge.py``, these actually run Docling
(in-process or via the ``.venv-docling`` subprocess bridge) on the project's
bundled academic PDFs and assert real figure/caption/table counts, so a
regression in extraction quality fails the suite.

Golden bounds are intentionally lower bounds (``>=``) measured on 2026-07-08
(attention: figures>=3, captions>=5, tables>=3) so minor Docling version drift
does not make the suite flaky while still catching genuine regressions.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.docling_adapter import (
    DoclingBackendUnavailable,
    DoclingExtractor,
)
from src.infrastructure.marker_adapter import MarkerParseResult

ATTENTION_PDF = Path("data/doc_attention_is_all_you_need_3b2fae/source.pdf")


@pytest.fixture(scope="module")
def attention_result() -> MarkerParseResult:
    """Parse the attention paper once with real Docling; skip if unavailable."""
    extractor = DoclingExtractor()
    try:
        extractor.require_backend_available()
    except DoclingBackendUnavailable:
        pytest.skip("Docling backend not available (run scripts/setup_docling.py)")
    if not ATTENTION_PDF.exists():
        pytest.skip(f"missing bundled test PDF: {ATTENTION_PDF}")
    return extractor.parse(ATTENTION_PDF, extract_images=True)


class TestDoclingGoldenAttention:
    def test_extracts_semantic_figures(
        self, attention_result: MarkerParseResult
    ) -> None:
        figures = [b for b in attention_result.blocks if b.block_type == "Figure"]
        assert len(figures) >= 3, f"expected >=3 figures, got {len(figures)}"

    def test_binds_captions_semantically(
        self, attention_result: MarkerParseResult
    ) -> None:
        captions = [b for b in attention_result.blocks if b.block_type == "Caption"]
        assert len(captions) >= 5, f"expected >=5 captions, got {len(captions)}"

    def test_extracts_tables(self, attention_result: MarkerParseResult) -> None:
        tables = [b for b in attention_result.blocks if b.block_type == "Table"]
        assert len(tables) >= 3, f"expected >=3 tables, got {len(tables)}"

    def test_reading_order_markdown_complete(
        self, attention_result: MarkerParseResult
    ) -> None:
        assert len(attention_result.markdown) > 15000
        assert attention_result.page_count >= 10

    def test_section_headers_recovered(
        self, attention_result: MarkerParseResult
    ) -> None:
        headers = [
            b for b in attention_result.blocks if b.block_type == "SectionHeader"
        ]
        assert len(headers) >= 5, f"expected >=5 section headers, got {len(headers)}"

    def test_images_returned_as_real_bytes(
        self, attention_result: MarkerParseResult
    ) -> None:
        assert len(attention_result.images) >= 1
        for name, data in attention_result.images.items():
            assert isinstance(data, bytes), f"image {name} is not bytes"
            assert len(data) > 0, f"image {name} is empty"

    def test_subprocess_mode_metadata(
        self, attention_result: MarkerParseResult
    ) -> None:
        # On a base interpreter without docling, the bridge runs via subprocess.
        assert attention_result.metadata.get("backend") == "docling"
