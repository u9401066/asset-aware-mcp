"""
Application Layer - DFM ↔ Table Bridge

Bridges DFM table/chart blocks with TableContext (A2T module),
enabling structured editing of docx tables via the existing MCP table tools.

Flow:
  docx → DFM → DfmBlock(TABLE) ──bridge──▶ TableContext ──table_tools──▶ edit
                                                              │
                                                       ◀──bridge──┘ updated DfmBlock
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from src.domain.docx_entities import (
    DfmBlock,
    DocxIR,
)
from src.domain.docx_value_objects import DfmBlockType
from src.domain.table_entities import ColumnDef, TableContext

logger = logging.getLogger(__name__)


class DfmTableBridge:
    """
    Bidirectional bridge between DFM table blocks and TableContext.

    Enables:
    - DfmBlock(TABLE) → TableContext: use MCP table_manage/table_data tools
    - TableContext → DfmBlock(TABLE): write back to docx
    - DfmBlock(CHART) data extraction to TableContext (read-only for now)
    """

    # ========================================================================
    # DfmBlock → TableContext
    # ========================================================================

    @staticmethod
    def block_to_table_context(
        block: DfmBlock,
        doc_id: str = "",
        source_description: str = "",
    ) -> TableContext:
        """
        Convert a DFM table block to a TableContext for structured editing.

        The TableContext can then be manipulated via existing table_manage/table_data
        MCP tools (add/remove rows, add/remove columns, citations, audit trail).

        Args:
            block: A DfmBlock with block_type == TABLE
            doc_id: Document ID for provenance tracking
            source_description: Description of the source document

        Returns:
            TableContext with the table data

        Raises:
            ValueError: If block is not a TABLE type
        """
        if block.block_type != DfmBlockType.TABLE:
            msg = f"Expected TABLE block, got {block.block_type.value}"
            raise ValueError(msg)

        # Parse the markdown table content
        rows_2d = _parse_md_table(block.content)
        if not rows_2d or len(rows_2d) < 1:
            # Empty table — create with no data
            return TableContext(
                id=f"dfm_{block.id}_{uuid.uuid4().hex[:8]}",
                intent="summary",
                title=f"Table {block.id}",
                columns=[],
                rows=[],
                source_description=source_description or f"From docx {doc_id}",
                source_doc_id=doc_id,
                source_block_id=block.id,
            )

        # First row = headers
        headers = rows_2d[0]
        columns = [
            ColumnDef(name=h.strip() or f"col_{i}", type="text")
            for i, h in enumerate(headers)
        ]

        # Remaining rows = data
        data_rows: list[dict[str, Any]] = []
        for row in rows_2d[1:]:
            row_dict: dict[str, Any] = {}
            for i, col in enumerate(columns):
                row_dict[col.name] = row[i] if i < len(row) else ""
            data_rows.append(row_dict)

        # Infer column types from data
        for col in columns:
            _infer_column_type(col, data_rows)

        table_id = f"dfm_{block.id}_{uuid.uuid4().hex[:8]}"
        return TableContext(
            id=table_id,
            intent="summary",
            title=f"Table {block.id}",
            columns=columns,
            rows=data_rows,
            source_description=source_description or f"From docx {doc_id}",
            source_doc_id=doc_id,
            source_block_id=block.id,
        )

    # ========================================================================
    # TableContext → DfmBlock
    # ========================================================================

    @staticmethod
    def table_context_to_block(
        tc: TableContext,
        original_block: DfmBlock | None = None,
        block_id: str | None = None,
    ) -> DfmBlock:
        """
        Convert a TableContext back to a DFM table block.

        If original_block is provided, preserves its metadata (style, col_widths,
        merged_cells, cell_formats) — only updates the text content.

        Args:
            tc: The TableContext with updated data
            original_block: Original DfmBlock to preserve metadata from
            block_id: Block ID to use (defaults to original or auto-generated)

        Returns:
            DfmBlock with updated content and preserved metadata
        """
        # Build markdown table content
        md_content = _table_context_to_md(tc)

        if original_block is not None:
            # Preserve structural metadata from original
            return DfmBlock(
                id=block_id or original_block.id,
                block_type=DfmBlockType.TABLE,
                content=md_content,
                style_name=original_block.style_name,
                table_style=original_block.table_style,
                col_widths=original_block.col_widths,
                merged_cells=original_block.merged_cells,
                cell_formats=original_block.cell_formats,
                is_nested=original_block.is_nested,
                parent_cell=original_block.parent_cell,
                raw_xml_ref=original_block.raw_xml_ref,
            )

        # New block (no original)
        return DfmBlock(
            id=block_id or f"t{uuid.uuid4().hex[:6]}",
            block_type=DfmBlockType.TABLE,
            content=md_content,
        )

    # ========================================================================
    # Apply TableContext back to DocxIR
    # ========================================================================

    @staticmethod
    def apply_table_context_to_ir(
        ir: DocxIR,
        block_id: str,
        tc: TableContext,
    ) -> DocxIR:
        """
        Update a table block in the IR with data from a TableContext.

        Finds the block by ID, replaces its content with the TableContext data,
        while preserving all structural metadata (styles, merge info, etc.).

        Args:
            ir: The DocxIR to update
            block_id: ID of the TABLE block to update
            tc: TableContext with new data

        Returns:
            Updated DocxIR (same object, mutated)

        Raises:
            ValueError: If block not found or not a TABLE
        """
        block = ir.find_block(block_id)
        if block is None:
            msg = f"Block not found: {block_id}"
            raise ValueError(msg)
        if block.block_type != DfmBlockType.TABLE:
            msg = f"Block {block_id} is {block.block_type.value}, not TABLE"
            raise ValueError(msg)

        # Update content only — preserve metadata
        block.content = _table_context_to_md(tc)
        return ir

    # ========================================================================
    # Chart Data Extraction (read-only)
    # ========================================================================

    @staticmethod
    def extract_chart_data(
        block: DfmBlock,
        chart_xml: str | None = None,
    ) -> TableContext | None:
        """
        Extract tabular data from a chart block.

        If chart_xml is provided, parse the c:chart XML for series data.
        Otherwise, return a placeholder TableContext based on metadata.

        Args:
            block: A DfmBlock with block_type == CHART
            chart_xml: Optional raw chart XML content

        Returns:
            TableContext with chart data, or None if extraction fails
        """
        if block.block_type != DfmBlockType.CHART:
            return None

        if chart_xml:
            return _parse_chart_xml_to_table(block, chart_xml)

        # No XML available — return metadata-only context
        return TableContext(
            id=f"chart_{block.id}",
            intent="summary",
            title=f"Chart {block.id} ({block.chart_type or 'unknown'})",
            columns=[
                ColumnDef(name="property", type="text"),
                ColumnDef(name="value", type="text"),
            ],
            rows=[
                {"property": "chart_type", "value": block.chart_type or "unknown"},
                {"property": "width_cm", "value": str(block.image_width_cm or "")},
                {"property": "height_cm", "value": str(block.image_height_cm or "")},
                {"property": "binary_ref", "value": block.binary_ref or ""},
                {"property": "data_hash", "value": block.data_hash or ""},
            ],
            source_description=f"Metadata from chart block {block.id}",
        )

    # ========================================================================
    # Batch operations
    # ========================================================================

    @staticmethod
    def extract_all_tables(ir: DocxIR) -> dict[str, TableContext]:
        """
        Extract all TABLE blocks from an IR as TableContext objects.

        Returns:
            Dict mapping block_id → TableContext
        """
        result: dict[str, TableContext] = {}
        for block in ir.get_blocks_by_type(DfmBlockType.TABLE):
            try:
                tc = DfmTableBridge.block_to_table_context(
                    block,
                    doc_id=ir.doc_id,
                    source_description=f"Table from {ir.source_filename}",
                )
                result[block.id] = tc
            except Exception:  # PIL/lxml may raise various errors
                logger.warning("Failed to convert table block %s", block.id)
        return result


# ============================================================================
# Private helpers
# ============================================================================


def _parse_md_table(text: str) -> list[list[str]] | None:
    """Parse a markdown table into a 2D list of cell texts."""
    import re

    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    if not lines:
        return None

    rows: list[list[str]] = []
    for line in lines:
        # Skip separator rows (|---|---|)
        if re.match(r"^\|[\s\-:|]+\|$", line):
            continue
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        cells = [c.strip() for c in cells[1:-1]]
        # Restore escaped newlines
        cells = [c.replace("<br>", "\n") for c in cells]
        rows.append(cells)
    return rows if rows else None


def _table_context_to_md(tc: TableContext) -> str:
    """Convert a TableContext to a markdown table string."""
    if not tc.columns:
        return ""

    col_names = tc.column_names
    lines: list[str] = []

    # Header
    lines.append("| " + " | ".join(col_names) + " |")
    # Separator
    lines.append("| " + " | ".join("---" for _ in col_names) + " |")
    # Data rows
    for row in tc.rows:
        cells = [str(row.get(c, "")) for c in col_names]
        # Escape pipe characters and newlines in cell content
        cells = [c.replace("|", "\\|").replace("\n", "<br>") for c in cells]
        lines.append("| " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _infer_column_type(col: ColumnDef, rows: list[dict[str, Any]]) -> None:
    """Infer column type from data values (mutates col.type in place)."""
    values = [r.get(col.name, "") for r in rows if r.get(col.name, "")]
    if not values:
        return

    # Check if all non-empty values are numeric
    numeric_count = 0
    for v in values:
        try:
            float(str(v).replace(",", ""))
            numeric_count += 1
        except ValueError:
            pass

    if numeric_count == len(values):
        col.type = "number"


def _parse_chart_xml_to_table(
    block: DfmBlock,
    chart_xml: str,
) -> TableContext | None:
    """
    Parse Office Open XML chart data into a TableContext.

    Handles:
    - c:barChart / c:lineChart / c:pieChart series
    - c:numRef / c:strRef data references

    Args:
        block: The chart DfmBlock
        chart_xml: Raw chart XML content

    Returns:
        TableContext with extracted data, or None on failure
    """
    try:
        from lxml import etree
    except ImportError:
        logger.warning("lxml not available for chart XML parsing")
        return None

    try:
        root = etree.fromstring(chart_xml.encode("utf-8"))  # trusted internal XML
    except etree.XMLSyntaxError:
        logger.warning("Invalid chart XML for block %s", block.id)
        return None

    # Chart namespaces
    ns = {
        "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    }

    # Find chart type and series
    chart_types = ["barChart", "lineChart", "pieChart", "areaChart", "scatterChart"]
    series_elements = []
    detected_type = block.chart_type or "unknown"

    for ct in chart_types:
        chart_elem = root.find(f".//c:{ct}", ns)
        if chart_elem is not None:
            detected_type = ct.replace("Chart", "")
            series_elements = chart_elem.findall("c:ser", ns)
            break

    if not series_elements:
        return None

    # Extract category labels (from first series)
    categories: list[str] = []
    first_cat = series_elements[0].find(".//c:cat", ns)
    if first_cat is not None:
        str_ref = first_cat.find("c:strRef/c:strCache", ns)
        if str_ref is not None:
            for pt in str_ref.findall("c:pt", ns):
                v = pt.find("c:v", ns)
                categories.append(v.text if v is not None and v.text else "")

    # Extract each series
    series_names: list[str] = []
    series_data: list[list[str]] = []

    for ser in series_elements:
        # Series name
        tx = ser.find("c:tx/c:strRef/c:strCache/c:pt/c:v", ns)
        name = (
            tx.text if tx is not None and tx.text else f"Series {len(series_names) + 1}"
        )
        series_names.append(name)

        # Series values
        values: list[str] = []
        val_elem = ser.find("c:val", ns)
        if val_elem is None:
            val_elem = ser.find("c:yVal", ns)
        if val_elem is not None:
            num_ref = val_elem.find("c:numRef/c:numCache", ns)
            if num_ref is not None:
                for pt in num_ref.findall("c:pt", ns):
                    v = pt.find("c:v", ns)
                    values.append(v.text if v is not None and v.text else "")
        series_data.append(values)

    if not series_names:
        return None

    # Build TableContext: categories as first column, then each series
    columns = [ColumnDef(name="Category", type="text")]
    for sn in series_names:
        columns.append(ColumnDef(name=sn, type="number"))

    # Ensure categories list matches data
    max_len = max(len(categories), *(len(sd) for sd in series_data))
    while len(categories) < max_len:
        categories.append(f"Item {len(categories) + 1}")

    rows: list[dict[str, Any]] = []
    for i in range(max_len):
        row: dict[str, Any] = {"Category": categories[i] if i < len(categories) else ""}
        for j, sn in enumerate(series_names):
            val = series_data[j][i] if i < len(series_data[j]) else ""
            # Convert to float if possible
            try:
                row[sn] = float(val) if val else ""
            except ValueError:
                row[sn] = val
        rows.append(row)

    return TableContext(
        id=f"chart_{block.id}",
        intent="summary",
        title=f"Chart Data: {block.content or detected_type}",
        columns=columns,
        rows=rows,
        source_description=f"Extracted from {detected_type} chart block {block.id}",
    )
