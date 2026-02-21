"""
Infrastructure Layer - DFM Renderer

Converts DocxIR → DFM (Docx-Flavored Markdown) text format.
Produces a human-readable, editable file with YAML metadata blocks
for elements that cannot be represented in standard Markdown.
"""

from __future__ import annotations

from typing import Any

import yaml

from src.domain.docx_entities import (
    DfmBlock,
    DocxIR,
    FormatRun,
)
from src.domain.docx_value_objects import DfmBlockType, ImageAnchorType


class DfmRenderer:
    """Renders DocxIR into DFM text format."""

    def render(self, ir: DocxIR) -> str:
        """
        Render the complete DocxIR as a DFM string.

        Returns:
            DFM text ready to be written to content.dfm
        """
        lines: list[str] = []

        # 1. YAML frontmatter
        lines.append(self._render_frontmatter(ir))
        lines.append("")

        # 2. Styles block
        lines.append(self._render_styles(ir))
        lines.append("")

        # 3. Content blocks
        for block in ir.blocks:
            rendered = self._render_block(block)
            if rendered is not None:
                lines.append(rendered)
                lines.append("")  # Blank line between blocks

        return "\n".join(lines)

    # ========================================================================
    # Frontmatter
    # ========================================================================

    def _render_frontmatter(self, ir: DocxIR) -> str:
        """Render YAML frontmatter."""
        fm = {
            "dfm_version": "1.0",
            "source": ir.source_filename,
            "doc_id": ir.doc_id,
            "created": ir.created_at.isoformat(),
            "checksum": ir.checksum,
        }
        yaml_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
        return f"---\n{yaml_str}\n---"

    # ========================================================================
    # Styles
    # ========================================================================

    def _render_styles(self, ir: DocxIR) -> str:
        """Render document-level style information."""
        style_data = ir.style_info.to_dict()
        yaml_str = yaml.dump(
            style_data, default_flow_style=False, allow_unicode=True
        ).strip()
        return f"<!-- dfm:styles\n{yaml_str}\n-->"

    # ========================================================================
    # Block dispatch
    # ========================================================================

    def _render_block(self, block: DfmBlock) -> str | None:
        """Render a single block to DFM text."""
        renderers = {
            DfmBlockType.PARAGRAPH: self._render_paragraph,
            DfmBlockType.HEADING: self._render_heading,
            DfmBlockType.LIST_ITEM: self._render_list_item,
            DfmBlockType.FORMAT: self._render_format,
            DfmBlockType.TABLE: self._render_table,
            DfmBlockType.IMAGE: self._render_image,
            DfmBlockType.CAPTION: self._render_caption,
            DfmBlockType.CHART: self._render_chart,
            DfmBlockType.TOC: self._render_toc,
            DfmBlockType.HEADER: self._render_header,
            DfmBlockType.FOOTER: self._render_footer,
            DfmBlockType.FIELD: self._render_field,
            DfmBlockType.BREAK: self._render_break,
            DfmBlockType.FOOTNOTE: self._render_footnote,
            DfmBlockType.CITATION: self._render_citation,
            DfmBlockType.MACRO: self._render_macro,
            DfmBlockType.OLE: self._render_ole,
            DfmBlockType.BOOKMARK: self._render_bookmark,
            DfmBlockType.REVISION: self._render_revision,
        }
        renderer = renderers.get(block.block_type)
        if renderer:
            return renderer(block)
        return None

    # ========================================================================
    # Editable blocks
    # ========================================================================

    def _render_paragraph(self, block: DfmBlock) -> str:
        """Render a simple paragraph."""
        style_attr = f" s:{block.style_name}" if block.style_name else ""
        header = f"<!-- @b:{block.id}{style_attr} -->"

        # Convert runs to Markdown formatting
        md_text = self._runs_to_md(block.runs) if block.runs else block.content
        return f"{header}\n{md_text}"

    def _render_heading(self, block: DfmBlock) -> str:
        """Render a heading."""
        style_attr = f" s:{block.style_name}" if block.style_name else ""
        header = f"<!-- @b:{block.id}{style_attr} -->"
        prefix = "#" * min(block.level, 6)
        return f"{header}\n{prefix} {block.content}"

    def _render_list_item(self, block: DfmBlock) -> str:
        """Render a list item."""
        attrs = [f"@b:{block.id}"]
        if block.style_name:
            attrs.append(f"s:{block.style_name}")
        if block.list_level > 0:
            attrs.append(f"level:{block.list_level}")
        if block.num_id is not None:
            attrs.append(f"numId:{block.num_id}")
        header = f"<!-- {' '.join(attrs)} -->"

        indent = "  " * block.list_level
        # Determine bullet vs numbered
        if block.style_name and "number" in block.style_name.lower():
            marker = "1."
        else:
            marker = "-"

        md_text = self._runs_to_md(block.runs) if block.runs else block.content
        return f"{header}\n{indent}{marker} {md_text}"

    def _render_format(self, block: DfmBlock) -> str:
        """Render a mixed-format paragraph with YAML runs metadata."""
        runs_data = [r.to_dict() for r in block.runs]
        yaml_str = yaml.dump(
            {"runs": runs_data},
            default_flow_style=False,
            allow_unicode=True,
        ).strip()

        header = f"<!-- dfm:format @b:{block.id}"
        if block.style_name:
            header += f" s:{block.style_name}"
        header += f"\n{yaml_str}\n-->"

        # Fallback editable text
        fallback = self._runs_to_md(block.runs) if block.runs else block.content
        return f"{header}\n{fallback}\n<!-- /dfm:format -->"

    def _render_caption(self, block: DfmBlock) -> str:
        """Render a caption."""
        style_attr = f" s:{block.style_name}" if block.style_name else ""
        header = f"<!-- @b:{block.id}{style_attr} -->"
        return f"{header}\n*{block.content}*"

    # ========================================================================
    # Table
    # ========================================================================

    def _render_table(self, block: DfmBlock) -> str:
        """Render a table with YAML metadata."""
        parts: list[str] = []

        # Build YAML metadata
        meta: dict[str, Any] = {}
        if block.table_style:
            meta["style"] = block.table_style
        if block.col_widths:
            meta["col_widths"] = block.col_widths
        if block.merged_cells:
            meta["merged_cells"] = [mc.to_dict() for mc in block.merged_cells]
        if block.cell_formats:
            meta["cell_formats"] = {
                k: v.to_dict() for k, v in block.cell_formats.items()
            }
        if block.is_nested:
            meta["nested"] = True
        if block.parent_cell:
            meta["parent_cell"] = block.parent_cell
        if block.raw_xml_ref:
            meta["raw_xml_ref"] = block.raw_xml_ref

        header = f"<!-- dfm:table @b:{block.id}"
        if meta:
            yaml_str = yaml.dump(
                meta, default_flow_style=False, allow_unicode=True
            ).strip()
            header += f"\n{yaml_str}"
        header += "\n-->"
        parts.append(header)

        # Warning for merged cells
        if block.merged_cells:
            parts.append("<!-- ⚠️ 此表格有合併儲存格，結構保護，僅文字可編輯 -->")

        # Table content (markdown)
        parts.append(block.content)

        parts.append("<!-- /dfm:table -->")
        return "\n".join(parts)

    # ========================================================================
    # Image
    # ========================================================================

    def _render_image(self, block: DfmBlock) -> str:
        """Render an image block."""
        meta: dict[str, Any] = {}
        if block.image_path:
            meta["path"] = block.image_path
        if block.image_width_cm:
            meta["width_cm"] = block.image_width_cm
        if block.image_height_cm:
            meta["height_cm"] = block.image_height_cm
        if block.image_anchor != ImageAnchorType.INLINE:
            meta["anchor"] = block.image_anchor.value
        if block.image_alt:
            meta["alt"] = block.image_alt

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        header = f"<!-- dfm:image @b:{block.id}\n{yaml_str}\n-->"
        alt = block.image_alt or block.content
        path = block.image_path or ""
        return f"{header}\n![{alt}]({path})\n<!-- /dfm:image -->"

    # ========================================================================
    # Protected blocks
    # ========================================================================

    def _render_chart(self, block: DfmBlock) -> str:
        """Render an embedded chart (protected)."""
        meta: dict[str, Any] = {
            "type": "embedded_excel",
        }
        if block.chart_type:
            meta["chart_type"] = block.chart_type
        if block.data_hash:
            meta["data_hash"] = block.data_hash
        if block.binary_ref:
            meta["binary_ref"] = block.binary_ref
        if block.image_width_cm:
            meta["width_cm"] = block.image_width_cm
        if block.image_height_cm:
            meta["height_cm"] = block.image_height_cm

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        caption = block.content or "Embedded Chart"
        return (
            f"<!-- dfm:chart @b:{block.id}\n{yaml_str}\n-->\n"
            f"📊 *[嵌入圖表：{caption}]*\n"
            f"*此圖表為嵌入式 Excel 圖表，請用 Word 編輯。*\n"
            f"<!-- /dfm:chart -->"
        )

    def _render_toc(self, block: DfmBlock) -> str:
        """Render a table of contents (protected)."""
        meta: dict[str, Any] = {}
        if block.toc_depth:
            meta["depth"] = block.toc_depth
        if block.field_code:
            meta["field_code"] = block.field_code
        if block.xml_ref:
            meta["raw_xml_ref"] = block.xml_ref

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        return (
            f"<!-- dfm:toc @b:{block.id}\n{yaml_str}\n-->\n"
            f"🔖 *[目錄 — 自動產生，請勿編輯]*\n"
            f"<!-- /dfm:toc -->"
        )

    def _render_header(self, block: DfmBlock) -> str:
        """Render a page header (protected)."""
        meta: dict[str, Any] = {}
        if block.hdr_ftr_type:
            meta["type"] = block.hdr_ftr_type
        if block.xml_ref:
            meta["xml_ref"] = block.xml_ref
        if block.preview_text:
            meta["preview"] = block.preview_text

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        return f"<!-- dfm:header @b:{block.id}\n{yaml_str}\n-->"

    def _render_footer(self, block: DfmBlock) -> str:
        """Render a page footer (protected)."""
        meta: dict[str, Any] = {}
        if block.hdr_ftr_type:
            meta["type"] = block.hdr_ftr_type
        if block.xml_ref:
            meta["xml_ref"] = block.xml_ref
        if block.preview_text:
            meta["preview"] = block.preview_text

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        return f"<!-- dfm:footer @b:{block.id}\n{yaml_str}\n-->"

    def _render_field(self, block: DfmBlock) -> str:
        """Render a field code (protected)."""
        meta: dict[str, Any] = {}
        if block.field_type:
            meta["type"] = block.field_type
        if block.field_instruction:
            meta["instruction"] = block.field_instruction
        if block.field_display:
            meta["display"] = block.field_display

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        return f"<!-- dfm:field @b:{block.id}\n{yaml_str}\n-->"

    def _render_break(self, block: DfmBlock) -> str:
        """Render a page/section break."""
        attrs = [f"@b:{block.id}"]
        if block.break_type:
            attrs.append(f"type:{block.break_type.value}")

        header = f"<!-- dfm:break {' '.join(attrs)}"

        if block.section_page_setup:
            meta = {"page_setup": block.section_page_setup.to_dict()}
            yaml_str = yaml.dump(
                meta, default_flow_style=False, allow_unicode=True
            ).strip()
            header += f"\n{yaml_str}"

        header += " -->"
        return header

    def _render_footnote(self, block: DfmBlock) -> str:
        """Render a footnote."""
        fn_id = block.footnote_id or 0
        header = f"<!-- dfm:footnote @b:{block.id}\nid: {fn_id}\n-->"
        return f"{header}\n[^{fn_id}]: {block.content}\n<!-- /dfm:footnote -->"

    def _render_citation(self, block: DfmBlock) -> str:
        """Render a bibliography citation."""
        meta: dict[str, Any] = {}
        if block.citation_style:
            meta["style"] = block.citation_style
        if block.citation_entries:
            meta["entries"] = block.citation_entries

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        return (
            f"<!-- dfm:citation @b:{block.id}\n{yaml_str}\n-->\n"
            f"{block.content}\n"
            f"<!-- /dfm:citation -->"
        )

    def _render_macro(self, block: DfmBlock) -> str:
        """Render a VBA macro (protected)."""
        meta: dict[str, Any] = {}
        if block.macro_name:
            meta["name"] = block.macro_name
        if block.binary_ref:
            meta["binary_ref"] = block.binary_ref
        if block.macro_hash:
            meta["hash"] = block.macro_hash

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        name = block.macro_name or "VBA Macro"
        return (
            f"<!-- dfm:macro @b:{block.id}\n{yaml_str}\n-->\n"
            f"🔧 *[VBA 巨集：{name} — 二進位保護，請用 Word 編輯]*\n"
            f"<!-- /dfm:macro -->"
        )

    def _render_ole(self, block: DfmBlock) -> str:
        """Render an OLE embedded object (protected)."""
        meta: dict[str, Any] = {}
        if block.ole_prog_id:
            meta["prog_id"] = block.ole_prog_id
        if block.binary_ref:
            meta["binary_ref"] = block.binary_ref
        if block.ole_display_name:
            meta["display_name"] = block.ole_display_name
        if block.ole_width_cm:
            meta["width_cm"] = block.ole_width_cm
        if block.ole_height_cm:
            meta["height_cm"] = block.ole_height_cm

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        display = block.ole_display_name or "Embedded Object"
        prog = block.ole_prog_id or "Unknown"
        return (
            f"<!-- dfm:ole @b:{block.id}\n{yaml_str}\n-->\n"
            f"📎 *[嵌入物件：{display} ({prog})]*\n"
            f"<!-- /dfm:ole -->"
        )

    def _render_bookmark(self, block: DfmBlock) -> str:
        """Render a bookmark anchor."""
        name = block.bookmark_name or ""
        return f'<!-- dfm:bookmark @b:{block.id} name:"{name}" -->'

    def _render_revision(self, block: DfmBlock) -> str:
        """Render a tracked change revision."""
        meta: dict[str, Any] = {}
        if block.revision_type:
            meta["type"] = block.revision_type
        if block.revision_author:
            meta["author"] = block.revision_author
        if block.revision_date:
            meta["date"] = block.revision_date

        yaml_str = yaml.dump(meta, default_flow_style=False, allow_unicode=True).strip()

        return (
            f"<!-- dfm:revision @b:{block.id}\n{yaml_str}\n-->\n"
            f"{block.content}\n"
            f"<!-- /dfm:revision -->"
        )

    # ========================================================================
    # Helpers
    # ========================================================================

    @staticmethod
    def _runs_to_md(runs: list[FormatRun]) -> str:
        """Convert format runs to Markdown-formatted text."""
        parts = []
        for run in runs:
            text = run.text
            if not text:
                continue
            if run.bold and run.italic:
                text = f"***{text}***"
            elif run.bold:
                text = f"**{text}**"
            elif run.italic:
                text = f"*{text}*"
            if run.strike:
                text = f"~~{text}~~"
            if run.superscript:
                text = f"^{text}^"
            if run.subscript:
                text = f"~{text}~"
            parts.append(text)
        return "".join(parts)
