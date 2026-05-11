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
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from zipfile import ZipFile

from lxml import etree  # type: ignore[import-untyped]

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
from src.infrastructure.dfm_parser import DfmParser
from src.infrastructure.encoding_guard import validate_zip_magic

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

_REVISION_TAG_TYPES = {
    "ins": "insert",
    "del": "delete",
    "moveFrom": "move_from",
    "moveTo": "move_to",
    "rPrChange": "format",
    "pPrChange": "paragraph_format",
}
_NON_VISIBLE_REVISION_TAGS = {"del", "moveFrom"}
_DIFF_TOKEN_RE = re.compile(r"\s+|\S+")
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_DOCX_LOCATOR_VERSION = "docx-dfm-locator-v1"

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


def _safe_int(value: str | None, default: int | None = None) -> int | None:
    """Parse an OpenXML integer attribute without trusting converted DOCX."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@dataclass
class _TrackChangeContext:
    """Shared state for one DOCX tracked-change write operation."""

    author: str
    date: str
    next_id: int = 1

    def take_id(self) -> str:
        revision_id = str(self.next_id)
        self.next_id += 1
        return revision_id


@dataclass
class _RunStyleSpan:
    """Character span mapped to the run properties that styled it."""

    start: int
    end: int
    rpr: etree._Element | None = None


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

        # Guard: verify ZIP magic bytes before opening (fail-closed).
        # EncodingError propagates up so callers can surface a clean message.
        validate_zip_magic(docx_path)

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
            tree = etree.fromstring(doc_xml)
            body = tree.find(f".//{{{NS['w']}}}body")
            if body is not None:
                self._parse_body(body, ir, rels, assets_dir, parts_dir)

            # 6. Parse footnotes
            self._parse_footnotes(zf, ir)

            # 7. Parse headers/footers
            self._parse_headers_footers(zf, ir, parts_dir)

        return ir

    def ir_to_docx(
        self,
        ir: DocxIR,
        data_dir: Path,
        output_path: Path,
        *,
        changed_block_ids: set[str] | None = None,
        original_ir: DocxIR | None = None,
        track_changes: bool = False,
        revision_author: str = "Asset-Aware MCP",
    ) -> Path:
        """
        Rebuild a .docx file from a DocxIR.

        Uses the original.docx as base and replaces text content
        according to the modified IR blocks. When ``track_changes`` is enabled,
        changed text is emitted as Word revisions (``w:del``/``w:ins``) by
        diffing ``original_ir`` against ``ir``.

        Args:
            ir: The (possibly modified) intermediate representation
            data_dir: Directory containing original.docx, parts/, assets/
            output_path: Where to write the output .docx
            changed_block_ids: Optional set of block ids that may be written
            original_ir: Original IR before edits, required for precise diffs
            track_changes: If True, write textual edits as Word Track Changes
            revision_author: Author recorded on generated revision elements

        Returns:
            Path to the generated .docx file
        """
        original = data_dir / "original.docx"
        if not original.exists():
            raise FileNotFoundError(f"Original docx not found: {original}")

        # Copy original as base
        shutil.copy2(original, output_path)

        # Modify document.xml in-place within the zip
        self._update_document_xml(
            output_path,
            ir,
            changed_block_ids=changed_block_ids,
            original_ir=original_ir,
            track_changes=track_changes,
            revision_author=revision_author,
        )

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
        tree = etree.fromstring(rels_xml)

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
            tree = etree.fromstring(doc_xml)
            sect_pr = tree.find(f".//{{{NS['w']}}}sectPr")
            if sect_pr is not None:
                style_info.page_setup = self._parse_page_setup(sect_pr)

        # Parse default font from styles.xml
        if "word/styles.xml" in zf.namelist():
            styles_xml = zf.read("word/styles.xml")
            styles_tree = etree.fromstring(styles_xml)
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
        paragraph_index = 0
        table_index = 0
        sdt_index = 0
        for source_order, element in enumerate(body):
            tag = etree.QName(element.tag).localname

            if tag == "p":
                self._parse_paragraph(
                    element,
                    ir,
                    rels,
                    assets_dir,
                    source_part="word/document.xml",
                    source_story="body",
                    paragraph_index=paragraph_index,
                    source_order=source_order,
                )
                paragraph_index += 1
            elif tag == "tbl":
                self._parse_table(
                    element,
                    ir,
                    rels,
                    assets_dir,
                    parts_dir,
                    source_part="word/document.xml",
                    source_story="body",
                    table_index=table_index,
                    source_order=source_order,
                )
                table_index += 1
            elif tag == "sdt":
                # Structured document tag (may contain TOC, etc.)
                self._parse_sdt(
                    element,
                    ir,
                    rels,
                    assets_dir,
                    parts_dir,
                    source_part="word/document.xml",
                    source_story="body",
                    sdt_index=sdt_index,
                    source_order=source_order,
                )
                sdt_index += 1
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
        *,
        source_part: str = "word/document.xml",
        source_story: str = "body",
        paragraph_index: int | None = None,
        table_index: int | None = None,
        source_order: int | None = None,
        parent_table_id: str | None = None,
        parent_cell: str | None = None,
        sdt_index: int | None = None,
    ) -> None:
        """Parse a <w:p> element into one or more DfmBlocks."""
        # Check for embedded images
        drawings = p_elem.findall(f".//{{{NS['w']}}}drawing")
        if drawings:
            for drawing_index, drawing in enumerate(drawings):
                drawing_metadata = self._docx_locator_metadata(
                    source_part=source_part,
                    source_story=source_story,
                    source_element="w:drawing",
                    paragraph_index=paragraph_index,
                    table_index=table_index,
                    source_order=source_order,
                    parent_table_id=parent_table_id,
                    parent_cell=parent_cell,
                    sdt_index=sdt_index,
                    extra={"drawing_index": drawing_index},
                )
                self._parse_drawing(
                    drawing,
                    ir,
                    rels,
                    assets_dir,
                    metadata=drawing_metadata,
                )
            # If paragraph has only drawing (no text), don't create text block
            text = self._get_paragraph_text(p_elem)
            if not text.strip():
                self._add_revision_blocks(
                    p_elem,
                    ir,
                    scope="paragraph",
                    source_metadata=drawing_metadata if drawings else None,
                )
                return

        # Check for field codes (TOC, PAGE, etc.)
        fld_chars = p_elem.findall(f".//{{{NS['w']}}}fldChar")
        if fld_chars:
            field_metadata = self._docx_locator_metadata(
                source_part=source_part,
                source_story=source_story,
                source_element="w:p",
                paragraph_index=paragraph_index,
                table_index=table_index,
                source_order=source_order,
                parent_table_id=parent_table_id,
                parent_cell=parent_cell,
                sdt_index=sdt_index,
            )
            self._parse_field_paragraph(p_elem, ir, metadata=field_metadata)
            source_block_id = ir.blocks[-1].id if ir.blocks else None
            self._add_revision_blocks(
                p_elem,
                ir,
                scope="paragraph",
                source_block_id=source_block_id,
                source_metadata=field_metadata,
            )
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
                        metadata=self._docx_locator_metadata(
                            source_part=source_part,
                            source_story=source_story,
                            source_element="w:p",
                            paragraph_index=paragraph_index,
                            table_index=table_index,
                            source_order=source_order,
                            parent_table_id=parent_table_id,
                            parent_cell=parent_cell,
                            sdt_index=sdt_index,
                        ),
                    )
                )
                self._add_revision_blocks(
                    p_elem,
                    ir,
                    scope="paragraph",
                    source_block_id=block_id,
                    source_metadata=ir.blocks[-1].metadata if ir.blocks else None,
                )
                return

        # Get paragraph properties
        ppr = p_elem.find(f"{{{NS['w']}}}pPr")
        style_name = self._get_style_name(ppr)
        outline_lvl = self._get_outline_level(ppr)

        # Parse runs
        runs = self._parse_runs(p_elem)
        text = "".join(r.text for r in runs)
        paragraph_metadata = self._docx_locator_metadata(
            source_part=source_part,
            source_story=source_story,
            source_element="w:p",
            paragraph_index=paragraph_index,
            table_index=table_index,
            source_order=source_order,
            parent_table_id=parent_table_id,
            parent_cell=parent_cell,
            sdt_index=sdt_index,
            runs=runs,
        )

        if not text.strip():
            # Empty paragraph — still preserve for spacing
            block_id = ir.next_block_id(DfmBlockType.PARAGRAPH)
            ir.add_block(
                DfmBlock(
                    id=block_id,
                    block_type=DfmBlockType.PARAGRAPH,
                    content="",
                    style_name=style_name,
                    metadata=paragraph_metadata,
                )
            )
            self._add_revision_blocks(
                p_elem,
                ir,
                scope="paragraph",
                source_block_id=block_id,
                source_metadata=paragraph_metadata,
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
                    metadata=paragraph_metadata,
                )
            )
            self._add_revision_blocks(
                p_elem,
                ir,
                scope="paragraph",
                source_block_id=block_id,
                source_metadata=paragraph_metadata,
            )
            return
        list_level = self._get_list_level(ppr)
        num_id = self._get_num_id(ppr)
        style_looks_list = bool(
            style_name
            and ("list" in style_name.lower() or "bullet" in style_name.lower())
        )
        if num_id is not None or style_looks_list:
            # List item
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
                    metadata=paragraph_metadata,
                )
            )
            self._add_revision_blocks(
                p_elem,
                ir,
                scope="paragraph",
                source_block_id=block_id,
                source_metadata=paragraph_metadata,
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
                    metadata=paragraph_metadata,
                )
            )
            self._add_revision_blocks(
                p_elem,
                ir,
                scope="paragraph",
                source_block_id=block_id,
                source_metadata=paragraph_metadata,
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
                    metadata=paragraph_metadata,
                )
            )
            self._add_revision_blocks(
                p_elem,
                ir,
                scope="paragraph",
                source_block_id=block_id,
                source_metadata=paragraph_metadata,
            )

    def _parse_runs(self, p_elem: etree._Element) -> list[FormatRun]:
        """Parse all <w:r> elements in a paragraph into FormatRuns."""
        runs = []
        for r_elem in self._iter_text_runs(p_elem):
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
        *,
        source_part: str = "word/document.xml",
        source_story: str = "body",
        table_index: int | None = None,
        source_order: int | None = None,
        parent_table_id: str | None = None,
        parent_cell: str | None = None,
        sdt_index: int | None = None,
    ) -> None:
        """Parse a <w:tbl> element into a DfmBlock plus any nested child tables."""
        block, nested_blocks = self._build_table_block(
            tbl_elem,
            ir,
            rels,
            assets_dir,
            parts_dir,
            source_part=source_part,
            source_story=source_story,
            table_index=table_index,
            source_order=source_order,
            parent_table_id=parent_table_id,
            parent_cell=parent_cell,
            sdt_index=sdt_index,
        )
        ir.add_block(block)
        self._add_revision_blocks(
            tbl_elem,
            ir,
            scope="table",
            source_block_id=block.id,
            context_text=block.content,
            source_metadata=block.metadata,
        )
        for nested_block in nested_blocks:
            ir.add_block(nested_block)

    def _build_table_block(
        self,
        tbl_elem: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        parts_dir: Path,
        *,
        source_part: str = "word/document.xml",
        source_story: str = "body",
        table_index: int | None = None,
        source_order: int | None = None,
        parent_cell: str | None = None,
        parent_table_id: str | None = None,
        sdt_index: int | None = None,
    ) -> tuple[DfmBlock, list[DfmBlock]]:
        """Build a table block and recursively extract nested child table blocks."""
        block_id = ir.next_block_id(DfmBlockType.TABLE)

        tbl_pr = tbl_elem.find(f"{{{NS['w']}}}tblPr")
        table_style = None
        if tbl_pr is not None:
            style_el = tbl_pr.find(f"{{{NS['w']}}}tblStyle")
            if style_el is not None:
                table_style = style_el.get(f"{{{NS['w']}}}val")

        rows_data: list[list[str]] = []
        merged_cells: list[MergedCell] = []
        cell_formats: dict[str, CellFormat] = {}
        col_widths: list[float] = []
        nested_blocks: list[DfmBlock] = []
        has_nested_descendants = False
        cell_locators: list[dict[str, int | str]] = []

        tbl_grid = tbl_elem.find(f"{{{NS['w']}}}tblGrid")
        if tbl_grid is not None:
            for grid_col in tbl_grid.findall(f"{{{NS['w']}}}gridCol"):
                w = grid_col.get(f"{{{NS['w']}}}w")
                if w:
                    col_widths.append(_twips_to_cm(int(w)))

        for row_idx, tr_elem in enumerate(tbl_elem.findall(f"{{{NS['w']}}}tr")):
            row_cells: list[str] = []
            for col_idx, tc_elem, col_span, tc_pr in self._iter_row_cells(tr_elem):
                while len(row_cells) < col_idx:
                    row_cells.append("")
                cell_text, child_nested_blocks = self._extract_cell_content(
                    tc_elem,
                    ir,
                    rels,
                    assets_dir,
                    parts_dir,
                    parent_cell=f"{row_idx}:{col_idx}",
                    parent_table_id=block_id,
                    source_part=source_part,
                    source_story=source_story,
                    table_index=table_index,
                    sdt_index=sdt_index,
                )
                row_cells.append(cell_text)
                row_cells.extend("" for _ in range(col_span - 1))
                nested_blocks.extend(child_nested_blocks)
                has_nested_descendants = has_nested_descendants or bool(
                    child_nested_blocks
                )

                if tc_pr is not None:
                    v_merge_state = self._get_vmerge_state(tc_pr)
                    cell_locator: dict[str, int | str] = {
                        "row_index": row_idx,
                        "col_index": col_idx,
                        "col_span": col_span,
                    }
                    if v_merge_state:
                        cell_locator["v_merge"] = v_merge_state
                    cell_locators.append(cell_locator)
                    if v_merge_state == "restart":
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
                    elif v_merge_state is None and col_span > 1:
                        merged_cells.append(
                            MergedCell(
                                row=row_idx,
                                col=col_idx,
                                row_span=1,
                                col_span=col_span,
                            )
                        )

                    cell_fmt = self._parse_cell_format(tc_pr, tc_elem)
                    if cell_fmt:
                        cell_formats[f"{row_idx}:{col_idx}"] = cell_fmt
                else:
                    cell_locators.append(
                        {
                            "row_index": row_idx,
                            "col_index": col_idx,
                            "col_span": col_span,
                        }
                    )

            rows_data.append(row_cells)

        md_table = self._rows_to_md_table(rows_data)
        raw_xml_ref = None
        if has_nested_descendants or parent_cell is not None:
            raw_xml_ref = f"parts/nested_table_{block_id}.xml"
            xml_path = parts_dir / f"nested_table_{block_id}.xml"
            xml_path.write_bytes(etree.tostring(tbl_elem, xml_declaration=True))

        metadata: dict[str, object] = self._docx_locator_metadata(
            source_part=source_part,
            source_story=source_story,
            source_element="w:tbl",
            table_index=table_index,
            source_order=source_order,
            parent_table_id=parent_table_id,
            parent_cell=parent_cell,
            sdt_index=sdt_index,
            text=md_table,
            extra={
                "table_index_scope": "parent_cell"
                if parent_table_id is not None
                else "story",
                "row_count": len(rows_data),
                "column_count": max((len(row) for row in rows_data), default=0),
                "cell_locators": cell_locators,
            },
        )
        if parent_table_id is not None:
            metadata["parent_table_id"] = parent_table_id
        if has_nested_descendants:
            metadata["contains_nested_tables"] = True

        block = DfmBlock(
            id=block_id,
            block_type=DfmBlockType.TABLE,
            content=md_table,
            table_style=table_style,
            col_widths=col_widths,
            merged_cells=merged_cells,
            cell_formats=cell_formats,
            is_nested=has_nested_descendants or parent_cell is not None,
            parent_cell=parent_cell,
            raw_xml_ref=raw_xml_ref,
            metadata=metadata,
        )
        return block, nested_blocks

    def _extract_cell_content(
        self,
        tc_elem: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        parts_dir: Path,
        *,
        parent_cell: str,
        parent_table_id: str,
        source_part: str,
        source_story: str,
        table_index: int | None = None,
        sdt_index: int | None = None,
    ) -> tuple[str, list[DfmBlock]]:
        """Extract direct cell content while preserving nested table boundaries."""
        segments: list[str] = []
        nested_blocks: list[DfmBlock] = []
        nested_table_index = 0

        for child in tc_elem:
            tag = etree.QName(child.tag).localname
            if tag == "tcPr":
                continue
            if tag == "p":
                segments.append(self._get_paragraph_text(child))
                continue
            if tag == "tbl":
                nested_block, child_nested_blocks = self._build_table_block(
                    child,
                    ir,
                    rels,
                    assets_dir,
                    parts_dir,
                    source_part=source_part,
                    source_story=source_story,
                    table_index=nested_table_index,
                    parent_cell=parent_cell,
                    parent_table_id=parent_table_id,
                    sdt_index=sdt_index,
                )
                nested_table_index += 1
                nested_blocks.append(nested_block)
                nested_blocks.extend(child_nested_blocks)
                segments.append(self._nested_table_marker(nested_block.id))

        while segments and not segments[-1]:
            segments.pop()

        return "\n".join(segments), nested_blocks

    def _parse_drawing(
        self,
        drawing: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        *,
        metadata: dict[str, object] | None = None,
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
                self._parse_chart(
                    target,
                    ir,
                    rels,
                    assets_dir,
                    width_cm,
                    height_cm,
                    metadata=metadata,
                )
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
                metadata=metadata or {},
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
        *,
        metadata: dict[str, object] | None = None,
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
                metadata=metadata or {},
            )
        )

    def _parse_field_paragraph(
        self,
        p_elem: etree._Element,
        ir: DocxIR,
        *,
        metadata: dict[str, object] | None = None,
    ) -> None:
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
                    metadata=metadata or {},
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
                    metadata=metadata or {},
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
                    metadata=metadata or {},
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
                    metadata=metadata or {},
                )
            )

    def _parse_sdt(
        self,
        sdt_elem: etree._Element,
        ir: DocxIR,
        rels: dict[str, dict[str, str]],
        assets_dir: Path,
        parts_dir: Path,
        *,
        source_part: str = "word/document.xml",
        source_story: str = "body",
        sdt_index: int | None = None,
        source_order: int | None = None,
    ) -> None:
        """Parse a structured document tag (<w:sdt>), often used for TOC."""
        sdt_metadata = self._docx_locator_metadata(
            source_part=source_part,
            source_story=source_story,
            source_element="w:sdt",
            sdt_index=sdt_index,
            source_order=source_order,
            text=self._get_all_text(sdt_elem),
        )
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
                            metadata=sdt_metadata,
                        )
                    )
                    return

        # Otherwise, parse content normally
        sdt_content = sdt_elem.find(f"{{{NS['w']}}}sdtContent")
        if sdt_content is not None:
            paragraph_index = 0
            table_index = 0
            for child_order, child in enumerate(sdt_content):
                tag = etree.QName(child.tag).localname
                if tag == "p":
                    self._parse_paragraph(
                        child,
                        ir,
                        rels,
                        assets_dir,
                        source_part=source_part,
                        source_story=source_story,
                        paragraph_index=paragraph_index,
                        source_order=child_order,
                        sdt_index=sdt_index,
                    )
                    paragraph_index += 1
                elif tag == "tbl":
                    self._parse_table(
                        child,
                        ir,
                        rels,
                        assets_dir,
                        parts_dir,
                        source_part=source_part,
                        source_story=source_story,
                        table_index=table_index,
                        source_order=child_order,
                        sdt_index=sdt_index,
                    )
                    table_index += 1

    def _parse_footnotes(self, zf: ZipFile, ir: DocxIR) -> None:
        """Parse word/footnotes.xml."""
        if "word/footnotes.xml" not in zf.namelist():
            return

        fn_xml = zf.read("word/footnotes.xml")
        tree = etree.fromstring(fn_xml)

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
            paragraphs = footnote.findall(f"{{{NS['w']}}}p")
            for p in paragraphs:
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
                        metadata=self._docx_locator_metadata(
                            source_part="word/footnotes.xml",
                            source_story="footnote",
                            source_element="w:footnote",
                            text=text,
                            extra={
                                "footnote_id": fn_id,
                                "paragraph_count": len(paragraphs),
                            },
                        ),
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
                tree = etree.fromstring(data)
                preview = self._get_all_text(tree)
                paragraphs = tree.findall(f".//{{{NS['w']}}}p")

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
                        metadata=self._docx_locator_metadata(
                            source_part=name,
                            source_story="header",
                            source_element="w:hdr",
                            text=preview,
                            extra={
                                "hdr_ftr_type": hdr_type,
                                "paragraph_count": len(paragraphs),
                            },
                        ),
                    )
                )

            elif name.startswith("word/footer") and name.endswith(".xml"):
                data = zf.read(name)
                safe_name = Path(name).name
                (parts_dir / safe_name).write_bytes(data)

                preview_tree = etree.fromstring(data)
                preview = self._get_all_text(preview_tree)
                paragraphs = preview_tree.findall(f".//{{{NS['w']}}}p")

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
                        metadata=self._docx_locator_metadata(
                            source_part=name,
                            source_story="footer",
                            source_element="w:ftr",
                            text=preview,
                            extra={
                                "hdr_ftr_type": ftr_type,
                                "paragraph_count": len(paragraphs),
                            },
                        ),
                    )
                )

    # ========================================================================
    # Private: Locator metadata helpers
    # ========================================================================

    def _docx_locator_metadata(
        self,
        *,
        source_part: str,
        source_story: str,
        source_element: str,
        paragraph_index: int | None = None,
        table_index: int | None = None,
        source_order: int | None = None,
        parent_table_id: str | None = None,
        parent_cell: str | None = None,
        sdt_index: int | None = None,
        runs: list[FormatRun] | None = None,
        text: str | None = None,
        extra: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Build a stable, lightweight locator for DOCX-origin DFM blocks."""
        metadata: dict[str, object] = {
            "locator_version": _DOCX_LOCATOR_VERSION,
            "source_part": source_part,
            "source_story": source_story,
            "source_element": source_element,
        }
        if source_order is not None:
            metadata["source_order"] = source_order
        if paragraph_index is not None:
            metadata["paragraph_index"] = paragraph_index
        if table_index is not None:
            metadata["table_index"] = table_index
        if parent_table_id is not None:
            metadata["parent_table_id"] = parent_table_id
        if parent_cell is not None:
            metadata["parent_cell"] = parent_cell
        if sdt_index is not None:
            metadata["sdt_index"] = sdt_index

        if runs is not None:
            text = "".join(run.text for run in runs)
            metadata["run_count"] = len(runs)
            metadata["run_ranges"] = self._docx_run_ranges(runs)

        if text is not None:
            metadata.update(self._docx_text_locator(text))

        if extra:
            metadata.update(
                {key: value for key, value in extra.items() if value is not None}
            )
        return metadata

    @staticmethod
    def _docx_text_locator(text: str) -> dict[str, object]:
        return {
            "char_range": [0, len(text)],
            "byte_range": [0, len(text.encode("utf-8"))],
            "text_sha256": f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}",
        }

    @staticmethod
    def _docx_run_ranges(runs: list[FormatRun]) -> list[dict[str, object]]:
        ranges: list[dict[str, object]] = []
        char_cursor = 0
        byte_cursor = 0
        for run_index, run in enumerate(runs):
            text = run.text
            char_end = char_cursor + len(text)
            byte_len = len(text.encode("utf-8"))
            byte_end = byte_cursor + byte_len
            ranges.append(
                {
                    "run_index": run_index,
                    "char_start": char_cursor,
                    "char_end": char_end,
                    "byte_start": byte_cursor,
                    "byte_end": byte_end,
                    "text_sha256": f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}",
                }
            )
            char_cursor = char_end
            byte_cursor = byte_end
        return ranges

    # ========================================================================
    # Private: XML text extraction helpers
    # ========================================================================

    def _add_revision_blocks(
        self,
        elem: etree._Element,
        ir: DocxIR,
        *,
        scope: str,
        source_block_id: str | None = None,
        context_text: str | None = None,
        source_metadata: dict[str, object] | None = None,
    ) -> None:
        """Expose Word tracked changes as read-only DFM revision blocks."""
        fallback_context = context_text
        if fallback_context is None and self._local_name(elem) == "p":
            fallback_context = self._get_paragraph_text(elem)

        for revision_elem in self._iter_revision_elements(elem):
            revision_tag = self._local_name(revision_elem)
            revision_type = _REVISION_TAG_TYPES[revision_tag]
            revision_text = self._get_revision_text(revision_elem).strip()
            if not revision_text:
                revision_text = (fallback_context or "").strip()
            if not revision_text:
                revision_text = "[tracked format change]"

            metadata: dict[str, object] = dict(source_metadata or {})
            metadata.update(
                {
                    "source_tag": f"w:{revision_tag}",
                    "scope": scope,
                    "visible_in_current_text": revision_tag
                    not in _NON_VISIBLE_REVISION_TAGS,
                }
            )
            metadata.update(self._docx_text_locator(revision_text))
            revision_id = revision_elem.get(f"{{{NS['w']}}}id")
            if revision_id:
                metadata["revision_id"] = revision_id
            if source_block_id:
                metadata["source_block_id"] = source_block_id

            ir.add_block(
                DfmBlock(
                    id=ir.next_block_id(DfmBlockType.REVISION),
                    block_type=DfmBlockType.REVISION,
                    content=revision_text,
                    revision_type=revision_type,
                    revision_author=revision_elem.get(f"{{{NS['w']}}}author"),
                    revision_date=revision_elem.get(f"{{{NS['w']}}}date"),
                    metadata=metadata,
                )
            )

    def _iter_revision_elements(self, elem: etree._Element) -> list[etree._Element]:
        """Return top-level tracked-change elements within an XML subtree."""
        revisions = []
        for candidate in elem.iter():
            if candidate is elem:
                continue
            tag = self._local_name(candidate)
            if tag not in _REVISION_TAG_TYPES:
                continue
            if self._has_revision_ancestor(candidate, elem):
                continue
            revisions.append(candidate)
        return revisions

    def _has_revision_ancestor(
        self,
        elem: etree._Element,
        stop: etree._Element,
    ) -> bool:
        parent = elem.getparent()
        while parent is not None and parent is not stop:
            if self._local_name(parent) in _REVISION_TAG_TYPES:
                return True
            parent = parent.getparent()
        return False

    def _get_revision_text(self, revision_elem: etree._Element) -> str:
        """Extract inserted/deleted revision text, including w:delText nodes."""
        parts: list[str] = []
        for child in revision_elem.iter():
            tag = self._local_name(child)
            if tag in {"t", "delText"} and child.text:
                parts.append(child.text)
            elif tag == "tab":
                parts.append("\t")
            elif tag == "br":
                br_type = child.get(f"{{{NS['w']}}}type")
                if br_type != "page":
                    parts.append("\n")
        return "".join(parts)

    def _get_paragraph_text(self, p_elem: etree._Element) -> str:
        """Get concatenated text from a paragraph element."""
        return "".join(run.text for run in self._parse_runs(p_elem))

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
            if self._has_ancestor_with_local_name(t_elem, _NON_VISIBLE_REVISION_TAGS):
                continue
            if t_elem.text:
                parts.append(t_elem.text)
        return " ".join(parts)

    @staticmethod
    def _local_name(elem: etree._Element) -> str:
        if not isinstance(elem.tag, str):
            return ""
        return str(etree.QName(elem.tag).localname)

    def _has_ancestor_with_local_name(
        self,
        elem: etree._Element,
        names: set[str],
    ) -> bool:
        parent = elem.getparent()
        while parent is not None:
            if self._local_name(parent) in names:
                return True
            parent = parent.getparent()
        return False

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
                parsed = _safe_int(val)
                if parsed is not None:
                    return parsed

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
                parsed = _safe_int(val)
                if parsed is not None:
                    return parsed
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
                parsed = _safe_int(val)
                if parsed is not None:
                    return parsed
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

    def _get_row_grid_offset(self, tr_elem: etree._Element) -> int:
        """Return the logical column offset declared by w:gridBefore."""
        tr_pr = tr_elem.find(f"{{{NS['w']}}}trPr")
        if tr_pr is None:
            return 0
        grid_before = tr_pr.find(f"{{{NS['w']}}}gridBefore")
        if grid_before is None:
            return 0
        return _safe_int(grid_before.get(f"{{{NS['w']}}}val"), default=0) or 0

    def _get_cell_grid_span(self, tc_pr: etree._Element | None) -> int:
        """Return the logical column span for a table cell."""
        if tc_pr is None:
            return 1
        grid_span = tc_pr.find(f"{{{NS['w']}}}gridSpan")
        if grid_span is None:
            return 1
        return max(_safe_int(grid_span.get(f"{{{NS['w']}}}val"), default=1) or 1, 1)

    def _get_vmerge_state(self, tc_pr: etree._Element | None) -> str | None:
        """Return restart/continue for vertical merge cells."""
        if tc_pr is None:
            return None
        v_merge = tc_pr.find(f"{{{NS['w']}}}vMerge")
        if v_merge is None:
            return None
        return v_merge.get(f"{{{NS['w']}}}val") or "continue"

    def _iter_row_cells(
        self,
        tr_elem: etree._Element,
    ) -> list[tuple[int, etree._Element, int, etree._Element | None]]:
        """Yield physical cells with their logical table-grid column."""
        logical_col = self._get_row_grid_offset(tr_elem)
        cells: list[tuple[int, etree._Element, int, etree._Element | None]] = []
        for tc_elem in tr_elem.findall(f"{{{NS['w']}}}tc"):
            tc_pr = tc_elem.find(f"{{{NS['w']}}}tcPr")
            col_span = self._get_cell_grid_span(tc_pr)
            cells.append((logical_col, tc_elem, col_span, tc_pr))
            logical_col += col_span
        return cells

    def _find_row_cell(
        self,
        tr_elem: etree._Element,
        logical_col: int,
    ) -> tuple[int, etree._Element, int, etree._Element | None] | None:
        """Find the cell that starts at a logical column."""
        for cell_info in self._iter_row_cells(tr_elem):
            if cell_info[0] == logical_col:
                return cell_info
        return None

    def _count_vmerge(
        self, tbl_elem: etree._Element, start_row: int, col_idx: int
    ) -> int:
        """Count how many rows are vertically merged starting from start_row."""
        rows = tbl_elem.findall(f"{{{NS['w']}}}tr")
        span = 1
        for row_idx in range(start_row + 1, len(rows)):
            cell_info = self._find_row_cell(rows[row_idx], col_idx)
            if cell_info is None:
                break
            _, _tc_elem, _col_span, tc_pr = cell_info
            if self._get_vmerge_state(tc_pr) == "continue":
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

        # Clean cell text (escape table delimiters/newlines for markdown, strip)
        for row in rows:
            for i, cell in enumerate(row):
                row[i] = (
                    cell.replace("\\", "\\\\")
                    .replace("|", "\\|")
                    .replace("\n", "<br>")
                    .strip()
                )

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

    @staticmethod
    def _nested_table_marker(block_id: str) -> str:
        """Return the inline placeholder used for nested tables inside cell text."""
        return f"[[NESTED_TABLE:{block_id}]]"

    @classmethod
    def _nested_table_marker_match(cls, value: str) -> re.Match[str] | None:
        """Match a nested-table placeholder token."""
        return re.fullmatch(r"\[\[NESTED_TABLE:(t\d{3})\]\]", value.strip())

    # ========================================================================
    # Private: Rebuild docx from IR
    # ========================================================================

    def _update_document_xml(
        self,
        docx_path: Path,
        ir: DocxIR,
        changed_block_ids: set[str] | None = None,
        *,
        original_ir: DocxIR | None = None,
        track_changes: bool = False,
        revision_author: str = "Asset-Aware MCP",
    ) -> None:
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
                        modified_xml = self._apply_text_changes(
                            doc_xml,
                            ir,
                            changed_block_ids,
                            original_ir=original_ir,
                            track_changes=track_changes,
                            revision_author=revision_author,
                        )
                        zout.writestr(item, modified_xml)
                    elif item.filename == "word/settings.xml" and track_changes:
                        settings_xml = zin.read(item.filename)
                        zout.writestr(item, self._enable_track_revisions(settings_xml))
                    else:
                        zout.writestr(item, zin.read(item.filename))

        # Replace original with modified
        temp_path.replace(docx_path)

    def _apply_text_changes(
        self,
        doc_xml: bytes,
        ir: DocxIR,
        changed_block_ids: set[str] | None = None,
        *,
        original_ir: DocxIR | None = None,
        track_changes: bool = False,
        revision_author: str = "Asset-Aware MCP",
    ) -> bytes:
        """
        Apply text changes from IR blocks back to document.xml.

        Walks paragraphs and tables in the same order as original parsing,
        matching each to the corresponding IR block by index position.
        """
        tree = etree.fromstring(doc_xml)
        body = tree.find(f".//{{{NS['w']}}}body")
        if body is None:
            return doc_xml

        original_blocks = (
            {block.id: block for block in original_ir.blocks} if original_ir else {}
        )
        revision_context = (
            _TrackChangeContext(
                author=revision_author or "Asset-Aware MCP",
                date=self._revision_timestamp(),
                next_id=self._max_revision_id(tree) + 1,
            )
            if track_changes
            else None
        )

        top_level_blocks = [
            block
            for block in ir.blocks
            if not (
                block.block_type == DfmBlockType.TABLE and block.parent_cell is not None
            )
            and block.block_type != DfmBlockType.REVISION
        ]
        block_idx = 0
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]] = {}
        for block in ir.blocks:
            if block.block_type != DfmBlockType.TABLE or block.parent_cell is None:
                continue
            parent_id = str(block.metadata.get("parent_table_id", ""))
            if not parent_id:
                continue
            nested_blocks_by_parent.setdefault(parent_id, {}).setdefault(
                block.parent_cell,
                [],
            ).append(block)

        for element in body:
            tag = etree.QName(element.tag).localname

            if tag == "p":
                if block_idx < len(top_level_blocks):
                    block = top_level_blocks[block_idx]
                    if block.block_type in (
                        DfmBlockType.PARAGRAPH,
                        DfmBlockType.HEADING,
                        DfmBlockType.LIST_ITEM,
                        DfmBlockType.FORMAT,
                        DfmBlockType.CAPTION,
                    ) and (changed_block_ids is None or block.id in changed_block_ids):
                        original_block = original_blocks.get(block.id)
                        original_text = (
                            self._block_write_text(original_block)
                            if original_block is not None
                            else self._get_paragraph_text(element)
                        )
                        self._update_paragraph_text(
                            element,
                            block,
                            revision_context=revision_context,
                            original_text=original_text,
                        )
                    block_idx += 1
            elif tag == "tbl" and block_idx < len(top_level_blocks):
                block = top_level_blocks[block_idx]
                if block.block_type == DfmBlockType.TABLE:
                    should_update_self = (
                        changed_block_ids is None or block.id in changed_block_ids
                    )
                    has_nested_updates = self._table_has_changed_nested_descendant(
                        block.id,
                        nested_blocks_by_parent,
                        changed_block_ids,
                    )
                    if should_update_self or has_nested_updates:
                        self._update_table_text(
                            element,
                            block,
                            nested_blocks_by_parent,
                            changed_block_ids,
                            update_direct_text=should_update_self,
                            revision_context=revision_context,
                        )
                block_idx += 1

        return bytes(
            etree.tostring(
                tree, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        )

    def _update_paragraph_text(
        self,
        p_elem: etree._Element,
        block: DfmBlock,
        *,
        revision_context: _TrackChangeContext | None = None,
        original_text: str | None = None,
    ) -> None:
        """Update text content of a paragraph element from a DfmBlock."""
        if revision_context is not None:
            desired_text = self._block_write_text(block)
            baseline_text = (
                original_text
                if original_text is not None
                else self._get_paragraph_text(p_elem)
            )
            if baseline_text != desired_text:
                self._replace_paragraph_with_tracked_change(
                    p_elem,
                    baseline_text,
                    desired_text,
                    revision_context,
                    new_runs=block.runs,
                )
                return

        runs = self._iter_text_runs(p_elem)
        if not runs:
            return

        if block.runs:
            runs_text = "".join(run.text for run in block.runs)
            text_segments = (
                [run.text for run in block.runs]
                if runs_text == block.content
                else [block.content]
            )
        else:
            text_segments = [block.content]
        if not text_segments:
            text_segments = [""]

        self._set_run_texts(runs, text_segments)

    @staticmethod
    def _block_write_text(block: DfmBlock) -> str:
        """Return the exact visible text intended for DOCX write-back."""
        return block.plain_text if block.runs else block.content

    def _update_table_text(
        self,
        tbl_elem: etree._Element,
        block: DfmBlock,
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]],
        changed_block_ids: set[str] | None = None,
        *,
        update_direct_text: bool = True,
        revision_context: _TrackChangeContext | None = None,
    ) -> None:
        """Update text content of table cells from a DfmBlock."""
        md_rows = self._parse_md_table(block.content)
        if not md_rows:
            return

        xml_rows = tbl_elem.findall(f"{{{NS['w']}}}tr")

        for row_idx, (xml_row, md_row) in enumerate(
            zip(xml_rows, md_rows, strict=False)
        ):
            for col_idx, cell, _col_span, tc_pr in self._iter_row_cells(xml_row):
                if col_idx >= len(md_row):
                    continue
                if self._get_vmerge_state(tc_pr) == "continue":
                    continue
                md_cell = md_row[col_idx]
                nested_blocks = nested_blocks_by_parent.get(block.id, {}).get(
                    f"{row_idx}:{col_idx}",
                    [],
                )
                desired_text = md_cell.strip()
                current_text = self._get_table_cell_content_for_compare(
                    cell,
                    nested_blocks,
                ).strip()
                should_update_direct_text = (
                    update_direct_text and desired_text != current_text
                )
                self._update_table_cell(
                    cell,
                    desired_text,
                    nested_blocks,
                    nested_blocks_by_parent,
                    changed_block_ids,
                    update_direct_text=should_update_direct_text,
                    revision_context=revision_context,
                )

    def _get_table_cell_content_for_compare(
        self,
        cell: etree._Element,
        nested_blocks: list[DfmBlock],
    ) -> str:
        """Return direct cell content using nested-table markers for comparison."""
        segments: list[str] = []
        nested_iter = iter(nested_blocks)
        for child in cell:
            tag = etree.QName(child.tag).localname
            if tag == "tcPr":
                continue
            if tag == "p":
                segments.append(self._get_paragraph_text(child))
                continue
            if tag == "tbl":
                nested_block = next(nested_iter, None)
                if nested_block is not None:
                    segments.append(self._nested_table_marker(nested_block.id))

        while segments and not segments[-1]:
            segments.pop()
        return "\n".join(segments)

    def _update_table_cell(
        self,
        cell: etree._Element,
        cell_text: str,
        nested_blocks: list[DfmBlock],
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]],
        changed_block_ids: set[str] | None = None,
        *,
        update_direct_text: bool = True,
        revision_context: _TrackChangeContext | None = None,
    ) -> None:
        """Update a table cell while preserving nested table boundaries."""
        desired_items = cell_text.split("\n") if cell_text else []
        direct_children = [
            child for child in cell if etree.QName(child.tag).localname != "tcPr"
        ]
        last_paragraph: etree._Element | None = None
        nested_iter = iter(nested_blocks)

        for child in direct_children:
            tag = etree.QName(child.tag).localname
            if tag == "p":
                next_text = self._get_paragraph_text(child)
                if update_direct_text:
                    next_text = ""
                    if desired_items and not self._nested_table_marker_match(
                        desired_items[0]
                    ):
                        next_text = desired_items.pop(0)
                    self._set_paragraph_plain_text(
                        child,
                        next_text,
                        revision_context=revision_context,
                    )
                last_paragraph = child
                continue

            if tag != "tbl":
                continue

            nested_block = next(nested_iter, None)
            if desired_items and self._nested_table_marker_match(desired_items[0]):
                desired_items.pop(0)
            if nested_block is None:
                continue
            if changed_block_ids is None or nested_block.id in changed_block_ids:
                self._update_table_text(
                    child,
                    nested_block,
                    nested_blocks_by_parent,
                    changed_block_ids,
                    revision_context=revision_context,
                )

        leftover_text = [
            item for item in desired_items if not self._nested_table_marker_match(item)
        ]
        if update_direct_text and leftover_text and last_paragraph is not None:
            current_text = self._get_paragraph_text(last_paragraph)
            suffix = "\n".join(leftover_text)
            merged = f"{current_text}\n{suffix}" if current_text else suffix
            self._set_paragraph_plain_text(
                last_paragraph,
                merged,
                revision_context=revision_context,
            )

    def _table_has_changed_nested_descendant(
        self,
        table_id: str,
        nested_blocks_by_parent: dict[str, dict[str, list[DfmBlock]]],
        changed_block_ids: set[str] | None,
    ) -> bool:
        """Return whether a table has any changed nested descendant blocks."""
        if changed_block_ids is None:
            return True

        child_groups = nested_blocks_by_parent.get(table_id, {})
        for child_blocks in child_groups.values():
            for child_block in child_blocks:
                if child_block.id in changed_block_ids:
                    return True
                if self._table_has_changed_nested_descendant(
                    child_block.id,
                    nested_blocks_by_parent,
                    changed_block_ids,
                ):
                    return True
        return False

    def _set_paragraph_plain_text(
        self,
        p_elem: etree._Element,
        text: str,
        *,
        revision_context: _TrackChangeContext | None = None,
    ) -> None:
        """Replace the visible text in a paragraph while preserving existing runs."""
        if revision_context is not None:
            original_text = self._get_paragraph_text(p_elem)
            if original_text != text:
                self._replace_paragraph_with_tracked_change(
                    p_elem,
                    original_text,
                    text,
                    revision_context,
                )
                return

        runs = self._iter_text_runs(p_elem)
        if not runs:
            return
        self._set_run_texts(runs, [text])

    def _replace_paragraph_with_tracked_change(
        self,
        p_elem: etree._Element,
        old_text: str,
        new_text: str,
        revision_context: _TrackChangeContext,
        *,
        new_runs: list[FormatRun] | None = None,
    ) -> None:
        """Rewrite a paragraph's textual content as native Word revisions."""
        old_spans = self._paragraph_run_style_spans(p_elem)
        new_spans = self._format_run_style_spans(new_runs or [])
        target = self._track_change_rewrite_target(p_elem)
        self._remove_textual_children(target)

        for op, text, old_start, old_end, new_start, new_end in self._diff_text_ops(
            old_text, new_text
        ):
            if not text:
                continue
            if op == "equal":
                self._append_text_with_style_spans(
                    target,
                    text,
                    old_spans,
                    old_start,
                    old_end,
                )
            elif op == "delete":
                self._append_revision_text_with_style_spans(
                    target,
                    "del",
                    text,
                    revision_context,
                    old_spans,
                    old_start,
                    old_end,
                )
            elif op == "insert":
                spans = new_spans or old_spans
                span_start = new_start if new_spans else old_start
                span_end = new_end if new_spans else old_start
                self._append_revision_text_with_style_spans(
                    target,
                    "ins",
                    text,
                    revision_context,
                    spans,
                    span_start,
                    span_end,
                )

    def _diff_text_chunks(self, old_text: str, new_text: str) -> list[tuple[str, str]]:
        """Return stable token-level chunks for Word revision emission."""
        return [
            (op, text)
            for op, text, _old_start, _old_end, _new_start, _new_end in self._diff_text_ops(
                old_text, new_text
            )
        ]

    def _diff_text_ops(
        self, old_text: str, new_text: str
    ) -> list[tuple[str, str, int, int, int, int]]:
        """Return token-level diff ops with source offsets for styling/provenance."""
        old_tokens = self._tokenize_diff_text(old_text)
        new_tokens = self._tokenize_diff_text(new_text)
        old_offsets = self._token_offsets(old_tokens)
        new_offsets = self._token_offsets(new_tokens)
        matcher = SequenceMatcher(None, old_tokens, new_tokens, autojunk=False)

        chunks: list[tuple[str, str, int, int, int, int]] = []
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            old_char_start = old_offsets[old_start]
            old_char_end = old_offsets[old_end]
            new_char_start = new_offsets[new_start]
            new_char_end = new_offsets[new_end]
            if tag == "equal":
                chunks.append(
                    (
                        "equal",
                        "".join(new_tokens[new_start:new_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_end,
                    )
                )
            elif tag == "delete":
                chunks.append(
                    (
                        "delete",
                        "".join(old_tokens[old_start:old_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_end,
                    )
                )
            elif tag == "insert":
                chunks.append(
                    (
                        "insert",
                        "".join(new_tokens[new_start:new_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_end,
                    )
                )
            else:
                chunks.append(
                    (
                        "delete",
                        "".join(old_tokens[old_start:old_end]),
                        old_char_start,
                        old_char_end,
                        new_char_start,
                        new_char_start,
                    )
                )
                chunks.append(
                    (
                        "insert",
                        "".join(new_tokens[new_start:new_end]),
                        old_char_start,
                        old_char_start,
                        new_char_start,
                        new_char_end,
                    )
                )
        return chunks

    @staticmethod
    def _tokenize_diff_text(text: str) -> list[str]:
        """Tokenize while preserving whitespace so diff chunks quote exactly."""
        if not text:
            return []
        return _DIFF_TOKEN_RE.findall(text)

    @staticmethod
    def _token_offsets(tokens: list[str]) -> list[int]:
        offsets = [0]
        cursor = 0
        for token in tokens:
            cursor += len(token)
            offsets.append(cursor)
        return offsets

    def _track_change_rewrite_target(self, p_elem: etree._Element) -> etree._Element:
        """Preserve a single hyperlink/SDT wrapper when all text lives inside it."""
        textual_children = [
            child
            for child in p_elem
            if self._local_name(child) != "pPr"
            and self._is_textual_paragraph_child(child)
        ]
        if len(textual_children) != 1:
            return p_elem

        child = textual_children[0]
        tag = self._local_name(child)
        if tag == "hyperlink":
            return child
        if tag == "sdt":
            content = child.find(f"{{{NS['w']}}}sdtContent")
            if content is not None:
                return content
        return p_elem

    def _paragraph_run_style_spans(self, p_elem: etree._Element) -> list[_RunStyleSpan]:
        spans: list[_RunStyleSpan] = []
        cursor = 0
        for r_elem in self._iter_text_runs(p_elem):
            text = self._run_visible_text(r_elem)
            if not text:
                continue
            rpr = r_elem.find(f"{{{NS['w']}}}rPr")
            spans.append(
                _RunStyleSpan(
                    start=cursor,
                    end=cursor + len(text),
                    rpr=self._clone_rpr(rpr),
                )
            )
            cursor += len(text)
        return spans

    def _format_run_style_spans(self, runs: list[FormatRun]) -> list[_RunStyleSpan]:
        spans: list[_RunStyleSpan] = []
        cursor = 0
        for run in runs:
            if not run.text:
                continue
            spans.append(
                _RunStyleSpan(
                    start=cursor,
                    end=cursor + len(run.text),
                    rpr=self._format_run_to_rpr(run),
                )
            )
            cursor += len(run.text)
        return spans

    def _append_revision_text_with_style_spans(
        self,
        parent: etree._Element,
        tag: str,
        text: str,
        revision_context: _TrackChangeContext,
        spans: list[_RunStyleSpan],
        source_start: int,
        source_end: int,
    ) -> None:
        revision = etree.SubElement(parent, f"{{{NS['w']}}}{tag}")
        revision.set(f"{{{NS['w']}}}id", revision_context.take_id())
        revision.set(f"{{{NS['w']}}}author", revision_context.author)
        revision.set(f"{{{NS['w']}}}date", revision_context.date)
        self._append_text_with_style_spans(
            revision,
            text,
            spans,
            source_start,
            source_end,
            text_tag="delText" if tag == "del" else "t",
        )

    def _append_text_with_style_spans(
        self,
        parent: etree._Element,
        text: str,
        spans: list[_RunStyleSpan],
        source_start: int,
        source_end: int,
        *,
        text_tag: str = "t",
    ) -> None:
        if not text:
            return
        if not spans or source_end <= source_start:
            self._append_text_run(
                parent,
                text,
                text_tag=text_tag,
                rpr_template=self._style_at_offset(spans, source_start),
            )
            return

        emitted_until = 0
        for span in spans:
            overlap_start = max(source_start, span.start)
            overlap_end = min(source_end, span.end)
            if overlap_end <= overlap_start:
                continue

            chunk_start = overlap_start - source_start
            chunk_end = overlap_end - source_start
            if chunk_start > emitted_until:
                self._append_text_run(
                    parent,
                    text[emitted_until:chunk_start],
                    text_tag=text_tag,
                    rpr_template=self._style_at_offset(
                        spans, source_start + emitted_until
                    ),
                )
            self._append_text_run(
                parent,
                text[chunk_start:chunk_end],
                text_tag=text_tag,
                rpr_template=span.rpr,
            )
            emitted_until = chunk_end

        if emitted_until < len(text):
            self._append_text_run(
                parent,
                text[emitted_until:],
                text_tag=text_tag,
                rpr_template=self._style_at_offset(spans, source_start + emitted_until),
            )

    def _style_at_offset(
        self, spans: list[_RunStyleSpan], offset: int
    ) -> etree._Element | None:
        if not spans:
            return None
        previous = spans[0]
        for span in spans:
            if span.start <= offset < span.end:
                return self._clone_rpr(span.rpr)
            if span.end <= offset:
                previous = span
        return self._clone_rpr(previous.rpr)

    def _run_visible_text(self, r_elem: etree._Element) -> str:
        parts: list[str] = []
        for child in r_elem:
            tag = self._local_name(child)
            if tag in {"t", "delText"} and child.text:
                parts.append(child.text)
            elif tag == "tab":
                parts.append("\t")
            elif tag == "br":
                br_type = child.get(f"{{{NS['w']}}}type")
                if br_type != "page":
                    parts.append("\n")
        return "".join(parts)

    def _format_run_to_rpr(self, run: FormatRun) -> etree._Element | None:
        rpr = etree.Element(f"{{{NS['w']}}}rPr")
        if run.bold:
            etree.SubElement(rpr, f"{{{NS['w']}}}b")
        if run.italic:
            etree.SubElement(rpr, f"{{{NS['w']}}}i")
        if run.underline:
            etree.SubElement(rpr, f"{{{NS['w']}}}u", {f"{{{NS['w']}}}val": "single"})
        if run.font_name:
            etree.SubElement(
                rpr,
                f"{{{NS['w']}}}rFonts",
                {
                    f"{{{NS['w']}}}ascii": run.font_name,
                    f"{{{NS['w']}}}hAnsi": run.font_name,
                },
            )
        if run.font_size:
            etree.SubElement(
                rpr,
                f"{{{NS['w']}}}sz",
                {f"{{{NS['w']}}}val": str(int(run.font_size / HALF_POINTS_TO_PT))},
            )
        if run.color:
            etree.SubElement(
                rpr,
                f"{{{NS['w']}}}color",
                {f"{{{NS['w']}}}val": run.color.lstrip("#")},
            )
        return rpr if len(rpr) > 0 else None

    def _clone_rpr(self, rpr: etree._Element | None) -> etree._Element | None:
        return etree.fromstring(etree.tostring(rpr)) if rpr is not None else None

    def _remove_textual_children(self, p_elem: etree._Element) -> None:
        """Remove paragraph text containers while preserving non-textual anchors."""
        for child in list(p_elem):
            if self._local_name(child) == "pPr":
                continue
            if self._is_textual_paragraph_child(child):
                p_elem.remove(child)

    def _is_textual_paragraph_child(self, elem: etree._Element) -> bool:
        tag = self._local_name(elem)
        if tag in {"del", "ins", "moveFrom", "moveTo"}:
            return True
        if tag in {"hyperlink", "sdt"}:
            return self._element_has_textual_content(elem)
        if tag == "r":
            return self._element_has_textual_content(elem)
        return False

    def _element_has_textual_content(self, elem: etree._Element) -> bool:
        text_tags = {"t", "delText", "instrText", "tab", "br"}
        return any(self._local_name(child) in text_tags for child in elem.iter())

    def _append_revision_run(
        self,
        parent: etree._Element,
        tag: str,
        text: str,
        revision_context: _TrackChangeContext,
        *,
        rpr_template: etree._Element | None = None,
    ) -> None:
        revision = etree.SubElement(parent, f"{{{NS['w']}}}{tag}")
        revision.set(f"{{{NS['w']}}}id", revision_context.take_id())
        revision.set(f"{{{NS['w']}}}author", revision_context.author)
        revision.set(f"{{{NS['w']}}}date", revision_context.date)
        self._append_text_run(
            revision,
            text,
            text_tag="delText" if tag == "del" else "t",
            rpr_template=rpr_template,
        )

    def _append_text_run(
        self,
        parent: etree._Element,
        text: str,
        *,
        text_tag: str = "t",
        rpr_template: etree._Element | None = None,
    ) -> None:
        run = etree.SubElement(parent, f"{{{NS['w']}}}r")
        if rpr_template is not None:
            run.append(etree.fromstring(etree.tostring(rpr_template)))
        for part in re.split(r"(\t|\n)", text):
            if not part:
                continue
            if part == "\t":
                etree.SubElement(run, f"{{{NS['w']}}}tab")
                continue
            if part == "\n":
                etree.SubElement(run, f"{{{NS['w']}}}br")
                continue
            text_elem = etree.SubElement(run, f"{{{NS['w']}}}{text_tag}")
            text_elem.text = part
            text_elem.set(_XML_SPACE, "preserve")

    def _iter_text_runs(self, p_elem: etree._Element) -> list[etree._Element]:
        """Return paragraph runs in document order, including hyperlink/SDT runs."""
        runs = []
        for r_elem in p_elem.findall(f".//{{{NS['w']}}}r"):
            if self._has_ancestor_with_local_name(r_elem, _NON_VISIBLE_REVISION_TAGS):
                continue
            runs.append(r_elem)
        return runs

    def _set_run_texts(self, runs: list[etree._Element], segments: list[str]) -> None:
        """Assign visible text across existing XML runs without rewriting structure."""
        normalized_segments = list(segments) if segments else [""]
        for index, r_elem in enumerate(runs):
            t_elem = r_elem.find(f"{{{NS['w']}}}t")
            segment = (
                normalized_segments[index] if index < len(normalized_segments) else ""
            )
            if t_elem is None:
                has_break = r_elem.find(f"{{{NS['w']}}}br") is not None
                if has_break and segment in {"\n", "\r\n"}:
                    continue
                if segment:
                    t_elem = etree.SubElement(r_elem, f"{{{NS['w']}}}t")
                else:
                    continue

            text = segment
            if index == len(runs) - 1 and len(normalized_segments) > len(runs):
                tail = normalized_segments[index:]
                text = "".join(tail)

            t_elem.text = text
            t_elem.set(_XML_SPACE, "preserve")

    @staticmethod
    def _revision_timestamp() -> str:
        """Return an OOXML-compatible UTC timestamp."""
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def _max_revision_id(self, tree: etree._Element) -> int:
        """Find the highest existing Word revision id to avoid collisions."""
        max_id = 0
        for elem in tree.iter():
            if self._local_name(elem) not in _REVISION_TAG_TYPES:
                continue
            revision_id = _safe_int(elem.get(f"{{{NS['w']}}}id"), default=0)
            if revision_id is not None:
                max_id = max(max_id, revision_id)
        return max_id

    def _enable_track_revisions(self, settings_xml: bytes) -> bytes:
        """Ensure Word's settings part records Track Changes as enabled."""
        try:
            tree = etree.fromstring(settings_xml)
        except etree.XMLSyntaxError:
            return settings_xml

        if tree.find(f"{{{NS['w']}}}trackRevisions") is None:
            etree.SubElement(tree, f"{{{NS['w']}}}trackRevisions")
        return bytes(
            etree.tostring(
                tree, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        )

    @staticmethod
    def _parse_md_table(md_table: str) -> list[list[str]]:
        """Parse a markdown pipe table back into rows of cell text."""
        rows = []
        for line in md_table.strip().split("\n"):
            line = line.strip()
            if not line.startswith("|"):
                continue
            # Skip separator row
            if DfmParser._is_md_table_separator_row(line):
                continue
            cells = DfmParser._split_md_table_row(line)
            # Restore escaped newlines (<br> → real newline)
            cells = [c.replace("<br>", "\n") for c in cells]
            rows.append(cells)
        return rows
