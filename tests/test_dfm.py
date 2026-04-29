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
from pathlib import Path

import pytest
from lxml import etree

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
from src.infrastructure.docx_adapter import NS, DocxAdapter

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
        assert not DfmBlockType.CITATION.is_editable
        assert not DfmBlockType.CHART.is_editable
        assert not DfmBlockType.MACRO.is_editable

    def test_protected_types(self):
        assert DfmBlockType.CHART.is_protected
        assert DfmBlockType.TOC.is_protected
        assert DfmBlockType.CITATION.is_protected
        assert DfmBlockType.REVISION.is_protected
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


class TestDocxAdapterParsing:
    def test_numbered_paragraph_without_list_style_is_list_item(self):
        p = etree.fromstring(
            f"""
            <w:p xmlns:w="{NS["w"]}">
              <w:pPr>
                <w:pStyle w:val="Normal"/>
                <w:numPr>
                  <w:ilvl w:val="2"/>
                  <w:numId w:val="7"/>
                </w:numPr>
              </w:pPr>
              <w:r><w:t>Nested numbered item</w:t></w:r>
            </w:p>
            """
        )
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            source_filename="test.docx",
            checksum="abc123",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
        )

        DocxAdapter()._parse_paragraph(p, ir, {}, Path.cwd())

        assert len(ir.blocks) == 1
        block = ir.blocks[0]
        assert block.block_type == DfmBlockType.LIST_ITEM
        assert block.list_level == 2
        assert block.num_id == 7

    def test_corrupt_numbering_values_do_not_abort_paragraph_parse(self):
        p = etree.fromstring(
            f"""
            <w:p xmlns:w="{NS["w"]}">
              <w:pPr>
                <w:numPr>
                  <w:ilvl w:val="not-an-int"/>
                  <w:numId w:val="also-bad"/>
                </w:numPr>
              </w:pPr>
              <w:r><w:t>Converted list-ish text</w:t></w:r>
            </w:p>
            """
        )
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            source_filename="test.docx",
            checksum="abc123",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
        )

        DocxAdapter()._parse_paragraph(p, ir, {}, Path.cwd())

        assert len(ir.blocks) == 1
        assert ir.blocks[0].block_type == DfmBlockType.PARAGRAPH

    def test_hyperlink_runs_are_parsed_and_cleared_on_edit(self):
        p = etree.fromstring(
            f"""
            <w:p xmlns:w="{NS["w"]}" xmlns:r="{NS["r"]}">
              <w:r><w:t>Prefix </w:t></w:r>
              <w:hyperlink r:id="rId1">
                <w:r><w:t>LINK</w:t></w:r>
              </w:hyperlink>
              <w:r><w:t> Suffix</w:t></w:r>
            </w:p>
            """
        )
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            source_filename="test.docx",
            checksum="abc123",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
        )
        adapter = DocxAdapter()

        adapter._parse_paragraph(p, ir, {}, Path.cwd())
        assert ir.blocks[0].content == "Prefix LINK Suffix"

        adapter._update_paragraph_text(
            p,
            DfmBlock(
                id="p001",
                block_type=DfmBlockType.PARAGRAPH,
                content="Replacement",
            ),
        )

        assert adapter._get_paragraph_text(p) == "Replacement"
        assert p.find(f"{{{NS['w']}}}hyperlink") is not None

    def test_tracked_insert_and_delete_are_exposed_as_revision_blocks(self):
        p = etree.fromstring(
            f"""
            <w:p xmlns:w="{NS["w"]}">
              <w:r><w:t>Keep </w:t></w:r>
              <w:ins w:id="1" w:author="Alice" w:date="2026-04-29T01:02:03Z">
                <w:r><w:t>added</w:t></w:r>
              </w:ins>
              <w:del w:id="2" w:author="Bob" w:date="2026-04-29T02:03:04Z">
                <w:r><w:delText>removed</w:delText></w:r>
              </w:del>
              <w:r><w:t> tail</w:t></w:r>
            </w:p>
            """
        )
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            source_filename="test.docx",
            checksum="abc123",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
        )

        DocxAdapter()._parse_paragraph(p, ir, {}, Path.cwd())

        assert ir.blocks[0].content == "Keep added tail"
        revisions = ir.get_blocks_by_type(DfmBlockType.REVISION)
        assert [block.revision_type for block in revisions] == ["insert", "delete"]
        assert [block.content for block in revisions] == ["added", "removed"]
        assert revisions[0].revision_author == "Alice"
        assert revisions[0].metadata["revision_id"] == "1"
        assert revisions[0].metadata["source_tag"] == "w:ins"
        assert revisions[0].metadata["source_block_id"] == ir.blocks[0].id
        assert revisions[1].revision_author == "Bob"
        assert revisions[1].metadata["visible_in_current_text"] is False

    def test_table_tracked_changes_are_exposed_without_polluting_cell_text(
        self,
        tmp_path: Path,
    ):
        tbl = etree.fromstring(
            f"""
            <w:tbl xmlns:w="{NS["w"]}">
              <w:tr>
                <w:tc>
                  <w:p>
                    <w:r><w:t>A </w:t></w:r>
                    <w:del w:id="3" w:author="Reviewer">
                      <w:r><w:delText>B</w:delText></w:r>
                    </w:del>
                    <w:ins w:id="4" w:author="Reviewer">
                      <w:r><w:t>C</w:t></w:r>
                    </w:ins>
                  </w:p>
                </w:tc>
              </w:tr>
            </w:tbl>
            """
        )
        ir = DocxIR(doc_id="test_doc_001", source_path="test.docx")

        DocxAdapter()._parse_table(tbl, ir, {}, tmp_path, tmp_path)

        table_block = ir.blocks[0]
        assert table_block.block_type == DfmBlockType.TABLE
        assert "A C" in table_block.content
        assert "B" not in table_block.content
        revisions = ir.get_blocks_by_type(DfmBlockType.REVISION)
        assert [block.revision_type for block in revisions] == ["delete", "insert"]
        assert [block.content for block in revisions] == ["B", "C"]
        assert revisions[0].metadata["source_block_id"] == table_block.id

    def test_revision_blocks_do_not_shift_docx_writeback_alignment(self):
        doc_xml = f"""
        <w:document xmlns:w="{NS["w"]}">
          <w:body>
            <w:p><w:r><w:t>One</w:t></w:r></w:p>
            <w:p><w:r><w:t>Two</w:t></w:r></w:p>
          </w:body>
        </w:document>
        """.encode()
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            blocks=[
                DfmBlock(
                    id="p001",
                    block_type=DfmBlockType.PARAGRAPH,
                    content="One",
                ),
                DfmBlock(
                    id="rev001",
                    block_type=DfmBlockType.REVISION,
                    content="deleted",
                    revision_type="delete",
                ),
                DfmBlock(
                    id="p002",
                    block_type=DfmBlockType.PARAGRAPH,
                    content="Changed two",
                ),
            ],
        )

        updated = DocxAdapter()._apply_text_changes(
            doc_xml,
            ir,
            changed_block_ids={"p002"},
        )

        tree = etree.fromstring(updated)
        texts = [t.text for t in tree.findall(f".//{{{NS['w']}}}t")]
        assert texts == ["One", "Changed two"]


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

    def test_render_revision_includes_track_change_metadata(
        self,
        renderer: DfmRenderer,
    ):
        block = DfmBlock(
            id="rev001",
            block_type=DfmBlockType.REVISION,
            content="removed text",
            revision_type="delete",
            revision_author="Alice",
            revision_date="2026-04-29T01:02:03Z",
            metadata={
                "revision_id": "7",
                "source_tag": "w:del",
                "scope": "paragraph",
                "source_block_id": "p001",
                "visible_in_current_text": False,
            },
        )

        result = renderer._render_revision(block)

        assert "<!-- dfm:revision @b:rev001" in result
        assert "type: delete" in result
        assert "revision_id: '7'" in result
        assert "source_tag: w:del" in result
        assert "source_block_id: p001" in result
        assert "visible_in_current_text: false" in result
        assert "removed text" in result

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

    @pytest.mark.parametrize(
        "block_type, block_id",
        [
            (DfmBlockType.FIELD, "f001"),
            (DfmBlockType.HEADER, "hdr001"),
            (DfmBlockType.FOOTER, "ftr001"),
        ],
    )
    def test_protected_compound_blocks_do_not_swallow_following_edits(
        self,
        renderer: DfmRenderer,
        parser: DfmParser,
        block_type: DfmBlockType,
        block_id: str,
    ):
        ir = DocxIR(doc_id="docx_1", source_path="demo.docx", checksum="abc")
        ir.blocks.append(DfmBlock(id=block_id, block_type=block_type, content=""))
        ir.blocks.append(
            DfmBlock(
                id="p001",
                block_type=DfmBlockType.PARAGRAPH,
                content="Original paragraph",
            )
        )

        dfm = renderer.render(ir).replace("Original paragraph", "Edited paragraph")
        result = parser.parse(dfm)

        edit = next(e for e in result.edits if e.block_id == "p001")
        assert edit.new_content == "Edited paragraph"

    def test_md_to_plain(self, parser: DfmParser):
        assert parser._md_to_plain("**bold**") == "bold"
        assert parser._md_to_plain("*italic*") == "italic"
        assert parser._md_to_plain("***both***") == "both"
        assert parser._md_to_plain("~~strike~~") == "strike"
        assert parser._md_to_plain("^super^") == "super"
        literal = r"x \~not sub\~ y \^not super\^ z \\ slash \*stars\*"
        assert (
            parser._md_to_plain(literal)
            == "x ~not sub~ y ^not super^ z \\ slash *stars*"
        )

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

    def test_parse_md_table_with_br(self, parser: DfmParser):
        """Cells containing <br> should be restored to real newlines."""
        table = "| Col |\n| --- |\n| Line 1<br>Line 2 |"
        rows = parser._parse_md_table(table)
        assert rows is not None
        assert rows[1][0] == "Line 1\nLine 2"

    def test_rows_to_md_table_with_newline(self, parser: DfmParser):
        """Newlines in cell data should be escaped as <br>."""
        rows = [["Col"], ["Line 1\nLine 2"]]
        result = parser._rows_to_md_table(rows)
        assert "<br>" in result
        assert "Line 1\nLine 2" not in result

    def test_md_table_newline_roundtrip(self, parser: DfmParser):
        """Round-trip: rows with newlines → md → parse → same rows."""
        original = [["Header"], ["A\nB\nC"], ["Simple"]]
        md = parser._rows_to_md_table(original)
        parsed = parser._parse_md_table(md)
        assert parsed is not None
        assert parsed[1][0] == "A\nB\nC"
        assert parsed[2][0] == "Simple"

    def test_md_table_escaped_pipe_roundtrip(self, parser: DfmParser):
        """Round-trip: literal pipes inside cells must not create columns."""
        original = [["A", "B"], ["x|y", r"path\name"]]
        md = parser._rows_to_md_table(original)
        parsed = parser._parse_md_table(md)
        assert parsed == original

    def test_docx_adapter_table_builder_escapes_literal_pipes(self, parser: DfmParser):
        md = DocxAdapter._rows_to_md_table([["A", "B"], ["x|y", "z"]])
        parsed = parser._parse_md_table(md)
        assert parsed == [["A", "B"], ["x|y", "z"]]

    def test_docx_adapter_table_parser_handles_escaped_literal_pipes(self):
        md = "| A | B |\n| --- | --- |\n| x\\|y | z |"

        parsed = DocxAdapter._parse_md_table(md)

        assert parsed == [["A", "B"], ["x|y", "z"]]


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

    def test_split_noop_preserves_literal_markdown_and_marker_comments(
        self, renderer: DfmRenderer, parser: DfmParser
    ):
        content = (
            "Keep *literal* **stars** ~~tildes~~ ^carets^ "
            "<!-- @p999 --> <!-- @b:p999 -->"
        )
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            source_filename="test.docx",
            checksum="abc123",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            blocks=[
                DfmBlock(
                    id="p001",
                    block_type=DfmBlockType.PARAGRAPH,
                    content=content,
                )
            ],
        )

        md_text, yaml_text = renderer.render_split(ir)
        parse_result = parser.parse_split(md_text, yaml_text)
        updated = parser.apply_edits(ir, parse_result)

        assert parse_result.errors == []
        assert "\\*" in md_text
        assert "\\<!--" in md_text
        assert updated.find_block("p001").content == content

    def test_single_dfm_noop_preserves_literal_markdown_and_marker_comments(
        self, renderer: DfmRenderer, parser: DfmParser
    ):
        content = "Keep *literal* and <!-- @b:p999 --> as text"
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            source_filename="test.docx",
            checksum="abc123",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            blocks=[
                DfmBlock(
                    id="p001",
                    block_type=DfmBlockType.PARAGRAPH,
                    content=content,
                )
            ],
        )

        dfm_text = renderer.render(ir)
        parse_result = parser.parse(dfm_text)
        updated = parser.apply_edits(ir, parse_result)

        assert parse_result.errors == []
        assert updated.find_block("p001").content == content

    def test_multiline_list_item_roundtrips_in_split_and_single_dfm(
        self, renderer: DfmRenderer, parser: DfmParser
    ):
        content = "first line\nsecond line with *literal* marker"
        ir = DocxIR(
            doc_id="test_doc_001",
            source_path="test.docx",
            source_filename="test.docx",
            checksum="abc123",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            blocks=[
                DfmBlock(
                    id="l001",
                    block_type=DfmBlockType.LIST_ITEM,
                    content=content,
                    list_level=1,
                )
            ],
        )

        md_text, yaml_text = renderer.render_split(ir)
        split_result = parser.parse_split(md_text, yaml_text)
        split_updated = parser.apply_edits(ir, split_result)

        dfm_text = renderer.render(split_updated)
        single_result = parser.parse(dfm_text)
        single_updated = parser.apply_edits(split_updated, single_result)

        assert split_result.errors == []
        assert single_result.errors == []
        assert single_updated.find_block("l001").content == content

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
