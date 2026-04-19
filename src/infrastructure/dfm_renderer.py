"""
Infrastructure Layer - DFM Renderer

Converts DocxIR → DFM (Docx-Flavored Markdown) text format.
Produces a human-readable, editable file with YAML metadata blocks
for elements that cannot be represented in standard Markdown.
"""

from __future__ import annotations

import logging
from typing import Any

import yaml

from src.domain.docx_entities import (  # noqa: TC001
    DfmBlock,
    DocxIR,
    FormatRun,
)
from src.domain.docx_value_objects import DfmBlockType, ImageAnchorType

logger = logging.getLogger(__name__)


class DfmRenderer:
    """Renders DocxIR into DFM text format."""

    # ========================================================================
    # Split format: content.md + format.yaml
    # ========================================================================

    def render_split(self, ir: DocxIR) -> tuple[str, str]:
        """
        Render DocxIR as a clean Markdown file + a YAML sidecar.

        Returns:
            (md_content, yaml_content) — the .md is human-editable,
            the .yaml holds all formatting metadata.
        """
        md_lines: list[str] = []
        block_meta: dict[str, dict[str, Any]] = {}

        # --- Frontmatter (minimal, in .md) ---
        fm = {
            "dfm_version": "1.0",
            "format_file": "format.yaml",
            "doc_id": ir.doc_id,
        }
        fm_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True).strip()
        md_lines.append(f"---\n{fm_yaml}\n---")
        md_lines.append("")

        # --- Content blocks ---
        for block in ir.blocks:
            md_part = self._render_block_md(block)
            if md_part is not None:
                md_lines.append(md_part)
                md_lines.append("")

            meta = self._render_block_meta(block)
            if meta is not None:
                block_meta[block.id] = meta

        # --- Build format.yaml ---
        format_data: dict[str, Any] = {
            "dfm_version": "1.0",
            "doc_id": ir.doc_id,
            "source": ir.source_filename,
            "checksum": ir.checksum,
            "created": ir.created_at.isoformat(),
            "styles": ir.style_info.to_dict(),
            "blocks": block_meta,
        }
        yaml_content = yaml.dump(
            format_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        return "\n".join(md_lines), yaml_content

    def _render_block_md(self, block: DfmBlock) -> str | None:
        """Render a block as clean Markdown (no YAML blobs)."""
        bt = block.block_type
        marker = f"<!-- @{block.id} -->"

        if bt == DfmBlockType.PARAGRAPH:
            md_text = self._runs_to_md(block.runs) if block.runs else block.content
            return f"{marker}\n{md_text}"

        if bt == DfmBlockType.HEADING:
            prefix = "#" * min(block.level, 6)
            return f"{marker}\n{prefix} {block.content}"

        if bt == DfmBlockType.LIST_ITEM:
            indent = "  " * block.list_level
            marker_char = (
                "1."
                if block.style_name and "number" in block.style_name.lower()
                else "-"
            )
            md_text = self._runs_to_md(block.runs) if block.runs else block.content
            return f"{marker}\n{indent}{marker_char} {md_text}"

        if bt == DfmBlockType.FORMAT:
            md_text = self._runs_to_md(block.runs) if block.runs else block.content
            return f"{marker}\n{md_text}"

        if bt == DfmBlockType.TABLE:
            return f"{marker}\n{block.content}"

        if bt == DfmBlockType.CAPTION:
            return f"{marker}\n*{block.content}*"

        if bt == DfmBlockType.IMAGE:
            alt = block.image_alt or block.content
            path = block.image_path or ""
            return f"{marker}\n![{alt}]({path})"

        if bt == DfmBlockType.BREAK:
            return f"{marker}\n\n---"

        if bt == DfmBlockType.FOOTNOTE:
            fn_id = block.footnote_id or 0
            return f"{marker}\n[^{fn_id}]: {block.content}"

        if bt == DfmBlockType.CITATION:
            return f"{marker}\n{block.content}"

        if bt == DfmBlockType.REVISION:
            return f"{marker}\n{block.content}"

        # Protected blocks → placeholder
        if bt == DfmBlockType.CHART:
            caption = block.content or "Embedded Chart"
            return f"{marker}\n> 📊 *[嵌入圖表：{caption}]*"

        if bt == DfmBlockType.TOC:
            return f"{marker}\n> 🔖 *[目錄 — 自動產生]*"

        if bt == DfmBlockType.MACRO:
            name = block.macro_name or "VBA Macro"
            return f"{marker}\n> 🔧 *[VBA 巨集：{name}]*"

        if bt == DfmBlockType.OLE:
            display = block.ole_display_name or "Embedded Object"
            return f"{marker}\n> 📎 *[嵌入物件：{display}]*"

        if bt in (DfmBlockType.HEADER, DfmBlockType.FOOTER):
            kind = "頁首" if bt == DfmBlockType.HEADER else "頁尾"
            preview = block.preview_text or ""
            return f"{marker}\n> 📄 *[{kind}：{preview}]*"

        if bt == DfmBlockType.FIELD:
            return f"{marker}\n> *[欄位：{block.field_type or ''}]*"

        if bt == DfmBlockType.BOOKMARK:
            return None  # Invisible in clean MD

        return None

    def _render_block_meta(self, block: DfmBlock) -> dict[str, Any] | None:
        """Extract formatting metadata for format.yaml."""
        bt = block.block_type
        meta: dict[str, Any] = {"type": bt.value}

        if block.style_name:
            meta["style"] = block.style_name

        if bt == DfmBlockType.PARAGRAPH:
            if not block.style_name and not block.runs:
                return meta  # Minimal
            if block.runs:
                meta["runs"] = [r.to_dict() for r in block.runs]
            return meta

        if bt == DfmBlockType.HEADING:
            meta["level"] = block.level
            return meta

        if bt == DfmBlockType.LIST_ITEM:
            meta["list_level"] = block.list_level
            if block.num_id is not None:
                meta["num_id"] = block.num_id
            return meta

        if bt == DfmBlockType.FORMAT:
            if block.runs:
                meta["runs"] = [r.to_dict() for r in block.runs]
            return meta

        if bt == DfmBlockType.TABLE:
            if block.table_style:
                meta["table_style"] = block.table_style
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
            if block.metadata.get("parent_table_id"):
                meta["parent_table_id"] = block.metadata["parent_table_id"]
            if block.metadata.get("contains_nested_tables"):
                meta["contains_nested_tables"] = True
            return meta

        if bt == DfmBlockType.IMAGE:
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
            return meta

        if bt == DfmBlockType.CAPTION:
            return meta

        if bt == DfmBlockType.BREAK:
            if block.break_type:
                meta["break_type"] = block.break_type.value
            if block.section_page_setup:
                meta["section_page_setup"] = block.section_page_setup.to_dict()
            return meta

        if bt == DfmBlockType.FOOTNOTE:
            meta["footnote_id"] = block.footnote_id
            return meta

        if bt == DfmBlockType.CITATION:
            if block.citation_style:
                meta["citation_style"] = block.citation_style
            if block.citation_entries:
                meta["citation_entries"] = block.citation_entries
            return meta

        if bt == DfmBlockType.CHART:
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
            return meta

        if bt in (DfmBlockType.HEADER, DfmBlockType.FOOTER):
            if block.hdr_ftr_type:
                meta["hdr_ftr_type"] = block.hdr_ftr_type
            if block.xml_ref:
                meta["xml_ref"] = block.xml_ref
            if block.preview_text:
                meta["preview"] = block.preview_text
            return meta

        if bt == DfmBlockType.TOC:
            if block.toc_depth:
                meta["depth"] = block.toc_depth
            if block.field_code:
                meta["field_code"] = block.field_code
            if block.xml_ref:
                meta["raw_xml_ref"] = block.xml_ref
            return meta

        if bt == DfmBlockType.FIELD:
            if block.field_type:
                meta["field_type"] = block.field_type
            if block.field_instruction:
                meta["field_instruction"] = block.field_instruction
            if block.field_display:
                meta["field_display"] = block.field_display
            return meta

        if bt == DfmBlockType.MACRO:
            if block.macro_name:
                meta["name"] = block.macro_name
            if block.binary_ref:
                meta["binary_ref"] = block.binary_ref
            if block.macro_hash:
                meta["hash"] = block.macro_hash
            return meta

        if bt == DfmBlockType.OLE:
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
            return meta

        if bt == DfmBlockType.BOOKMARK:
            if block.bookmark_name:
                meta["name"] = block.bookmark_name
            return meta

        if bt == DfmBlockType.REVISION:
            if block.revision_type:
                meta["revision_type"] = block.revision_type
            if block.revision_author:
                meta["revision_author"] = block.revision_author
            if block.revision_date:
                meta["revision_date"] = block.revision_date
            return meta

        return meta

    # ========================================================================
    # Original DFM format (single file)
    # ========================================================================

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
    def _escape_md(text: str) -> str:
        """Escape Markdown-special characters so they survive round-trip."""
        # Backslash must be first to avoid double-escaping
        text = text.replace("\\", "\\\\")
        text = text.replace("*", "\\*")
        text = text.replace("~", "\\~")
        text = text.replace("^", "\\^")
        return text

    @staticmethod
    def _runs_to_md(runs: list[FormatRun]) -> str:
        """Convert format runs to Markdown-formatted text.

        Merges adjacent runs with identical formatting to produce
        cleaner Markdown (e.g. ``**AB**`` instead of ``**A****B**``).
        """
        if not runs:
            return ""

        # Group consecutive runs by formatting key
        groups: list[tuple[tuple, list[str]]] = []
        for run in runs:
            if not run.text:
                continue
            key = (run.bold, run.italic, run.strike, run.superscript, run.subscript)
            if groups and groups[-1][0] == key:
                groups[-1][1].append(run.text)
            else:
                groups.append((key, [run.text]))

        parts = []
        for (bold, italic, strike, superscript, subscript), texts in groups:
            text = DfmRenderer._escape_md("".join(texts))
            if bold and italic:
                text = f"***{text}***"
            elif bold:
                text = f"**{text}**"
            elif italic:
                text = f"*{text}*"
            if strike:
                text = f"~~{text}~~"
            if superscript:
                text = f"^{text}^"
            if subscript:
                text = f"~{text}~"
            parts.append(text)
        return "".join(parts)
