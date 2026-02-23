"""
Infrastructure Layer - Docx Adapter

Parses .docx files into DocxIR (Intermediate Representation) and
rebuilds .docx from modified IR. Uses python-docx and lxml for
direct Open XML manipulation.
"""

from __future__ import annotations

import hashlib
import logging
import re
import shutil
from pathlib import Path
from zipfile import ZipFile

from lxml import etree

from src.domain.docx_entities import (
    CellFormat,
    DfmBlock,
    DocxIR,
    DocxStyleInfo,
    FormatRun,
    MergedCell,
    PageSetup,
)
from src.domain.docx_value_objects import (
    BreakType,
    DfmBlockType,
    ImageAnchorType,
    TableCellAlign,
)

logger = logging.getLogger(__name__)

# ============================================================================
# Open XML Namespaces
# ============================================================================

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

# EMU to cm conversion (1 cm = 360000 EMU)
EMU_PER_CM = 360000
# Twips to cm conversion (1 cm = 567 twips)
TWIPS_PER_CM = 567
# Half-points to pt (font size in half-points)
HALF_POINTS_TO_PT = 0.5


def _emu_to_cm(emu: int) -> float:
    """Convert EMU (English Metric Units) to centimeters."""
    return round(emu / EMU_PER_CM, 2)


def _cm_to_emu(cm: float) -> int:
    """Convert centimeters to EMU."""
    return int(cm * EMU_PER_CM)


def _twips_to_cm(twips: int) -> float:
    """Convert twips to centimeters."""
    return round(twips / TWIPS_PER_CM, 2)


def _half_pt_to_pt(half_pt: int) -> float:
    """Convert half-points to points."""
    return half_pt * HALF_POINTS_TO_PT


class DocxAdapter:
    """
    Bidirectional converter between .docx files and DocxIR.

    docx → IR: parse_to_ir()
    IR → docx: ir_to_docx()
    """

    def parse_to_ir(self, docx_path: Path, output_dir: Path) -> DocxIR:
        """
        Parse a .docx file into a DocxIR intermediate representation.

        Extracts all content blocks, preserves formatting metadata,
        saves binary assets and XML parts to output_dir.

        Args:
            docx_path: Path to the .docx file
            output_dir: Directory to store assets, parts, and original backup

        Returns:
            DocxIR with all blocks and metadata
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        parts_dir = output_dir / "parts"
        parts_dir.mkdir(exist_ok=True)

        # Compute checksum
        checksum = self._compute_checksum(docx_path)

        # Copy original for backup
        original_backup = output_dir / "original.docx"
        if not original_backup.exists():
            shutil.copy2(docx_path, original_backup)

        # Generate doc_id
        stem = re.sub(r"[^a-z0-9]", "_", docx_path.stem.lower())[:30]
        hash_suffix = hashlib.sha256(str(docx_path.absolute()).encode()).hexdigest()[:6]
        doc_id = f"docx_{stem}_{hash_suffix}"

        ir = DocxIR(
            doc_id=doc_id,
            source_path=str(docx_path),
            source_filename=docx_path.name,
            checksum=checksum,
        )

        with ZipFile(docx_path, "r") as zf:
            # 1. Preserve XML parts
            self._preserve_xml_parts(zf, parts_dir, ir)

            # 2. Extract media assets
            self._extract_media(zf, assets_dir, ir)

            # 3. Parse relationships
            rels = self._parse_relationships(zf)

            # 4. Parse document styles/page setup
            ir.style_info = self._parse_styles(zf)

            # 5. Parse document body → blocks
            doc_xml = zf.read("word/document.xml")
            tree = etree.fromstring(doc_xml)  # noqa: S320 - parse OOXML from local .docx package
            body = tree.find(f".//{{{NS['w']}}}body")
            if body is not None:
                self._parse_body(body, ir, rels, assets_dir, parts_dir)

            # 6. Parse footnotes
            self._parse_footnotes(zf, ir)

            # 7. Parse headers/footers
            self._parse_headers_footers(zf, ir, parts_dir)

        return ir

    def ir_to_docx(self, ir: DocxIR, data_dir: Path, output_path: Path) -> Path:
        """
        Rebuild a .docx file from a DocxIR.

        Uses the original.docx as base and replaces text content
        according to the modified IR blocks.

        Args:
            ir: The (possibly modified) intermediate representation
            data_dir: Directory containing original.docx, parts/, assets/
            output_path: Where to write the output .docx

        Returns:
            Path to the generated .docx file
        """
        original = data_dir / "original.docx"
        if not original.exists():
            raise FileNotFoundError(f"Original docx not found: {original}")

        # Copy original as base
        shutil.copy2(original, output_path)

        # Build block ID → new content mapping
        content_map = {}
        for block in ir.blocks:
            content_map[block.id] = block

        # Modify document.xml in-place within the zip
        self._update_document_xml(output_path, ir)

        return output_path

    # ========================================================================
    # Private: Parsing helpers
    # ========================================================================

    @staticmethod
    def _compute_checksum(path: Path) -> str:
        """Compute SHA-256 checksum of a file."""
        sha = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha.update(chunk)
        return f"sha256:{sha.hexdigest()}"

    def _preserve_xml_parts(self, zf: ZipFile, parts_dir: Path, ir: DocxIR) -> None:
        """Save non-content XML parts for round-trip preservation."""
        preserve_list = [
            "word/styles.xml",
            "word/numbering.xml",
            "word/settings.xml",
            "word/theme/theme1.xml",
            "word/fontTable.xml",
            "word/webSettings.xml",
            "[Content_Types].xml",
        ]
        for part_name in preserve_list:
            if part_name in zf.namelist():
                data = zf.read(part_name)
                safe_name = (
                    part_name.replace("/", "_").replace("[", "").replace("]", "")
                )
                out_path = parts_dir / safe_name
                out_path.write_bytes(data)
                ir.preserved_parts[part_name] = f"parts/{safe_name}"

    def _extract_media(self, zf: ZipFile, assets_dir: Path, ir: DocxIR) -> None:
        """Extract all media files (images, etc.) from the docx."""
        for name in zf.namelist():
            if name.startswith("word/media/"):
                data = zf.read(name)
                filename = Path(name).name
                out_path = assets_dir / filename
                out_path.write_bytes(data)
                ir.assets[name] = f"assets/{filename}"

    def _parse_relationships(self, zf: ZipFile) -> dict[str, dict[str, str]]:
        """Parse word/_rels/document.xml.rels to get rId → target mapping."""
        rels: dict[str, dict[str, str]] = {}
        rels_path = "word/_rels/document.xml.rels"
        if rels_path not in zf.namelist():
            return rels

        rels_xml = zf.read(rels_path)
        tree = etree.fromstring(rels_xml)  # noqa: S320 - parse OOXML relationships from local .docx package

        for rel in tree.findall(f"{{{NS['rel']}}}Relationship"):
            rid = rel.get("Id", "")
            target = rel.get("Target", "")
            rel_type = rel.get("Type", "")
            rels[rid] = {"target": target, "type": rel_type}

        return rels

    def _parse_styles(self, zf: ZipFile) -> DocxStyleInfo:
        """Parse document styles and page setup from settings/styles XML."""
        style_info = DocxStyleInfo()

        # Parse page setup from document.xml (sectPr)
        if "word/document.xml" in zf.namelist():
            doc_xml = zf.read("word/document.xml")
            tree = etree.fromstring(doc_xml)  # noqa: S320 - parse OOXML from local .docx package
            sect_pr = tree.find(f".//{{{NS['w']}}}sectPr")
            if sect_pr is not None:
                style_info.page_setup = self._parse_page_setup(sect_pr)

        # Parse default font from styles.xml
        if "word/styles.xml" in zf.namelist():
            styles_xml = zf.read("word/styles.xml")
            styles_tree = etree.fromstring(styles_xml)  # noqa: S320 - parse OOXML styles from local .docx package
            doc_defaults = styles_tree.find(f".//{{{NS['w']}}}docDefaults")
            if doc_defaults is not None:
                rpr_default = doc_defaults.find(
                    f".//{{{NS['w']}}}rPrDefault/{{{NS['w']}}}rPr"
                )
                if rpr_default is not None:
                    font_el = rpr_default.find(f"{{{NS['w']}}}rFonts")
                    if font_el is not None:
                        style_info.default_font_name = (
                            font_el.get(f"{{{NS['w']}}}ascii")
                            or font_el.get(f"{{{NS['w']}}}hAnsi")
                            or "Calibri"
                        )
                    sz_el = rpr_default.find(f"{{{NS['w']}}}sz")
                    if sz_el is not None:
                        val = sz_el.get(f"{{{NS['w']}}}val")
                        if val:
                            style_info.default_font_size = _half_pt_to_pt(int(val))

        return style_info

    def _parse_page_setup(self, sect_pr: etree._Element) -> PageSetup:
        """Parse a sectPr element into PageSetup."""
        setup = PageSetup()

        # Page size
        pg_sz = sect_pr.find(f"{{{NS['w']}}}pgSz")
        if pg_sz is not None:
            w = pg_sz.get(f"{{{NS['w']}}}w")
            h = pg_sz.get(f"{{{NS['w']}}}h")
            orient = pg_sz.get(f"{{{NS['w']}}}orient")
            if orient == "landscape":
                setup.orientation = "landscape"
            if w and h:
                # Detect standard sizes
                w_cm = _twips_to_cm(int(w))
                h_cm = _twips_to_cm(int(h))
                if abs(w_cm - 21.0) < 0.5 and abs(h_cm - 29.7) < 0.5:
                    setup.size = "A4"
                elif abs(w_cm - 29.7) < 0.5 and abs(h_cm - 21.0) < 0.5:
                    setup.size = "A4"
                    setup.orientation = "landscape"
                elif abs(w_cm - 21.59) < 0.5 and abs(h_cm - 27.94) < 0.5:
                    setup.size = "Letter"
                else:
                    setup.size = "custom"
                    setup.custom_width = w_cm
                    setup.custom_height = h_cm

        # Margins
        pg_mar = sect_pr.find(f"{{{NS['w']}}}pgMar")
        if pg_mar is not None:
            for attr, field_name in [
                ("top", "margin_top"),
                ("bottom", "margin_bottom"),
                ("left", "margin_left"),
                ("right", "margin_right"),
                ("header", "header_distance"),
                ("footer", "footer_distance"),
            ]:
                val = pg_mar.get(f"{{{NS['w']}}}{attr}")
                if val:
                    setattr(setup, field_name, _twips_to_cm(int(val)))

        return setup

    def _parse_body(
        self,
        body: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        parts_dir: Path,
    ) -> None:
        """Parse all child elements of the document body into blocks."""
        for element in body:
            tag = etree.QName(element.tag).localname

            if tag == "p":
                self._parse_paragraph(element, ir, rels, assets_dir)
            elif tag == "tbl":
                self._parse_table(element, ir, rels, assets_dir, parts_dir)
            elif tag == "sdt":
                # Structured document tag (may contain TOC, etc.)
                self._parse_sdt(element, ir, rels, assets_dir, parts_dir)
            elif tag == "sectPr":
                # Final section properties — already handled in styles
                pass
            else:
                logger.debug(f"Skipping unknown body element: {tag}")

    def _parse_paragraph(
        self,
        p_elem: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
    ) -> None:
        """Parse a <w:p> element into one or more DfmBlocks."""
        # Check for embedded images
        drawings = p_elem.findall(f".//{{{NS['w']}}}drawing")
        if drawings:
            for drawing in drawings:
                self._parse_drawing(drawing, ir, rels, assets_dir)
            # If paragraph has only drawing (no text), don't create text block
            text = self._get_paragraph_text(p_elem)
            if not text.strip():
                return

        # Check for field codes (TOC, PAGE, etc.)
        fld_chars = p_elem.findall(f".//{{{NS['w']}}}fldChar")
        if fld_chars:
            self._parse_field_paragraph(p_elem, ir)
            return

        # Check for page/section break
        br_elem = p_elem.find(f".//{{{NS['w']}}}br")
        if br_elem is not None:
            br_type = br_elem.get(f"{{{NS['w']}}}type")
            if br_type == "page":
                block_id = ir.next_block_id(DfmBlockType.BREAK)
                ir.add_block(
                    DfmBlock(
                        id=block_id,
                        block_type=DfmBlockType.BREAK,
                        content="",
                        break_type=BreakType.PAGE,
                    )
                )
                return

        # Get paragraph properties
        ppr = p_elem.find(f"{{{NS['w']}}}pPr")
        style_name = self._get_style_name(ppr)
        outline_lvl = self._get_outline_level(ppr)

        # Parse runs
        runs = self._parse_runs(p_elem)
        text = "".join(r.text for r in runs)

        if not text.strip():
            # Empty paragraph — still preserve for spacing
            block_id = ir.next_block_id(DfmBlockType.PARAGRAPH)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.PARAGRAPH,
                    content="",
                    style_name=style_name,
                )
            )
            return

        # Determine block type
        if outline_lvl is not None and outline_lvl >= 0:
            # Heading
            level = outline_lvl + 1  # 0-based → 1-based
            block_id = ir.next_block_id(DfmBlockType.HEADING)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.HEADING,
                    content=text,
                    style_name=style_name,
                    level=level,
                    runs=runs,
                )
            )
        elif style_name and (
            "list" in style_name.lower() or "bullet" in style_name.lower()
        ):
            # List item
            list_level = self._get_list_level(ppr)
            num_id = self._get_num_id(ppr)
            block_id = ir.next_block_id(DfmBlockType.LIST_ITEM)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.LIST_ITEM,
                    content=text,
                    style_name=style_name,
                    list_level=list_level,
                    num_id=num_id,
                    runs=runs,
                )
            )
        elif style_name and "caption" in style_name.lower():
            # Caption
            block_id = ir.next_block_id(DfmBlockType.CAPTION)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.CAPTION,
                    content=text,
                    style_name=style_name,
                    runs=runs,
                )
            )
        else:
            # Check if mixed format
            has_mixed = self._has_mixed_formatting(runs)
            block_type = DfmBlockType.FORMAT if has_mixed else DfmBlockType.PARAGRAPH

            block_id = ir.next_block_id(block_type)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=block_type,
                    content=text,
                    style_name=style_name,
                    runs=runs,
                )
            )

    def _parse_runs(self, p_elem: etree._Element) -> list[FormatRun]:
        """Parse all <w:r> elements in a paragraph into FormatRuns."""
        runs = []
        for r_elem in p_elem.findall(f"{{{NS['w']}}}r"):
            text_parts = []
            for child in r_elem:
                tag = etree.QName(child.tag).localname
                if tag == "t":
                    text_parts.append(child.text or "")
                elif tag == "tab":
                    text_parts.append("\t")
                elif tag == "br":
                    br_type = child.get(f"{{{NS['w']}}}type")
                    if br_type != "page":  # Page breaks handled separately
                        text_parts.append("\n")

            text = "".join(text_parts)
            if not text:
                continue

            rpr = r_elem.find(f"{{{NS['w']}}}rPr")
            fmt = self._parse_run_properties(rpr)
            fmt.text = text
            runs.append(fmt)

        return runs

    def _parse_run_properties(self, rpr: etree._Element | None) -> FormatRun:
        """Parse <w:rPr> into a FormatRun (text will be set by caller)."""
        fmt = FormatRun(text="")
        if rpr is None:
            return fmt

        # Bold
        b_elem = rpr.find(f"{{{NS['w']}}}b")
        if b_elem is not None:
            val = b_elem.get(f"{{{NS['w']}}}val")
            fmt.bold = val != "0" if val else True

        # Italic
        i_elem = rpr.find(f"{{{NS['w']}}}i")
        if i_elem is not None:
            val = i_elem.get(f"{{{NS['w']}}}val")
            fmt.italic = val != "0" if val else True

        # Underline
        u_elem = rpr.find(f"{{{NS['w']}}}u")
        if u_elem is not None:
            val = u_elem.get(f"{{{NS['w']}}}val")
            fmt.underline = val not in (None, "none")

        # Strikethrough
        strike_elem = rpr.find(f"{{{NS['w']}}}strike")
        if strike_elem is not None:
            val = strike_elem.get(f"{{{NS['w']}}}val")
            fmt.strike = val != "0" if val else True

        # Superscript/subscript
        vert_align = rpr.find(f"{{{NS['w']}}}vertAlign")
        if vert_align is not None:
            val = vert_align.get(f"{{{NS['w']}}}val")
            fmt.superscript = val == "superscript"
            fmt.subscript = val == "subscript"

        # Font name
        fonts = rpr.find(f"{{{NS['w']}}}rFonts")
        if fonts is not None:
            fmt.font_name = (
                fonts.get(f"{{{NS['w']}}}ascii")
                or fonts.get(f"{{{NS['w']}}}hAnsi")
                or fonts.get(f"{{{NS['w']}}}eastAsia")
            )

        # Font size
        sz = rpr.find(f"{{{NS['w']}}}sz")
        if sz is not None:
            val = sz.get(f"{{{NS['w']}}}val")
            if val:
                fmt.font_size = _half_pt_to_pt(int(val))

        # Color
        color = rpr.find(f"{{{NS['w']}}}color")
        if color is not None:
            val = color.get(f"{{{NS['w']}}}val")
            if val and val != "auto":
                fmt.color = f"#{val}"

        # Highlight
        highlight = rpr.find(f"{{{NS['w']}}}highlight")
        if highlight is not None:
            fmt.highlight = highlight.get(f"{{{NS['w']}}}val")

        # Small caps
        small_caps = rpr.find(f"{{{NS['w']}}}smallCaps")
        if small_caps is not None:
            val = small_caps.get(f"{{{NS['w']}}}val")
            fmt.small_caps = val != "0" if val else True

        return fmt

    def _parse_table(
        self,
        tbl_elem: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        parts_dir: Path,
    ) -> None:
        """Parse a <w:tbl> element into a DfmBlock."""
        block_id = ir.next_block_id(DfmBlockType.TABLE)

        # Table style
        tbl_pr = tbl_elem.find(f"{{{NS['w']}}}tblPr")
        table_style = None
        if tbl_pr is not None:
            style_el = tbl_pr.find(f"{{{NS['w']}}}tblStyle")
            if style_el is not None:
                table_style = style_el.get(f"{{{NS['w']}}}val")

        # Parse rows and cells
        rows_data: list[list[str]] = []
        col_count = 0
        merged_cells: list[MergedCell] = []
        cell_formats: dict[str, CellFormat] = {}
        col_widths: list[float] = []

        # Try to get column widths from tblGrid
        tbl_grid = tbl_elem.find(f"{{{NS['w']}}}tblGrid")
        if tbl_grid is not None:
            for grid_col in tbl_grid.findall(f"{{{NS['w']}}}gridCol"):
                w = grid_col.get(f"{{{NS['w']}}}w")
                if w:
                    col_widths.append(_twips_to_cm(int(w)))

        # Parse rows
        for row_idx, tr_elem in enumerate(tbl_elem.findall(f"{{{NS['w']}}}tr")):
            row_cells: list[str] = []
            for col_idx, tc_elem in enumerate(tr_elem.findall(f"{{{NS['w']}}}tc")):
                # Get cell text
                cell_text = self._get_cell_text(tc_elem)
                row_cells.append(cell_text)

                # Check for merged cells
                tc_pr = tc_elem.find(f"{{{NS['w']}}}tcPr")
                if tc_pr is not None:
                    # Horizontal merge
                    grid_span = tc_pr.find(f"{{{NS['w']}}}gridSpan")
                    col_span = 1
                    if grid_span is not None:
                        val = grid_span.get(f"{{{NS['w']}}}val")
                        if val:
                            col_span = int(val)

                    # Vertical merge
                    v_merge = tc_pr.find(f"{{{NS['w']}}}vMerge")
                    if v_merge is not None:
                        val = v_merge.get(f"{{{NS['w']}}}val")
                        if val == "restart":
                            # Count how many rows this spans
                            row_span = self._count_vmerge(tbl_elem, row_idx, col_idx)
                            if col_span > 1 or row_span > 1:
                                merged_cells.append(
                                    MergedCell(
                                        row=row_idx,
                                        col=col_idx,
                                        row_span=row_span,
                                        col_span=col_span,
                                    )
                                )
                        # Continuation cell (merged into cell above)
                    elif col_span > 1:
                        merged_cells.append(
                            MergedCell(
                                row=row_idx,
                                col=col_idx,
                                row_span=1,
                                col_span=col_span,
                            )
                        )

                    # Cell formatting
                    cell_fmt = self._parse_cell_format(tc_pr, tc_elem)
                    if cell_fmt:
                        cell_formats[f"{row_idx}:{col_idx}"] = cell_fmt

            rows_data.append(row_cells)
            col_count = max(col_count, len(row_cells))

        # Build markdown table
        md_table = self._rows_to_md_table(rows_data)

        # Check if table has nested tables (complex case)
        nested_tables = tbl_elem.findall(f".//{{{NS['w']}}}tbl")
        is_nested = False
        raw_xml_ref = None
        if nested_tables:
            # Save raw XML for complex nested tables
            raw_xml_ref = f"parts/nested_table_{block_id}.xml"
            xml_path = parts_dir / f"nested_table_{block_id}.xml"
            xml_path.write_bytes(etree.tostring(tbl_elem, xml_declaration=True))
            is_nested = True

        ir.add_block(
            DfmBlock(
                id=block_id,
                block_type=DfmBlockType.TABLE,
                content=md_table,
                table_style=table_style,
                col_widths=col_widths,
                merged_cells=merged_cells,
                cell_formats=cell_formats,
                is_nested=is_nested,
                raw_xml_ref=raw_xml_ref,
            )
        )

    def _parse_drawing(
        self,
        drawing: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
    ) -> None:
        """Parse a <w:drawing> element (image or chart)."""
        # Check for inline image
        inline = drawing.find(f"{{{NS['wp']}}}inline")
        anchor = drawing.find(f"{{{NS['wp']}}}anchor")
        target = inline if inline is not None else anchor
        anchor_type = (
            ImageAnchorType.INLINE if inline is not None else ImageAnchorType.FLOATING
        )

        if target is None:
            return

        # Get dimensions
        extent = target.find(f"{{{NS['wp']}}}extent")
        width_cm = 0.0
        height_cm = 0.0
        if extent is not None:
            cx = extent.get("cx")
            cy = extent.get("cy")
            if cx:
                width_cm = _emu_to_cm(int(cx))
            if cy:
                height_cm = _emu_to_cm(int(cy))

        # Get alt text
        doc_pr = target.find(f"{{{NS['wp']}}}docPr")
        alt_text = ""
        if doc_pr is not None:
            alt_text = doc_pr.get("descr", "") or doc_pr.get("name", "")

        # Check for embedded chart
        chart_ref = target.find(f".//{{{NS['a']}}}graphicData")
        if chart_ref is not None:
            uri = chart_ref.get("uri", "")
            if "chart" in uri.lower():
                self._parse_chart(target, ir, rels, assets_dir, width_cm, height_cm)
                return

        # Regular image — find the blip (image reference)
        blip = target.find(f".//{{{NS['a']}}}blip")
        if blip is None:
            return

        embed_id = blip.get(f"{{{NS['r']}}}embed")
        if not embed_id or embed_id not in rels:
            return

        # Resolve image path
        rel_target = rels[embed_id]["target"]
        media_path = (
            f"word/{rel_target}" if not rel_target.startswith("word/") else rel_target
        )
        asset_name = ir.assets.get(media_path)
        if not asset_name:
            # Try just the filename
            filename = Path(rel_target).name
            asset_name = f"assets/{filename}"

        block_id = ir.next_block_id(DfmBlockType.IMAGE)
        ir.add_block(
            DfmBlock(
                id=block_id,
                block_type=DfmBlockType.IMAGE,
                content=alt_text or f"Image {block_id}",
                image_path=asset_name,
                image_width_cm=width_cm,
                image_height_cm=height_cm,
                image_anchor=anchor_type,
                image_alt=alt_text,
            )
        )

    def _parse_chart(
        self,
        target: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        width_cm: float,
        height_cm: float,
    ) -> None:
        """Parse an embedded chart into a protected DfmBlock."""
        block_id = ir.next_block_id(DfmBlockType.CHART)

        binary_ref = f"assets/chart_{block_id}.bin"

        ir.add_block(
            DfmBlock(
                id=block_id,
                block_type=DfmBlockType.CHART,
                content="Embedded Chart",
                binary_ref=binary_ref,
                chart_type="unknown",
                image_width_cm=width_cm,
                image_height_cm=height_cm,
            )
        )

    def _parse_field_paragraph(self, p_elem: etree._Element, ir: DocxIR) -> None:
        """Parse a paragraph containing field codes."""
        # Extract field instruction
        instr_texts = []
        for instr in p_elem.findall(f".//{{{NS['w']}}}instrText"):
            if instr.text:
                instr_texts.append(instr.text)

        instruction = " ".join(instr_texts).strip()

        # Determine field type
        if instruction.upper().startswith("TOC"):
            block_id = ir.next_block_id(DfmBlockType.TOC)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.TOC,
                    content="Table of Contents",
                    field_code=instruction,
                )
            )
        elif instruction.upper().startswith("PAGE"):
            block_id = ir.next_block_id(DfmBlockType.FIELD)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.FIELD,
                    content="",
                    field_type="PAGE",
                    field_instruction=instruction,
                )
            )
        elif (
            "ADDIN ZOTERO" in instruction.upper() or "ADDIN EN." in instruction.upper()
        ):
            # Zotero or EndNote citation
            display_text = self._get_paragraph_text(p_elem)
            block_id = ir.next_block_id(DfmBlockType.CITATION)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.CITATION,
                    content=display_text,
                    field_instruction=instruction,
                    citation_entries=[{"field_code": instruction}],
                )
            )
        else:
            # Generic field
            display_text = self._get_paragraph_text(p_elem)
            block_id = ir.next_block_id(DfmBlockType.FIELD)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.FIELD,
                    content=display_text,
                    field_instruction=instruction,
                )
            )

    def _parse_sdt(
        self,
        sdt_elem: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        parts_dir: Path,
    ) -> None:
        """Parse a structured document tag (<w:sdt>), often used for TOC."""
        # Check if this is a TOC
        sdt_pr = sdt_elem.find(f"{{{NS['w']}}}sdtPr")
        if sdt_pr is not None:
            doc_part = sdt_pr.find(f"{{{NS['w']}}}docPartObj")
            if doc_part is not None:
                gallery = doc_part.find(f"{{{NS['w']}}}docPartGallery")
                if (
                    gallery is not None
                    and "toc" in (gallery.get(f"{{{NS['w']}}}val") or "").lower()
                ):
                    # It's a TOC — save as protected block
                    block_id = ir.next_block_id(DfmBlockType.TOC)

                    # Save raw XML
                    xml_ref = f"parts/toc_{block_id}.xml"
                    xml_path = parts_dir / f"toc_{block_id}.xml"
                    xml_path.write_bytes(etree.tostring(sdt_elem, xml_declaration=True))

                    ir.add_block(
                        DfmBlock(
                            id=block_id,
                            block_type=DfmBlockType.TOC,
                            content="Table of Contents",
                            xml_ref=xml_ref,
                        )
                    )
                    return

        # Otherwise, parse content normally
        sdt_content = sdt_elem.find(f"{{{NS['w']}}}sdtContent")
        if sdt_content is not None:
            for child in sdt_content:
                tag = etree.QName(child.tag).localname
                if tag == "p":
                    self._parse_paragraph(child, ir, rels, assets_dir)
                elif tag == "tbl":
                    self._parse_table(child, ir, rels, assets_dir, parts_dir)

    def _parse_footnotes(self, zf: ZipFile, ir: DocxIR) -> None:
        """Parse word/footnotes.xml."""
        if "word/footnotes.xml" not in zf.namelist():
            return

        fn_xml = zf.read("word/footnotes.xml")
        tree = etree.fromstring(fn_xml)  # noqa: S320 - parse OOXML footnotes from local .docx package

        for footnote in tree.findall(f"{{{NS['w']}}}footnote"):
            fn_type = footnote.get(f"{{{NS['w']}}}type")
            if fn_type in ("separator", "continuationSeparator"):
                continue

            fn_id_str = footnote.get(f"{{{NS['w']}}}id")
            if fn_id_str is None:
                continue
            fn_id = int(fn_id_str)

            # Get footnote text
            text_parts = []
            for p in footnote.findall(f"{{{NS['w']}}}p"):
                text_parts.append(self._get_paragraph_text(p))
            text = "\n".join(text_parts)

            if text.strip():
                block_id = ir.next_block_id(DfmBlockType.FOOTNOTE)
                ir.add_block(
                    DfmBlock(
                        id=block_id,
                        block_type=DfmBlockType.FOOTNOTE,
                        content=text,
                        footnote_id=fn_id,
                    )
                )

    def _parse_headers_footers(self, zf: ZipFile, ir: DocxIR, parts_dir: Path) -> None:
        """Parse and preserve header/footer XML parts."""
        for name in zf.namelist():
            if name.startswith("word/header") and name.endswith(".xml"):
                data = zf.read(name)
                safe_name = Path(name).name
                (parts_dir / safe_name).write_bytes(data)

                # Extract preview text
                tree = etree.fromstring(data)  # noqa: S320 - parse saved OOXML header fragment
                preview = self._get_all_text(tree)

                hdr_type = "default"
                if "2" in safe_name:
                    hdr_type = "first"
                elif "3" in safe_name:
                    hdr_type = "even"

                block_id = ir.next_block_id(DfmBlockType.HEADER)
                ir.add_block(
                    DfmBlock(
                        id=block_id,
                        block_type=DfmBlockType.HEADER,
                        content="",
                        hdr_ftr_type=hdr_type,
                        xml_ref=f"parts/{safe_name}",
                        preview_text=preview[:100],
                    )
                )

            elif name.startswith("word/footer") and name.endswith(".xml"):
                data = zf.read(name)
                safe_name = Path(name).name
                (parts_dir / safe_name).write_bytes(data)

                preview_tree = etree.fromstring(data)  # noqa: S320 - parse saved OOXML footer fragment
                preview = self._get_all_text(preview_tree)

                ftr_type = "default"
                if "2" in safe_name:
                    ftr_type = "first"
                elif "3" in safe_name:
                    ftr_type = "even"

                block_id = ir.next_block_id(DfmBlockType.FOOTER)
                ir.add_block(
                    DfmBlock(
                        id=block_id,
                        block_type=DfmBlockType.FOOTER,
                        content="",
                        hdr_ftr_type=ftr_type,
                        xml_ref=f"parts/{safe_name}",
                        preview_text=preview[:100],
                    )
                )

    # ========================================================================
    # Private: XML text extraction helpers
    # ========================================================================

    def _get_paragraph_text(self, p_elem: etree._Element) -> str:
        """Get concatenated text from a paragraph element."""
        parts = []
        for t_elem in p_elem.findall(f".//{{{NS['w']}}}t"):
            if t_elem.text:
                parts.append(t_elem.text)
        return "".join(parts)

    def _get_cell_text(self, tc_elem: etree._Element) -> str:
        """Get text from a table cell, joining paragraphs with newlines."""
        parts = []
        for p in tc_elem.findall(f"{{{NS['w']}}}p"):
            parts.append(self._get_paragraph_text(p))
        return "\n".join(parts)

    def _get_all_text(self, elem: etree._Element) -> str:
        """Get all text from any element tree."""
        parts = []
        for t_elem in elem.findall(f".//{{{NS['w']}}}t"):
            if t_elem.text:
                parts.append(t_elem.text)
        return " ".join(parts)

    def _get_style_name(self, ppr: etree._Element | None) -> str | None:
        """Get paragraph style name from pPr."""
        if ppr is None:
            return None
        style = ppr.find(f"{{{NS['w']}}}pStyle")
        if style is not None:
            val: str | None = style.get(f"{{{NS['w']}}}val")
            return val
        return None

    def _get_outline_level(self, ppr: etree._Element | None) -> int | None:
        """Get outline level from pPr (indicates heading)."""
        if ppr is None:
            return None
        outline = ppr.find(f"{{{NS['w']}}}outlineLvl")
        if outline is not None:
            val = outline.get(f"{{{NS['w']}}}val")
            if val is not None:
                return int(val)

        # Also check style name for heading pattern
        style = self._get_style_name(ppr)
        if style:
            match = re.match(r"[Hh]eading\s*(\d+)", style)
            if match:
                return int(match.group(1)) - 1
        return None

    def _get_list_level(self, ppr: etree._Element | None) -> int:
        """Get list indentation level."""
        if ppr is None:
            return 0
        num_pr = ppr.find(f"{{{NS['w']}}}numPr")
        if num_pr is not None:
            ilvl = num_pr.find(f"{{{NS['w']}}}ilvl")
            if ilvl is not None:
                val = ilvl.get(f"{{{NS['w']}}}val")
                if val:
                    return int(val)
        return 0

    def _get_num_id(self, ppr: etree._Element | None) -> int | None:
        """Get numbering ID for list items."""
        if ppr is None:
            return None
        num_pr = ppr.find(f"{{{NS['w']}}}numPr")
        if num_pr is not None:
            num_id = num_pr.find(f"{{{NS['w']}}}numId")
            if num_id is not None:
                val = num_id.get(f"{{{NS['w']}}}val")
                if val:
                    return int(val)
        return None

    def _has_mixed_formatting(self, runs: list[FormatRun]) -> bool:
        """Check if runs have genuinely different formatting."""
        if len(runs) <= 1:
            return False
        first = runs[0]
        return any(
            r.bold != first.bold
            or r.italic != first.italic
            or r.font_name != first.font_name
            or r.font_size != first.font_size
            or r.color != first.color
            or r.underline != first.underline
            for r in runs[1:]
        )

    def _count_vmerge(
        self, tbl_elem: etree._Element, start_row: int, col_idx: int
    ) -> int:
        """Count how many rows are vertically merged starting from start_row."""
        rows = tbl_elem.findall(f"{{{NS['w']}}}tr")
        span = 1
        for row_idx in range(start_row + 1, len(rows)):
            cells = rows[row_idx].findall(f"{{{NS['w']}}}tc")
            if col_idx >= len(cells):
                break
            tc_pr = cells[col_idx].find(f"{{{NS['w']}}}tcPr")
            if tc_pr is not None:
                v_merge = tc_pr.find(f"{{{NS['w']}}}vMerge")
                if v_merge is not None and v_merge.get(f"{{{NS['w']}}}val") is None:
                    span += 1
                    continue
            break
        return span

    def _parse_cell_format(
        self, tc_pr: etree._Element, tc_elem: etree._Element
    ) -> CellFormat | None:
        """Parse cell-level formatting."""
        fmt = CellFormat()
        has_format = False

        # Background color (shading)
        shd = tc_pr.find(f"{{{NS['w']}}}shd")
        if shd is not None:
            fill = shd.get(f"{{{NS['w']}}}fill")
            if fill and fill != "auto":
                fmt.bg_color = f"#{fill}"
                has_format = True

        # Cell alignment
        jc = tc_pr.find(f"{{{NS['w']}}}jc")
        if jc is None:
            # Check paragraph alignment within cell
            p = tc_elem.find(f"{{{NS['w']}}}p")
            if p is not None:
                ppr = p.find(f"{{{NS['w']}}}pPr")
                if ppr is not None:
                    jc = ppr.find(f"{{{NS['w']}}}jc")

        if jc is not None:
            val = jc.get(f"{{{NS['w']}}}val")
            if val == "center":
                fmt.align = TableCellAlign.CENTER
                has_format = True
            elif val == "right":
                fmt.align = TableCellAlign.RIGHT
                has_format = True

        # Check first run for bold/italic
        first_r = tc_elem.find(f".//{{{NS['w']}}}r/{{{NS['w']}}}rPr")
        if first_r is not None:
            b = first_r.find(f"{{{NS['w']}}}b")
            if b is not None:
                fmt.bold = True
                has_format = True
            i = first_r.find(f"{{{NS['w']}}}i")
            if i is not None:
                fmt.italic = True
                has_format = True
            color = first_r.find(f"{{{NS['w']}}}color")
            if color is not None:
                val = color.get(f"{{{NS['w']}}}val")
                if val and val != "auto":
                    fmt.font_color = f"#{val}"
                    has_format = True

        return fmt if has_format else None

    # ========================================================================
    # Private: Markdown table builder
    # ========================================================================

    @staticmethod
    def _rows_to_md_table(rows: list[list[str]]) -> str:
        """Convert a list of rows to a Markdown pipe table."""
        if not rows:
            return ""

        # Ensure all rows have same number of columns
        max_cols = max(len(r) for r in rows)
        for row in rows:
            while len(row) < max_cols:
                row.append("")

        # Clean cell text (replace newlines, strip)
        for row in rows:
            for i, cell in enumerate(row):
                row[i] = cell.replace("\n", " ").strip()

        # Calculate column widths
        widths = [0] * max_cols
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell), 3)

        # Build table
        lines = []

        # Header row
        header = (
            "| "
            + " | ".join(rows[0][i].ljust(widths[i]) for i in range(max_cols))
            + " |"
        )
        lines.append(header)

        # Separator
        sep = "| " + " | ".join("-" * widths[i] for i in range(max_cols)) + " |"
        lines.append(sep)

        # Data rows
        for row in rows[1:]:
            line = (
                "| "
                + " | ".join(row[i].ljust(widths[i]) for i in range(max_cols))
                + " |"
            )
            lines.append(line)

        return "\n".join(lines)

    # ========================================================================
    # Private: Rebuild docx from IR
    # ========================================================================

    def _update_document_xml(self, docx_path: Path, ir: DocxIR) -> None:
        """
        Update document.xml within the docx zip with modified text from IR.

        Strategy: Parse the existing document.xml, walk paragraphs and tables
        in order, match them 1:1 with IR blocks, and update text content
        where it has changed.
        """
        import zipfile

        # Read the existing zip
        temp_path = docx_path.with_suffix(".tmp")

        with zipfile.ZipFile(docx_path, "r") as zin:
            doc_xml = zin.read("word/document.xml")

            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == "word/document.xml":
                        # Modify document.xml
                        modified_xml = self._apply_text_changes(doc_xml, ir)
                        zout.writestr(item, modified_xml)
                    else:
                        zout.writestr(item, zin.read(item.filename))

        # Replace original with modified
        temp_path.replace(docx_path)

    def _apply_text_changes(self, doc_xml: bytes, ir: DocxIR) -> bytes:
        """
        Apply text changes from IR blocks back to document.xml.

        Walks paragraphs and tables in the same order as original parsing,
        matching each to the corresponding IR block by index position.
        """
        tree = etree.fromstring(doc_xml)  # noqa: S320 - parse OOXML from local .docx package
        body = tree.find(f".//{{{NS['w']}}}body")
        if body is None:
            return doc_xml

        block_idx = 0

        for element in body:
            tag = etree.QName(element.tag).localname

            if tag == "p":
                if block_idx < len(ir.blocks):
                    block = ir.blocks[block_idx]
                    if block.block_type in (
                        DfmBlockType.PARAGRAPH,
                        DfmBlockType.HEADING,
                        DfmBlockType.LIST_ITEM,
                        DfmBlockType.FORMAT,
                        DfmBlockType.CAPTION,
                    ):
                        self._update_paragraph_text(element, block)
                    block_idx += 1
            elif tag == "tbl" and block_idx < len(ir.blocks):
                block = ir.blocks[block_idx]
                if block.block_type == DfmBlockType.TABLE:
                    self._update_table_text(element, block)
                block_idx += 1

        return bytes(
            etree.tostring(
                tree, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        )

    def _update_paragraph_text(self, p_elem: etree._Element, block: DfmBlock) -> None:
        """Update text content of a paragraph element from a DfmBlock."""
        runs = p_elem.findall(f"{{{NS['w']}}}r")
        if not runs:
            return

        new_text = block.content
        if not new_text:
            return

        # Simple strategy: put all text into the first run, clear others
        # This preserves the first run's formatting
        first_run_t = runs[0].find(f"{{{NS['w']}}}t")
        if first_run_t is not None:
            first_run_t.text = new_text
            first_run_t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")

        # Clear text from subsequent runs
        for r in runs[1:]:
            t_elem = r.find(f"{{{NS['w']}}}t")
            if t_elem is not None:
                t_elem.text = ""

    def _update_table_text(self, tbl_elem: etree._Element, block: DfmBlock) -> None:
        """Update text content of table cells from a DfmBlock."""
        # Parse markdown table back to rows
        md_rows = self._parse_md_table(block.content)
        if not md_rows:
            return

        xml_rows = tbl_elem.findall(f"{{{NS['w']}}}tr")

        for _row_idx, (xml_row, md_row) in enumerate(
            zip(xml_rows, md_rows, strict=False)
        ):
            cells = xml_row.findall(f"{{{NS['w']}}}tc")
            for _col_idx, (cell, md_cell) in enumerate(
                zip(cells, md_row, strict=False)
            ):
                # Update first paragraph's text in the cell
                paragraphs = cell.findall(f"{{{NS['w']}}}p")
                if not paragraphs:
                    continue

                first_p = paragraphs[0]
                first_r = first_p.find(f"{{{NS['w']}}}r")
                if first_r is not None:
                    t_elem = first_r.find(f"{{{NS['w']}}}t")
                    if t_elem is not None:
                        t_elem.text = md_cell.strip()
                        t_elem.set(
                            "{http://www.w3.org/XML/1998/namespace}space",
                            "preserve",
                        )

                    # Clear text from subsequent runs in the first paragraph
                    for r in first_p.findall(f"{{{NS['w']}}}r")[1:]:
                        t = r.find(f"{{{NS['w']}}}t")
                        if t is not None:
                            t.text = ""

                # Clear text from subsequent paragraphs in the cell
                for p in paragraphs[1:]:
                    for r in p.findall(f"{{{NS['w']}}}r"):
                        t = r.find(f"{{{NS['w']}}}t")
                        if t is not None:
                            t.text = ""

    @staticmethod
    def _parse_md_table(md_table: str) -> list[list[str]]:
        """Parse a markdown pipe table back into rows of cell text."""
        rows = []
        for line in md_table.strip().split("\n"):
            line = line.strip()
            if not line.startswith("|"):
                continue
            # Skip separator row
            if re.match(r"^\|[\s\-:|]+\|$", line):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            rows.append(cells)
        return rows
