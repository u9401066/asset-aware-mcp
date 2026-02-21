"""
Unit tests for the DFM (Docx-Flavored Markdown) module.

Tests cover:
- Domain entities and value objects
- DFM Renderer (IR → DFM text)
- DFM Parser (DFM text → edits)
- Round-trip consistency
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.domain.docx_entities import (
    CellFormat,
    DfmBlock,
    DocxIR,
    FormatRun,
    MergedCell,
    PageSetup,
)
from src.domain.docx_value_objects import (
    BreakType,
    DfmBlockType,
    TableCellAlign,
)
from src.infrastructure.dfm_parser import DfmParser
from src.infrastructure.dfm_renderer import DfmRenderer

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ir() -> DocxIR:
    """Create a minimal IR for testing."""
    ir = DocxIR(
        doc_id="test_doc_001",
        source_path="test.docx",
        source_filename="test.docx",
        checksum="abc123",
        created_at=datetime(2025, 1, 1, 12, 0, 0),
    )

    # Add a heading
    h1 = DfmBlock(
        id="h001",
        block_type=DfmBlockType.HEADING,
        content="Introduction",
        style_name="Heading1",
        level=1,
    )
    ir.blocks.append(h1)

    # Add a plain paragraph
    p1 = DfmBlock(
        id="p001",
        block_type=DfmBlockType.PARAGRAPH,
        content="This is a simple paragraph.",
        style_name="Normal",
    )
    ir.blocks.append(p1)

    # Add a formatted paragraph
    p2 = DfmBlock(
        id="p002",
        block_type=DfmBlockType.PARAGRAPH,
        content="Bold and italic text.",
        style_name="Normal",
        runs=[
            FormatRun(text="Bold ", bold=True),
            FormatRun(text="and ", italic=False),
            FormatRun(text="italic", italic=True),
            FormatRun(text=" text."),
        ],
    )
    ir.blocks.append(p2)

    # Add a list item
    l1 = DfmBlock(
        id="l001",
        block_type=DfmBlockType.LIST_ITEM,
        content="First item",
        list_level=0,
    )
    ir.blocks.append(l1)

    # Add a table
    t1 = DfmBlock(
        id="t001",
        block_type=DfmBlockType.TABLE,
        content="| Name | Age |\n| --- | --- |\n| Alice | 30 |\n| Bob | 25 |",
        table_style="TableGrid",
        col_widths=[5.0, 3.0],
    )
    ir.blocks.append(t1)

    return ir


@pytest.fixture
def renderer() -> DfmRenderer:
    return DfmRenderer()


@pytest.fixture
def parser() -> DfmParser:
    return DfmParser()


# ============================================================================
# Domain Entity Tests
# ============================================================================


class TestDfmBlockType:
    def test_editable_types(self):
        assert DfmBlockType.PARAGRAPH.is_editable
        assert DfmBlockType.HEADING.is_editable
        assert DfmBlockType.TABLE.is_editable
        assert not DfmBlockType.CHART.is_editable
        assert not DfmBlockType.MACRO.is_editable

    def test_protected_types(self):
        assert DfmBlockType.CHART.is_protected
        assert DfmBlockType.TOC.is_protected
        assert DfmBlockType.MACRO.is_protected
        assert not DfmBlockType.PARAGRAPH.is_protected
        assert not DfmBlockType.HEADING.is_protected

    def test_dfm_tag(self):
        assert DfmBlockType.TABLE.dfm_tag == "table"
        assert DfmBlockType.HEADING.dfm_tag == "heading"


class TestFormatRun:
    def test_plain_run(self):
        run = FormatRun(text="hello")
        assert run.is_plain

    def test_formatted_run(self):
        run = FormatRun(text="bold", bold=True)
        assert not run.is_plain

    def test_to_dict_minimal(self):
        run = FormatRun(text="hello")
        d = run.to_dict()
        assert d == {"text": "hello"}

    def test_to_dict_full(self):
        run = FormatRun(text="x", bold=True, italic=True, color="#FF0000")
        d = run.to_dict()
        assert d["bold"] is True
        assert d["italic"] is True
        assert d["color"] == "#FF0000"

    def test_from_dict_round_trip(self):
        original = FormatRun(text="test", bold=True, font_name="Arial", font_size=12.0)
        reconstructed = FormatRun.from_dict(original.to_dict())
        assert reconstructed.text == original.text
        assert reconstructed.bold == original.bold
        assert reconstructed.font_name == original.font_name
        assert reconstructed.font_size == original.font_size


class TestMergedCell:
    def test_round_trip(self):
        mc = MergedCell(row=0, col=1, row_span=2, col_span=3)
        d = mc.to_dict()
        mc2 = MergedCell.from_dict(d)
        assert mc2.row == mc.row
        assert mc2.col_span == mc.col_span


class TestCellFormat:
    def test_defaults(self):
        cf = CellFormat()
        assert cf.align == TableCellAlign.LEFT
        assert not cf.bold

    def test_round_trip(self):
        cf = CellFormat(bold=True, align=TableCellAlign.CENTER, bg_color="#FFFF00")
        d = cf.to_dict()
        cf2 = CellFormat.from_dict(d)
        assert cf2.bold is True
        assert cf2.align == TableCellAlign.CENTER
        assert cf2.bg_color == "#FFFF00"


class TestPageSetup:
    def test_defaults(self):
        ps = PageSetup()
        assert ps.size == "A4"
        assert ps.orientation == "portrait"

    def test_round_trip(self):
        ps = PageSetup(size="Letter", orientation="landscape", margin_top=1.0)
        d = ps.to_dict()
        ps2 = PageSetup.from_dict(d)
        assert ps2.size == "Letter"
        assert ps2.orientation == "landscape"
        assert ps2.margin_top == 1.0


class TestDfmBlock:
    def test_editable(self):
        b = DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="hello")
        assert b.is_editable
        assert not b.is_protected

    def test_protected(self):
        b = DfmBlock(id="c001", block_type=DfmBlockType.CHART, content="chart")
        assert b.is_protected
        assert not b.is_editable

    def test_plain_text_from_runs(self):
        b = DfmBlock(
            id="p001",
            block_type=DfmBlockType.PARAGRAPH,
            content="",
            runs=[FormatRun(text="hello "), FormatRun(text="world")],
        )
        assert b.plain_text == "hello world"

    def test_has_mixed_format(self):
        b = DfmBlock(
            id="p001",
            block_type=DfmBlockType.PARAGRAPH,
            content="",
            runs=[
                FormatRun(text="bold", bold=True),
                FormatRun(text="normal"),
            ],
        )
        assert b.has_mixed_format

    def test_no_mixed_format_single_run(self):
        b = DfmBlock(
            id="p001",
            block_type=DfmBlockType.PARAGRAPH,
            content="",
            runs=[FormatRun(text="only one")],
        )
        assert not b.has_mixed_format


class TestDocxIR:
    def test_next_block_id(self):
        ir = DocxIR(doc_id="test", source_path="")
        assert ir.next_block_id(DfmBlockType.PARAGRAPH) == "p001"
        assert ir.next_block_id(DfmBlockType.PARAGRAPH) == "p002"
        assert ir.next_block_id(DfmBlockType.TABLE) == "t001"

    def test_find_block(self, sample_ir: DocxIR):
        block = sample_ir.find_block("h001")
        assert block is not None
        assert block.block_type == DfmBlockType.HEADING

        assert sample_ir.find_block("nonexistent") is None

    def test_get_blocks_by_type(self, sample_ir: DocxIR):
        paragraphs = sample_ir.get_blocks_by_type(DfmBlockType.PARAGRAPH)
        assert len(paragraphs) == 2

    def test_editable_blocks(self, sample_ir: DocxIR):
        assert len(sample_ir.editable_blocks) == 5

    def test_summary(self, sample_ir: DocxIR):
        s = sample_ir.get_summary()
        assert s["total_blocks"] == 5
        assert s["doc_id"] == "test_doc_001"


# ============================================================================
# Renderer Tests
# ============================================================================


class TestDfmRenderer:
    def test_render_has_frontmatter(self, renderer: DfmRenderer, sample_ir: DocxIR):
        result = renderer.render(sample_ir)
        assert result.startswith("---")
        assert (
            "dfm_version: '1.0'" in result
            or 'dfm_version: "1.0"' in result
            or "dfm_version: 1.0" in result
        )
        assert "doc_id: test_doc_001" in result

    def test_render_heading(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="h001",
            block_type=DfmBlockType.HEADING,
            content="Title",
            level=2,
        )
        result = renderer._render_heading(block)
        assert "## Title" in result
        assert "@b:h001" in result

    def test_render_paragraph(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="p001",
            block_type=DfmBlockType.PARAGRAPH,
            content="Hello world",
            style_name="Normal",
        )
        result = renderer._render_paragraph(block)
        assert "Hello world" in result
        assert "@b:p001" in result
        assert "s:Normal" in result

    def test_render_paragraph_with_runs(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="p001",
            block_type=DfmBlockType.PARAGRAPH,
            content="",
            runs=[
                FormatRun(text="bold", bold=True),
                FormatRun(text=" normal"),
            ],
        )
        result = renderer._render_paragraph(block)
        assert "**bold**" in result
        assert " normal" in result

    def test_render_list_item(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="l001",
            block_type=DfmBlockType.LIST_ITEM,
            content="item text",
            list_level=1,
        )
        result = renderer._render_list_item(block)
        assert "  - item text" in result
        assert "level:1" in result

    def test_render_table(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="t001",
            block_type=DfmBlockType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            table_style="TableGrid",
        )
        result = renderer._render_table(block)
        assert "<!-- dfm:table @b:t001" in result
        assert "<!-- /dfm:table -->" in result
        assert "| A | B |" in result

    def test_render_table_with_merged_cells(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="t001",
            block_type=DfmBlockType.TABLE,
            content="| A | B |\n| --- | --- |\n| 1 | 2 |",
            merged_cells=[MergedCell(row=0, col=0, row_span=2, col_span=1)],
        )
        result = renderer._render_table(block)
        assert "⚠️" in result
        assert "merged_cells" in result

    def test_render_chart(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="c001",
            block_type=DfmBlockType.CHART,
            content="Revenue Chart",
            chart_type="bar",
            binary_ref="parts/chart1.xml",
        )
        result = renderer._render_chart(block)
        assert "📊" in result
        assert "dfm:chart" in result
        assert "Revenue Chart" in result

    def test_render_toc(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="toc001",
            block_type=DfmBlockType.TOC,
            content="",
            toc_depth=3,
        )
        result = renderer._render_toc(block)
        assert "🔖" in result
        assert "dfm:toc" in result

    def test_render_bookmark(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="bm001",
            block_type=DfmBlockType.BOOKMARK,
            content="",
            bookmark_name="ref_intro",
        )
        result = renderer._render_bookmark(block)
        assert 'name:"ref_intro"' in result

    def test_render_break(self, renderer: DfmRenderer):
        block = DfmBlock(
            id="br001",
            block_type=DfmBlockType.BREAK,
            content="",
            break_type=BreakType.PAGE,
        )
        result = renderer._render_break(block)
        assert "type:page" in result

    def test_runs_to_md_bold_italic(self):
        runs = [
            FormatRun(text="both", bold=True, italic=True),
            FormatRun(text=" strike", strike=True),
        ]
        result = DfmRenderer._runs_to_md(runs)
        assert "***both***" in result
        assert "~~ strike~~" in result

    def test_render_complete(self, renderer: DfmRenderer, sample_ir: DocxIR):
        result = renderer.render(sample_ir)
        # Should have frontmatter, styles, and all blocks
        assert "---" in result
        assert "dfm:styles" in result
        assert "# Introduction" in result
        assert "This is a simple paragraph" in result
        assert "dfm:table" in result


# ============================================================================
# Parser Tests
# ============================================================================


class TestDfmParser:
    def test_parse_frontmatter(self, parser: DfmParser):
        dfm = "---\ndoc_id: test_001\nsource: test.docx\nchecksum: abc123\n---\n"
        result = parser.parse(dfm)
        assert result.doc_id == "test_001"
        assert result.source == "test.docx"
        assert result.checksum == "abc123"

    def test_parse_missing_frontmatter(self, parser: DfmParser):
        result = parser.parse("no frontmatter here")
        assert len(result.errors) > 0

    def test_parse_simple_paragraph(self, parser: DfmParser):
        dfm = (
            "---\ndoc_id: x\nsource: x\nchecksum: x\n---\n\n"
            "<!-- @b:p001 s:Normal -->\n"
            "Hello world\n"
        )
        result = parser.parse(dfm)
        edits = [e for e in result.edits if e.block_id == "p001"]
        assert len(edits) == 1
        assert edits[0].new_content == "Hello world"

    def test_parse_heading(self, parser: DfmParser):
        dfm = (
            "---\ndoc_id: x\nsource: x\nchecksum: x\n---\n\n"
            "<!-- @b:h001 -->\n"
            "## My Heading\n"
        )
        result = parser.parse(dfm)
        edits = [e for e in result.edits if e.block_id == "h001"]
        assert len(edits) == 1
        assert edits[0].block_type == DfmBlockType.HEADING
        assert edits[0].new_content == "My Heading"

    def test_parse_bold_text(self, parser: DfmParser):
        dfm = (
            "---\ndoc_id: x\nsource: x\nchecksum: x\n---\n\n"
            "<!-- @b:p001 -->\n"
            "This is **bold** text\n"
        )
        result = parser.parse(dfm)
        edits = [e for e in result.edits if e.block_id == "p001"]
        assert len(edits) == 1
        assert edits[0].new_content == "This is bold text"

    def test_parse_compound_table(self, parser: DfmParser):
        dfm = (
            "---\ndoc_id: x\nsource: x\nchecksum: x\n---\n\n"
            "<!-- dfm:table @b:t001\nstyle: TableGrid\n-->\n"
            "| A | B |\n"
            "| --- | --- |\n"
            "| 1 | 2 |\n"
            "<!-- /dfm:table -->\n"
        )
        result = parser.parse(dfm)
        edits = [e for e in result.edits if e.block_id == "t001"]
        assert len(edits) == 1
        assert edits[0].table_rows is not None
        assert len(edits[0].table_rows) == 2  # Header + 1 data row
        assert edits[0].table_rows[0] == ["A", "B"]
        assert edits[0].table_rows[1] == ["1", "2"]

    def test_parse_bookmark(self, parser: DfmParser):
        dfm = (
            "---\ndoc_id: x\nsource: x\nchecksum: x\n---\n\n"
            '<!-- dfm:bookmark @b:bm001 name:"intro" -->\n'
        )
        result = parser.parse(dfm)
        edits = [e for e in result.edits if e.block_id == "bm001"]
        assert len(edits) == 1
        assert edits[0].block_type == DfmBlockType.BOOKMARK

    def test_parse_break(self, parser: DfmParser):
        dfm = (
            "---\ndoc_id: x\nsource: x\nchecksum: x\n---\n\n"
            "<!-- dfm:break @b:br001 type:page -->\n"
        )
        result = parser.parse(dfm)
        edits = [e for e in result.edits if e.block_id == "br001"]
        assert len(edits) == 1
        assert edits[0].block_type == DfmBlockType.BREAK

    def test_md_to_plain(self, parser: DfmParser):
        assert parser._md_to_plain("**bold**") == "bold"
        assert parser._md_to_plain("*italic*") == "italic"
        assert parser._md_to_plain("***both***") == "both"
        assert parser._md_to_plain("~~strike~~") == "strike"
        assert parser._md_to_plain("^super^") == "super"

    def test_parse_md_table(self, parser: DfmParser):
        table = "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"
        rows = parser._parse_md_table(table)
        assert rows is not None
        assert len(rows) == 3
        assert rows[0] == ["A", "B"]

    def test_rows_to_md_table(self, parser: DfmParser):
        rows = [["A", "B"], ["1", "2"]]
        result = parser._rows_to_md_table(rows)
        assert "| A | B |" in result
        assert "| 1 | 2 |" in result
        assert "| --- | --- |" in result


# ============================================================================
# Format Merge Tests
# ============================================================================


class TestFormatMerge:
    def test_small_edit_proportional(self, parser: DfmParser):
        runs = [
            FormatRun(text="Hello", bold=True),
            FormatRun(text=" World", italic=True),
        ]
        # Small edit: "Hello World" (11) → "Hello Worl" (10), ~9% change
        result = parser._merge_runs(runs, "Hello World", "Hello Worl")
        assert len(result) == 2
        assert result[0].bold is True
        assert result[1].italic is True

    def test_large_edit_primary_format(self, parser: DfmParser):
        runs = [
            FormatRun(text="Hello", bold=True),
            FormatRun(text=" World", italic=True),
        ]
        # Large edit: "Hello World" (11) → "Completely changed" (18), ~63% change
        result = parser._merge_runs(runs, "Hello World", "Completely changed")
        assert len(result) == 1
        assert result[0].bold is True  # Primary run format
        assert result[0].text == "Completely changed"

    def test_empty_runs(self, parser: DfmParser):
        result = parser._merge_runs([], "old", "new")
        assert len(result) == 1
        assert result[0].text == "new"


# ============================================================================
# Round-trip Tests
# ============================================================================


class TestRoundTrip:
    def test_render_then_parse(
        self, renderer: DfmRenderer, parser: DfmParser, sample_ir: DocxIR
    ):
        """Render IR → DFM text → parse back → verify block IDs match."""
        dfm_text = renderer.render(sample_ir)
        parse_result = parser.parse(dfm_text)

        # Should have no errors
        assert len(parse_result.errors) == 0

        # Should find frontmatter data
        assert parse_result.doc_id == "test_doc_001"
        assert parse_result.checksum == "abc123"

        # Should find edits for all blocks
        edit_ids = {e.block_id for e in parse_result.edits}
        original_ids = {b.id for b in sample_ir.blocks}
        assert original_ids.issubset(edit_ids)

    def test_apply_edits_paragraph(
        self, renderer: DfmRenderer, parser: DfmParser, sample_ir: DocxIR
    ):
        """Edit a paragraph and verify it gets applied."""
        dfm_text = renderer.render(sample_ir)

        # Modify the paragraph text
        dfm_text = dfm_text.replace(
            "This is a simple paragraph.",
            "This is a modified paragraph.",
        )

        parse_result = parser.parse(dfm_text)
        ir = parser.apply_edits(sample_ir, parse_result)

        block = ir.find_block("p001")
        assert block is not None
        assert "modified" in block.content

    def test_apply_edits_heading(
        self, renderer: DfmRenderer, parser: DfmParser, sample_ir: DocxIR
    ):
        """Edit a heading and verify."""
        dfm_text = renderer.render(sample_ir)
        dfm_text = dfm_text.replace("# Introduction", "# New Title")

        parse_result = parser.parse(dfm_text)
        ir = parser.apply_edits(sample_ir, parse_result)

        block = ir.find_block("h001")
        assert block is not None
        assert block.content == "New Title"
