"""
Tests for DfmTableBridge — DFM ↔ TableContext bidirectional conversion.

Covers:
- block_to_table_context: DfmBlock(TABLE) → TableContext
- table_context_to_block: TableContext → DfmBlock(TABLE)
- apply_table_context_to_ir: write back into IR
- extract_chart_data: chart block → TableContext (metadata + XML)
- extract_all_tables: batch extraction
- _parse_md_table / _table_context_to_md helpers
- Round-trip: block → tc → block
"""

from __future__ import annotations

import pytest

from src.application.dfm_table_bridge import (
    DfmTableBridge,
    _infer_column_type,
    _parse_md_table,
    _table_context_to_md,
)
from src.domain.docx_entities import (
    CellFormat,
    DfmBlock,
    DocxIR,
    MergedCell,
)
from src.domain.docx_value_objects import DfmBlockType
from src.domain.table_entities import ColumnDef, TableContext

# ============================================================================
# Fixtures
# ============================================================================


def _make_table_block(
    block_id: str = "t001",
    content: str | None = None,
    **kwargs,
) -> DfmBlock:
    """Create a TABLE DfmBlock for testing."""
    if content is None:
        content = (
            "| Name | Age | Score |\n"
            "| --- | --- | --- |\n"
            "| Alice | 30 | 95.5 |\n"
            "| Bob | 25 | 88 |"
        )
    return DfmBlock(
        id=block_id,
        block_type=DfmBlockType.TABLE,
        content=content,
        **kwargs,
    )


def _make_chart_block(block_id: str = "c001") -> DfmBlock:
    """Create a CHART DfmBlock for testing."""
    return DfmBlock(
        id=block_id,
        block_type=DfmBlockType.CHART,
        content="Sales Distribution",
        chart_type="bar",
        binary_ref="assets/chart_c001.bin",
        image_width_cm=12.0,
        image_height_cm=8.0,
        data_hash="abc123",
    )


def _make_ir() -> DocxIR:
    """Create a minimal DocxIR with one table for testing."""
    ir = DocxIR(
        doc_id="test_doc", source_path="/test.docx", source_filename="test.docx"
    )
    ir.add_block(_make_table_block("t001"))
    ir.add_block(
        DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="Hello")
    )
    ir.add_block(
        _make_table_block(
            "t002",
            content="| X | Y |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |",
        )
    )
    return ir


# ============================================================================
# _parse_md_table
# ============================================================================


class TestParseMdTable:
    def test_basic_table(self):
        text = "| A | B |\n| --- | --- |\n| 1 | 2 |\n| 3 | 4 |"
        rows = _parse_md_table(text)
        assert rows is not None
        assert len(rows) == 3
        assert rows[0] == ["A", "B"]
        assert rows[1] == ["1", "2"]
        assert rows[2] == ["3", "4"]

    def test_empty_string(self):
        assert _parse_md_table("") is None
        assert _parse_md_table("   ") is None

    def test_no_table_format(self):
        assert _parse_md_table("just text\nmore text") is None

    def test_table_with_extra_whitespace(self):
        text = "|  Name  |  Value  |\n| --- | --- |\n|  foo  |  bar  |"
        rows = _parse_md_table(text)
        assert rows is not None
        assert rows[0] == ["Name", "Value"]
        assert rows[1] == ["foo", "bar"]

    def test_alignment_separator(self):
        text = "| L | C | R |\n|:---|:---:|---:|\n| a | b | c |"
        rows = _parse_md_table(text)
        assert rows is not None
        assert len(rows) == 2  # Header + data, separator skipped

    def test_single_column(self):
        text = "| Only |\n| --- |\n| val |"
        rows = _parse_md_table(text)
        assert rows is not None
        assert rows[0] == ["Only"]
        assert rows[1] == ["val"]


# ============================================================================
# _table_context_to_md
# ============================================================================


class TestTableContextToMd:
    def test_basic_conversion(self):
        tc = TableContext(
            id="test",
            intent="summary",
            title="Test",
            columns=[
                ColumnDef(name="X", type="text"),
                ColumnDef(name="Y", type="number"),
            ],
            rows=[{"X": "a", "Y": 1}, {"X": "b", "Y": 2}],
        )
        md = _table_context_to_md(tc)
        assert "| X | Y |" in md
        assert "| --- | --- |" in md
        assert "| a | 1 |" in md
        assert "| b | 2 |" in md

    def test_empty_columns(self):
        tc = TableContext(
            id="test", intent="summary", title="Test", columns=[], rows=[]
        )
        assert _table_context_to_md(tc) == ""

    def test_pipe_in_cell_escaped(self):
        tc = TableContext(
            id="test",
            intent="summary",
            title="Test",
            columns=[ColumnDef(name="Val", type="text")],
            rows=[{"Val": "a|b"}],
        )
        md = _table_context_to_md(tc)
        assert "a\\|b" in md


# ============================================================================
# _infer_column_type
# ============================================================================


class TestInferColumnType:
    def test_numeric(self):
        col = ColumnDef(name="score", type="text")
        rows = [{"score": "95.5"}, {"score": "88"}, {"score": "100"}]
        _infer_column_type(col, rows)
        assert col.type == "number"

    def test_mixed_stays_text(self):
        col = ColumnDef(name="val", type="text")
        rows = [{"val": "95.5"}, {"val": "hello"}, {"val": "100"}]
        _infer_column_type(col, rows)
        assert col.type == "text"

    def test_empty_stays_text(self):
        col = ColumnDef(name="val", type="text")
        _infer_column_type(col, [])
        assert col.type == "text"

    def test_comma_number(self):
        col = ColumnDef(name="price", type="text")
        rows = [{"price": "1,000"}, {"price": "2,500"}]
        _infer_column_type(col, rows)
        assert col.type == "number"


# ============================================================================
# DfmTableBridge.block_to_table_context
# ============================================================================


class TestBlockToTableContext:
    def test_basic_conversion(self):
        block = _make_table_block()
        tc = DfmTableBridge.block_to_table_context(block, doc_id="doc1")

        assert tc.id.startswith("dfm_t001_")
        assert len(tc.columns) == 3
        assert tc.column_names == ["Name", "Age", "Score"]
        assert tc.row_count == 2
        assert tc.rows[0]["Name"] == "Alice"
        assert tc.rows[1]["Age"] == "25"

    def test_column_type_inference(self):
        block = _make_table_block()
        tc = DfmTableBridge.block_to_table_context(block)

        # Age and Score are numeric
        name_col = next(c for c in tc.columns if c.name == "Name")
        age_col = next(c for c in tc.columns if c.name == "Age")
        score_col = next(c for c in tc.columns if c.name == "Score")
        assert name_col.type == "text"
        assert age_col.type == "number"
        assert score_col.type == "number"

    def test_wrong_block_type_raises(self):
        block = DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="text")
        with pytest.raises(ValueError, match="Expected TABLE"):
            DfmTableBridge.block_to_table_context(block)

    def test_empty_table(self):
        block = _make_table_block(content="")
        tc = DfmTableBridge.block_to_table_context(block)
        assert tc.row_count == 0
        assert len(tc.columns) == 0

    def test_source_description(self):
        block = _make_table_block()
        tc = DfmTableBridge.block_to_table_context(
            block, doc_id="d1", source_description="custom source"
        )
        assert tc.source_description == "custom source"


# ============================================================================
# DfmTableBridge.table_context_to_block
# ============================================================================


class TestTableContextToBlock:
    def test_new_block(self):
        tc = TableContext(
            id="test",
            intent="comparison",
            title="Test",
            columns=[
                ColumnDef(name="A", type="text"),
                ColumnDef(name="B", type="number"),
            ],
            rows=[{"A": "x", "B": 10}],
        )
        block = DfmTableBridge.table_context_to_block(tc, block_id="t999")
        assert block.id == "t999"
        assert block.block_type == DfmBlockType.TABLE
        assert "| A | B |" in block.content
        assert "| x | 10 |" in block.content

    def test_preserve_original_metadata(self):
        original = _make_table_block(
            table_style="Grid Table 4",
            col_widths=[3.0, 2.0, 2.0],
        )
        original.merged_cells = [MergedCell(row=0, col=0, row_span=2)]
        original.cell_formats = {"0:0": CellFormat(bold=True)}

        tc = TableContext(
            id="test",
            intent="summary",
            title="T",
            columns=[ColumnDef(name="A", type="text")],
            rows=[{"A": "new"}],
        )

        block = DfmTableBridge.table_context_to_block(tc, original_block=original)
        assert block.id == "t001"  # Inherited from original
        assert block.table_style == "Grid Table 4"
        assert block.col_widths == [3.0, 2.0, 2.0]
        assert len(block.merged_cells) == 1
        assert block.cell_formats["0:0"].bold is True
        assert "| new |" in block.content  # Content updated

    def test_block_id_override(self):
        tc = TableContext(
            id="t",
            intent="summary",
            title="T",
            columns=[ColumnDef(name="X", type="text")],
            rows=[],
        )
        original = _make_table_block()
        block = DfmTableBridge.table_context_to_block(
            tc, original_block=original, block_id="t_override"
        )
        assert block.id == "t_override"


# ============================================================================
# DfmTableBridge.apply_table_context_to_ir
# ============================================================================


class TestApplyTableContextToIR:
    def test_update_existing_block(self):
        ir = _make_ir()
        tc = TableContext(
            id="new",
            intent="summary",
            title="Updated",
            columns=[
                ColumnDef(name="Name", type="text"),
                ColumnDef(name="Age", type="number"),
                ColumnDef(name="Score", type="number"),
            ],
            rows=[{"Name": "Charlie", "Age": 35, "Score": 99}],
        )

        DfmTableBridge.apply_table_context_to_ir(ir, "t001", tc)
        block = ir.find_block("t001")
        assert block is not None
        assert "Charlie" in block.content
        assert "99" in block.content

    def test_block_not_found_raises(self):
        ir = _make_ir()
        tc = TableContext(id="x", intent="summary", title="X", columns=[], rows=[])
        with pytest.raises(ValueError, match="Block not found"):
            DfmTableBridge.apply_table_context_to_ir(ir, "t999", tc)

    def test_non_table_block_raises(self):
        ir = _make_ir()
        tc = TableContext(id="x", intent="summary", title="X", columns=[], rows=[])
        with pytest.raises(ValueError, match="not TABLE"):
            DfmTableBridge.apply_table_context_to_ir(ir, "p001", tc)


# ============================================================================
# DfmTableBridge.extract_chart_data — metadata only
# ============================================================================


class TestExtractChartData:
    def test_metadata_only(self):
        block = _make_chart_block()
        tc = DfmTableBridge.extract_chart_data(block)
        assert tc is not None
        assert tc.id == "chart_c001"
        assert tc.row_count == 5
        # Check metadata rows
        props = {r["property"]: r["value"] for r in tc.rows}
        assert props["chart_type"] == "bar"
        assert props["width_cm"] == "12.0"
        assert props["binary_ref"] == "assets/chart_c001.bin"

    def test_wrong_type_returns_none(self):
        block = DfmBlock(id="p001", block_type=DfmBlockType.PARAGRAPH, content="text")
        assert DfmTableBridge.extract_chart_data(block) is None


# ============================================================================
# DfmTableBridge.extract_chart_data — XML parsing
# ============================================================================


class TestExtractChartDataXML:
    SAMPLE_CHART_XML = """<?xml version="1.0" encoding="UTF-8"?>
<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"
              xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <c:chart>
    <c:plotArea>
      <c:barChart>
        <c:ser>
          <c:tx>
            <c:strRef>
              <c:strCache>
                <c:pt idx="0"><c:v>Revenue</c:v></c:pt>
              </c:strCache>
            </c:strRef>
          </c:tx>
          <c:cat>
            <c:strRef>
              <c:strCache>
                <c:pt idx="0"><c:v>Q1</c:v></c:pt>
                <c:pt idx="1"><c:v>Q2</c:v></c:pt>
                <c:pt idx="2"><c:v>Q3</c:v></c:pt>
              </c:strCache>
            </c:strRef>
          </c:cat>
          <c:val>
            <c:numRef>
              <c:numCache>
                <c:pt idx="0"><c:v>100</c:v></c:pt>
                <c:pt idx="1"><c:v>200</c:v></c:pt>
                <c:pt idx="2"><c:v>300</c:v></c:pt>
              </c:numCache>
            </c:numRef>
          </c:val>
        </c:ser>
        <c:ser>
          <c:tx>
            <c:strRef>
              <c:strCache>
                <c:pt idx="0"><c:v>Profit</c:v></c:pt>
              </c:strCache>
            </c:strRef>
          </c:tx>
          <c:val>
            <c:numRef>
              <c:numCache>
                <c:pt idx="0"><c:v>20</c:v></c:pt>
                <c:pt idx="1"><c:v>50</c:v></c:pt>
                <c:pt idx="2"><c:v>80</c:v></c:pt>
              </c:numCache>
            </c:numRef>
          </c:val>
        </c:ser>
      </c:barChart>
    </c:plotArea>
  </c:chart>
</c:chartSpace>"""

    def test_parse_bar_chart(self):
        block = _make_chart_block()
        tc = DfmTableBridge.extract_chart_data(block, self.SAMPLE_CHART_XML)
        assert tc is not None
        assert tc.title.startswith("Chart Data:")
        assert len(tc.columns) == 3  # Category, Revenue, Profit
        assert tc.column_names == ["Category", "Revenue", "Profit"]
        assert tc.row_count == 3

        # Check data
        assert tc.rows[0]["Category"] == "Q1"
        assert tc.rows[0]["Revenue"] == 100.0
        assert tc.rows[0]["Profit"] == 20.0
        assert tc.rows[2]["Category"] == "Q3"
        assert tc.rows[2]["Revenue"] == 300.0
        assert tc.rows[2]["Profit"] == 80.0

    def test_invalid_xml_returns_none(self):
        block = _make_chart_block()
        tc = DfmTableBridge.extract_chart_data(block, "not xml at all")
        assert tc is None


# ============================================================================
# DfmTableBridge.extract_all_tables
# ============================================================================


class TestExtractAllTables:
    def test_extract_all(self):
        ir = _make_ir()
        tables = DfmTableBridge.extract_all_tables(ir)
        assert len(tables) == 2
        assert "t001" in tables
        assert "t002" in tables
        assert tables["t001"].column_names == ["Name", "Age", "Score"]
        assert tables["t002"].column_names == ["X", "Y"]

    def test_empty_ir(self):
        ir = DocxIR(doc_id="empty", source_path="")
        assert DfmTableBridge.extract_all_tables(ir) == {}


# ============================================================================
# Round-trip: block → tc → block
# ============================================================================


class TestRoundTrip:
    def test_content_preserved(self):
        original = _make_table_block(
            table_style="GridStyle",
            col_widths=[3.0, 2.0, 2.5],
        )

        # Forward
        tc = DfmTableBridge.block_to_table_context(original)
        assert tc.row_count == 2

        # Modify
        tc.rows.append({"Name": "Charlie", "Age": "35", "Score": "77"})

        # Backward
        result = DfmTableBridge.table_context_to_block(tc, original_block=original)

        assert result.table_style == "GridStyle"
        assert result.col_widths == [3.0, 2.0, 2.5]
        assert "Charlie" in result.content
        assert "Alice" in result.content

        # Re-parse to verify structure
        rows = _parse_md_table(result.content)
        assert rows is not None
        assert len(rows) == 4  # header + 3 data rows

    def test_ir_round_trip(self):
        ir = _make_ir()

        # Extract
        tc = DfmTableBridge.block_to_table_context(ir.find_block("t001"))

        # Modify
        tc.rows[0]["Name"] = "Modified"

        # Write back
        DfmTableBridge.apply_table_context_to_ir(ir, "t001", tc)

        block = ir.find_block("t001")
        assert "Modified" in block.content
        # Other blocks unchanged
        assert ir.find_block("p001").content == "Hello"
        assert ir.find_block("t002") is not None
