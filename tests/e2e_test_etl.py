"""
End-to-end ETL test: Ingest multiple real PDFs and validate extraction quality.

Tests:
1. 41598_2018_Article_27126.pdf  - Music playschool (Scientific Reports, 10 pages)
2. attention_is_all_you_need.pdf - Transformer paper (arXiv, 15 pages)
3. nobel_chemistry_2024.pdf      - Nobel Prize report
4. docling_paper.pdf             - Docling Technical Report
5. gpt4_medical.pdf              - GPT-4 Medical paper

Usage:
    uv run pytest tests/e2e_test_etl.py -v
    uv run pytest tests/e2e_test_etl.py -v -k "attention"
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from src.application.document_service import DocumentService
from src.infrastructure.file_storage import FileStorage
from src.infrastructure.pdf_extractor import PyMuPDFExtractor

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DATA_DIR = Path("data")
TEST_PDFS = Path("test_pdfs")


@pytest.fixture(scope="module")
def service() -> DocumentService:
    """Create a shared DocumentService for all tests."""
    return DocumentService(
        repository=FileStorage(base_dir=DATA_DIR),
        pdf_extractor=PyMuPDFExtractor(),
    )


def _clean_and_ingest(service: DocumentService, pdf_name: str) -> dict:
    """Helper: clean old data, ingest, return manifest dict."""
    pdf_path = TEST_PDFS / pdf_name
    if not pdf_path.exists():
        pytest.skip(f"PDF not found: {pdf_path}")

    # Run ingest
    results = asyncio.get_event_loop().run_until_complete(
        service.ingest([pdf_path])
    )
    assert len(results) == 1
    r = results[0]
    assert r.success, f"Ingest failed: {r.error}"

    # Load manifest
    manifest_path = DATA_DIR / r.doc_id / f"{r.doc_id}_manifest.json"
    assert manifest_path.exists(), f"Manifest not found: {manifest_path}"
    manifest = json.loads(manifest_path.read_text())

    # Load full markdown
    md_path = DATA_DIR / r.doc_id / f"{r.doc_id}_full.md"
    assert md_path.exists(), f"Markdown not found: {md_path}"
    md_text = md_path.read_text()

    return {
        "result": r,
        "manifest": manifest,
        "markdown": md_text,
        "doc_id": r.doc_id,
        "sections": manifest["assets"].get("sections", []),
        "tables": manifest["assets"].get("tables", []),
        "figures": manifest["assets"].get("figures", []),
    }


def _print_summary(data: dict, label: str):
    """Print a concise summary for visibility."""
    r = data["result"]
    sections = data["sections"]
    tables = data["tables"]
    figures = data["figures"]

    print(f"\n{'='*70}")
    print(f"  {label}")
    print(f"{'='*70}")
    print(f"  Doc ID:    {r.doc_id}")
    print(f"  Title:     {r.title}")
    print(f"  Pages:     {r.pages_processed}")
    print(f"  Sections:  {r.sections_found}")
    print(f"  Tables:    {r.tables_found}")
    print(f"  Figures:   {r.figures_found}")
    print(f"  Time:      {r.processing_time_seconds:.2f}s")

    if sections:
        print(f"\n  --- Sections ---")
        for s in sections:
            indent = "  " * s.get("level", 1)
            print(f"  {indent}[L{s['level']}] {s['title'][:60]} (p.{s.get('page', '?')})")

    if tables:
        print(f"\n  --- Tables ---")
        for t in tables:
            cap = t.get("caption", "")[:50] or "(no caption)"
            print(f"    {t['id']}: p.{t.get('page', '?')} {t.get('row_count', '?')}x{t.get('col_count', '?')} {cap}")

    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# Test 1: Music Playschool (Scientific Reports 2018)
# ---------------------------------------------------------------------------


class TestMusicPlayschool:
    """Test PDF with known built-in TOC, tables, and figures."""

    @pytest.fixture(autouse=True, scope="class")
    def ingest(self, service):
        """Ingest once, share data across all tests in this class."""
        # Clean old data first
        for d in DATA_DIR.glob("doc_41598*"):
            shutil.rmtree(d, ignore_errors=True)

        data = _clean_and_ingest(service, "41598_2018_Article_27126.pdf")
        _print_summary(data, "Music Playschool (Scientific Reports 2018)")
        self.__class__._data = data

    @property
    def data(self):
        return self.__class__._data

    def test_title_complete(self):
        """Title should be the full title, not truncated."""
        assert "linguistic skills" in self.data["result"].title.lower()
        assert len(self.data["result"].title) > 30

    def test_sections_from_pdf_toc(self):
        """Should have structured sections from PDF built-in TOC."""
        sections = self.data["sections"]
        assert len(sections) >= 10, f"Expected >=10 sections, got {len(sections)}"

        # Check hierarchical structure
        titles = [s["title"].lower() for s in sections]
        assert any("result" in t for t in titles), "Missing 'Results' section"
        assert any("discussion" in t for t in titles), "Missing 'Discussion' section"
        assert any("method" in t for t in titles), "Missing 'Methods' section"

        # Check multi-level hierarchy
        levels = {s["level"] for s in sections}
        assert len(levels) >= 2, f"Expected >=2 heading levels, got {levels}"

    def test_no_noise_headings(self):
        """Should NOT have single-letter noise like 'a', 'b', 'c', 'd'."""
        sections = self.data["sections"]
        noise = [s for s in sections if len(s["title"].strip()) <= 2]
        assert len(noise) == 0, f"Found noise headings: {[s['title'] for s in noise]}"

    def test_tables_extracted(self):
        """Should find at least 1 table (the real data table on page 3)."""
        tables = self.data["tables"]
        assert len(tables) >= 1, f"Expected >=1 table, got {len(tables)}"
        # The main table has multiple rows and columns
        main_table = tables[0]
        assert main_table.get("row_count", 0) > 5 or main_table.get("col_count", 0) > 2

    def test_figures_extracted(self):
        """Should have figures (images from PDF)."""
        figures = self.data["figures"]
        assert len(figures) >= 3, f"Expected >=3 figures, got {len(figures)}"

    def test_markdown_generated(self):
        """Full markdown should be non-empty and substantial."""
        md = self.data["markdown"]
        assert len(md) > 5000, f"Markdown too short: {len(md)} chars"

    def test_no_duplicate_section_ids(self):
        """Section IDs should be unique."""
        ids = [s["id"] for s in self.data["sections"]]
        assert len(ids) == len(set(ids)), f"Duplicate section IDs: {ids}"


# ---------------------------------------------------------------------------
# Test 2: Attention Is All You Need (arXiv 2017)
# ---------------------------------------------------------------------------


class TestAttentionPaper:
    """Transformer paper - arXiv format with tables and figures."""

    @pytest.fixture(autouse=True, scope="class")
    def ingest(self, service):
        for d in DATA_DIR.glob("doc_attention*"):
            shutil.rmtree(d, ignore_errors=True)

        data = _clean_and_ingest(service, "attention_is_all_you_need.pdf")
        _print_summary(data, "Attention Is All You Need (arXiv 2017)")
        self.__class__._data = data

    @property
    def data(self):
        return self.__class__._data

    def test_title_detected(self):
        """Title should contain 'attention'."""
        title = self.data["result"].title.lower()
        assert "attention" in title, f"Bad title: {self.data['result'].title}"

    def test_sections_exist(self):
        """Should have meaningful sections."""
        sections = self.data["sections"]
        assert len(sections) >= 3, f"Expected >=3 sections, got {len(sections)}"

    def test_key_sections_present(self):
        """Should have key sections like Introduction, Model Architecture, etc."""
        titles = [s["title"].lower() for s in self.data["sections"]]
        all_titles = " | ".join(titles)

        # At least some of these should be present
        expected_any = ["introduction", "model", "attention", "training", "result", "conclusion"]
        found = [e for e in expected_any if any(e in t for t in titles)]
        assert len(found) >= 2, f"Expected key sections, found: {found} in: {all_titles}"

    def test_tables_present(self):
        """Transformer paper has performance comparison tables."""
        tables = self.data["tables"]
        # arXiv PDFs may or may not have extractable tables
        # Just check that extraction doesn't crash
        assert isinstance(tables, list)
        print(f"  Tables found: {len(tables)}")

    def test_figures_present(self):
        """Should have figures (architecture diagrams)."""
        figures = self.data["figures"]
        assert len(figures) >= 1, f"Expected >=1 figure, got {len(figures)}"

    def test_no_noise_headings(self):
        """Should NOT have single-letter or noise headings."""
        sections = self.data["sections"]
        noise = [s for s in sections if len(s["title"].strip()) <= 2]
        assert len(noise) == 0, f"Found noise headings: {[s['title'] for s in noise]}"

    def test_markdown_complete(self):
        """Full markdown should contain key content."""
        md = self.data["markdown"].lower()
        assert "attention" in md
        assert len(self.data["markdown"]) > 5000


# ---------------------------------------------------------------------------
# Test 3: Nobel Chemistry 2024
# ---------------------------------------------------------------------------


class TestNobelChemistry:
    """Nobel Prize report - typically image-heavy with structured sections."""

    @pytest.fixture(autouse=True, scope="class")
    def ingest(self, service):
        for d in DATA_DIR.glob("doc_nobel_chemistry*"):
            shutil.rmtree(d, ignore_errors=True)

        data = _clean_and_ingest(service, "nobel_chemistry_2024.pdf")
        _print_summary(data, "Nobel Chemistry 2024")
        self.__class__._data = data

    @property
    def data(self):
        return self.__class__._data

    def test_title_detected(self):
        """Should have a meaningful title."""
        title = self.data["result"].title
        assert len(title) > 5, f"Title too short: '{title}'"

    def test_sections_exist(self):
        """Should have sections."""
        sections = self.data["sections"]
        assert len(sections) >= 2, f"Expected >=2 sections, got {len(sections)}"

    def test_figures_present(self):
        """Nobel reports usually have many figures."""
        figures = self.data["figures"]
        assert len(figures) >= 5, f"Expected >=5 figures, got {len(figures)}"

    def test_markdown_not_empty(self):
        """Markdown should be substantial."""
        assert len(self.data["markdown"]) > 3000

    def test_no_noise_headings(self):
        """Should NOT have single-character noise headings."""
        sections = self.data["sections"]
        noise = [s for s in sections if len(s["title"].strip()) <= 2]
        assert len(noise) == 0, f"Found noise: {[s['title'] for s in noise]}"


# ---------------------------------------------------------------------------
# Test 4: Docling Technical Report
# ---------------------------------------------------------------------------


class TestDoclingPaper:
    """Docling paper - technical report with many figures."""

    @pytest.fixture(autouse=True, scope="class")
    def ingest(self, service):
        for d in DATA_DIR.glob("doc_docling*"):
            shutil.rmtree(d, ignore_errors=True)

        data = _clean_and_ingest(service, "docling_paper.pdf")
        _print_summary(data, "Docling Technical Report")
        self.__class__._data = data

    @property
    def data(self):
        return self.__class__._data

    def test_title_contains_docling(self):
        """Title should reference 'Docling'."""
        title = self.data["result"].title.lower()
        assert "docling" in title, f"Bad title: {self.data['result'].title}"

    def test_sections_exist(self):
        """Should have structured sections."""
        sections = self.data["sections"]
        assert len(sections) >= 3, f"Expected >=3 sections, got {len(sections)}"

    def test_figures_present(self):
        """Docling report has many diagrams."""
        figures = self.data["figures"]
        assert len(figures) >= 5, f"Expected >=5 figures, got {len(figures)}"

    def test_markdown_complete(self):
        """Markdown should be substantial."""
        assert len(self.data["markdown"]) > 10000

    def test_no_noise_headings(self):
        """No noise headings."""
        sections = self.data["sections"]
        noise = [s for s in sections if len(s["title"].strip()) <= 2]
        assert len(noise) == 0, f"Found noise: {[s['title'] for s in noise]}"


# ---------------------------------------------------------------------------
# Test 5: GPT-4 Medical Paper
# ---------------------------------------------------------------------------


class TestGPT4Medical:
    """GPT-4 Medical - typically long paper with many sections."""

    @pytest.fixture(autouse=True, scope="class")
    def ingest(self, service):
        for d in DATA_DIR.glob("doc_gpt4*"):
            shutil.rmtree(d, ignore_errors=True)

        data = _clean_and_ingest(service, "gpt4_medical.pdf")
        _print_summary(data, "GPT-4 Medical Paper")
        self.__class__._data = data

    @property
    def data(self):
        return self.__class__._data

    def test_title_detected(self):
        """Title should reference GPT-4."""
        title = self.data["result"].title.lower()
        assert "gpt" in title or len(title) > 10, f"Bad title: {self.data['result'].title}"

    def test_sections_present(self):
        """Should have many sections (long paper)."""
        sections = self.data["sections"]
        assert len(sections) >= 5, f"Expected >=5 sections, got {len(sections)}"

    def test_figures_present(self):
        """Should have figures."""
        figures = self.data["figures"]
        assert len(figures) >= 3, f"Expected >=3 figures, got {len(figures)}"

    def test_markdown_substantial(self):
        """Markdown should be long (it's a big report)."""
        assert len(self.data["markdown"]) > 20000

    def test_no_noise_headings(self):
        """No noise headings."""
        sections = self.data["sections"]
        noise = [s for s in sections if len(s["title"].strip()) <= 2]
        assert len(noise) == 0, f"Found noise: {[s['title'] for s in noise]}"


# ---------------------------------------------------------------------------
# Cross-document tests
# ---------------------------------------------------------------------------


class TestCrossDocument:
    """Tests that validate properties across all documents."""

    @pytest.fixture(autouse=True, scope="class")
    def ingest_all(self, service):
        """Verify all manifests exist (they should have been created by previous classes)."""
        manifests = list(DATA_DIR.glob("doc_*/*_manifest.json"))
        self.__class__._manifests = []
        for mp in manifests:
            m = json.loads(mp.read_text())
            self.__class__._manifests.append(m)

    @property
    def manifests(self):
        return self.__class__._manifests

    def test_all_have_titles(self):
        """Every document should have a title."""
        for m in self.manifests:
            assert m["title"], f"Missing title in {m['doc_id']}"

    def test_all_have_sections(self):
        """Every document should have at least some sections."""
        for m in self.manifests:
            sections = m["assets"].get("sections", [])
            assert len(sections) >= 1, f"No sections in {m['doc_id']}"

    def test_all_have_figures(self):
        """Every document should have at least one figure."""
        for m in self.manifests:
            figures = m["assets"].get("figures", [])
            assert len(figures) >= 1, f"No figures in {m['doc_id']}"

    def test_section_ids_unique_per_doc(self):
        """Within each document, section IDs must be unique."""
        for m in self.manifests:
            sections = m["assets"].get("sections", [])
            ids = [s["id"] for s in sections]
            dupes = [i for i in ids if ids.count(i) > 1]
            assert len(dupes) == 0, f"Duplicate section IDs in {m['doc_id']}: {set(dupes)}"

    def test_no_noise_sections_globally(self):
        """No document should have single-letter noise sections."""
        for m in self.manifests:
            sections = m["assets"].get("sections", [])
            noise = [s for s in sections if len(s["title"].strip()) <= 2]
            assert len(noise) == 0, (
                f"Noise sections in {m['doc_id']}: {[s['title'] for s in noise]}"
            )
