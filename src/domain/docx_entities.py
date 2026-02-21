"""
Domain Layer - Docx Entities

Core entities for the DFM (Docx-Flavored Markdown) module.
Implements the Intermediate Representation (IR) for lossless docx ↔ DFM conversion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .docx_value_objects import (
    BLOCK_ID_PREFIXES,
    BreakType,
    DfmBlockType,
    ImageAnchorType,
    OrientationType,
    PageSizeType,
    TableCellAlign,
)

# ============================================================================
# Format Run — Inline text formatting
# ============================================================================


@dataclass
class FormatRun:
    """A contiguous run of text with uniform formatting within a paragraph."""

    text: str
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    superscript: bool = False
    subscript: bool = False
    font_name: str | None = None
    font_size: float | None = None  # in pt
    color: str | None = None  # hex e.g. "#FF0000"
    highlight: str | None = None  # highlight color name
    small_caps: bool = False

    @property
    def is_plain(self) -> bool:
        """Whether this run has no special formatting."""
        return (
            not self.bold
            and not self.italic
            and not self.underline
            and not self.strike
            and not self.superscript
            and not self.subscript
            and self.font_name is None
            and self.font_size is None
            and self.color is None
            and self.highlight is None
            and not self.small_caps
        )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"text": self.text}
        if self.bold:
            d["bold"] = True
        if self.italic:
            d["italic"] = True
        if self.underline:
            d["underline"] = True
        if self.strike:
            d["strike"] = True
        if self.superscript:
            d["superscript"] = True
        if self.subscript:
            d["subscript"] = True
        if self.font_name:
            d["font"] = self.font_name
        if self.font_size:
            d["size"] = self.font_size
        if self.color:
            d["color"] = self.color
        if self.highlight:
            d["highlight"] = self.highlight
        if self.small_caps:
            d["small_caps"] = True
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormatRun:
        return cls(
            text=data.get("text", ""),
            bold=data.get("bold", False),
            italic=data.get("italic", False),
            underline=data.get("underline", False),
            strike=data.get("strike", False),
            superscript=data.get("superscript", False),
            subscript=data.get("subscript", False),
            font_name=data.get("font"),
            font_size=data.get("size"),
            color=data.get("color"),
            highlight=data.get("highlight"),
            small_caps=data.get("small_caps", False),
        )


# ============================================================================
# Merged Cell — Table merge info
# ============================================================================


@dataclass
class MergedCell:
    """Describes a merged cell region in a table."""

    row: int
    col: int
    row_span: int = 1
    col_span: int = 1

    def to_dict(self) -> dict[str, int]:
        return {
            "row": self.row,
            "col": self.col,
            "row_span": self.row_span,
            "col_span": self.col_span,
        }

    @classmethod
    def from_dict(cls, data: dict[str, int]) -> MergedCell:
        return cls(
            row=data["row"],
            col=data["col"],
            row_span=data.get("row_span", 1),
            col_span=data.get("col_span", 1),
        )


# ============================================================================
# Cell Format — Individual cell formatting
# ============================================================================


@dataclass
class CellFormat:
    """Formatting for a specific table cell."""

    bold: bool = False
    italic: bool = False
    align: TableCellAlign = TableCellAlign.LEFT
    bg_color: str | None = None  # hex
    font_color: str | None = None  # hex
    font_name: str | None = None
    font_size: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        if self.bold:
            d["bold"] = True
        if self.italic:
            d["italic"] = True
        if self.align != TableCellAlign.LEFT:
            d["align"] = self.align.value
        if self.bg_color:
            d["bg_color"] = self.bg_color
        if self.font_color:
            d["font_color"] = self.font_color
        if self.font_name:
            d["font"] = self.font_name
        if self.font_size:
            d["size"] = self.font_size
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CellFormat:
        align_str = data.get("align", "left")
        return cls(
            bold=data.get("bold", False),
            italic=data.get("italic", False),
            align=TableCellAlign(align_str),
            bg_color=data.get("bg_color"),
            font_color=data.get("font_color"),
            font_name=data.get("font"),
            font_size=data.get("size"),
        )


# ============================================================================
# Page Setup — Document/section page configuration
# ============================================================================


@dataclass
class PageSetup:
    """Page setup configuration."""

    size: PageSizeType = "A4"
    orientation: OrientationType = "portrait"
    margin_top: float = 2.54  # cm
    margin_bottom: float = 2.54
    margin_left: float = 3.17
    margin_right: float = 3.17
    header_distance: float = 1.27
    footer_distance: float = 1.27
    # Custom dimensions (only when size="custom")
    custom_width: float | None = None  # cm
    custom_height: float | None = None  # cm

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "size": self.size,
            "orientation": self.orientation,
            "margins": {
                "top": self.margin_top,
                "bottom": self.margin_bottom,
                "left": self.margin_left,
                "right": self.margin_right,
            },
            "header_distance": self.header_distance,
            "footer_distance": self.footer_distance,
        }
        if self.custom_width:
            d["custom_width"] = self.custom_width
        if self.custom_height:
            d["custom_height"] = self.custom_height
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PageSetup:
        margins = data.get("margins", {})
        return cls(
            size=data.get("size", "A4"),
            orientation=data.get("orientation", "portrait"),
            margin_top=margins.get("top", 2.54),
            margin_bottom=margins.get("bottom", 2.54),
            margin_left=margins.get("left", 3.17),
            margin_right=margins.get("right", 3.17),
            header_distance=data.get("header_distance", 1.27),
            footer_distance=data.get("footer_distance", 1.27),
            custom_width=data.get("custom_width"),
            custom_height=data.get("custom_height"),
        )


# ============================================================================
# DFM Block — Core block unit
# ============================================================================


@dataclass
class DfmBlock:
    """
    A single block in the DFM intermediate representation.

    Each block corresponds to one logical unit in the docx
    (paragraph, table, image, etc.) and carries all metadata
    needed for lossless round-trip conversion.
    """

    id: str
    block_type: DfmBlockType
    content: str  # Visible/editable text or md
    style_name: str | None = None  # Word paragraph style name

    # Format runs (for mixed-format paragraphs)
    runs: list[FormatRun] = field(default_factory=list)

    # Heading-specific
    level: int = 0  # Heading level 1-6

    # List-specific
    list_level: int = 0
    num_id: int | None = None  # Word numbering ID

    # Table-specific
    table_style: str | None = None
    col_widths: list[float] = field(default_factory=list)  # in cm
    merged_cells: list[MergedCell] = field(default_factory=list)
    cell_formats: dict[str, CellFormat] = field(default_factory=dict)  # "row:col"
    is_nested: bool = False
    parent_cell: str | None = None  # "row:col" if nested
    raw_xml_ref: str | None = None  # path to preserved XML

    # Image-specific
    image_path: str | None = None  # relative to assets/
    image_width_cm: float | None = None
    image_height_cm: float | None = None
    image_anchor: ImageAnchorType = ImageAnchorType.INLINE
    image_alt: str = ""

    # Chart-specific
    chart_type: str | None = None  # bar, line, pie, etc.
    binary_ref: str | None = None  # relative to assets/
    data_hash: str | None = None

    # TOC-specific
    toc_depth: int = 3
    field_code: str | None = None

    # Header/Footer-specific
    hdr_ftr_type: str | None = None  # default, first, even
    xml_ref: str | None = None  # relative to parts/
    preview_text: str = ""

    # Field-specific
    field_type: str | None = None
    field_instruction: str | None = None
    field_display: str | None = None

    # Break-specific
    break_type: BreakType | None = None
    section_page_setup: PageSetup | None = None  # for section breaks

    # Footnote-specific
    footnote_id: int | None = None

    # Citation-specific
    citation_style: str | None = None
    citation_entries: list[dict[str, Any]] = field(default_factory=list)

    # Bookmark-specific
    bookmark_name: str | None = None

    # Revision-specific
    revision_type: str | None = None  # insert, delete, format
    revision_author: str | None = None
    revision_date: str | None = None

    # OLE-specific
    ole_prog_id: str | None = None
    ole_display_name: str | None = None
    ole_width_cm: float | None = None
    ole_height_cm: float | None = None

    # Macro-specific
    macro_name: str | None = None
    macro_hash: str | None = None

    # Generic metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_editable(self) -> bool:
        return self.block_type.is_editable

    @property
    def is_protected(self) -> bool:
        return self.block_type.is_protected

    @property
    def has_mixed_format(self) -> bool:
        """Whether this block has multiple format runs with different styles."""
        if len(self.runs) <= 1:
            return False
        first = self.runs[0]
        return any(
            r.bold != first.bold
            or r.italic != first.italic
            or r.font_name != first.font_name
            or r.font_size != first.font_size
            or r.color != first.color
            for r in self.runs[1:]
        )

    @property
    def plain_text(self) -> str:
        """Get concatenated text from all runs."""
        if self.runs:
            return "".join(r.text for r in self.runs)
        return self.content


# ============================================================================
# Document Styles — Document-level style metadata
# ============================================================================


@dataclass
class DocxStyleInfo:
    """Document-level style information preserved for round-trip."""

    page_setup: PageSetup = field(default_factory=PageSetup)
    default_font_name: str = "Calibri"
    default_font_size: float = 11.0
    default_font_color: str = "#000000"

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_setup": self.page_setup.to_dict(),
            "default_font": {
                "name": self.default_font_name,
                "size": self.default_font_size,
                "color": self.default_font_color,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DocxStyleInfo:
        font = data.get("default_font", {})
        return cls(
            page_setup=PageSetup.from_dict(data.get("page_setup", {})),
            default_font_name=font.get("name", "Calibri"),
            default_font_size=font.get("size", 11.0),
            default_font_color=font.get("color", "#000000"),
        )


# ============================================================================
# DocxIR — Aggregate Root: Intermediate Representation
# ============================================================================


@dataclass
class DocxIR:
    """
    Docx Intermediate Representation — the aggregate root for DFM conversion.

    Contains all information needed to losslessly reconstruct a .docx file
    from a DFM editing session.
    """

    doc_id: str
    source_path: str
    source_filename: str = ""
    checksum: str = ""  # SHA-256 of original docx

    # Document metadata
    style_info: DocxStyleInfo = field(default_factory=DocxStyleInfo)

    # All blocks in document order
    blocks: list[DfmBlock] = field(default_factory=list)

    # Binary assets: asset_name → relative path in assets/
    assets: dict[str, str] = field(default_factory=dict)

    # XML parts preserved for round-trip
    preserved_parts: dict[str, str] = field(
        default_factory=dict
    )  # part_name → rel path

    # Relationships data (for image/chart/OLE references)
    relationships: dict[str, str] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Block ID counters (for generating unique IDs)
    _id_counters: dict[str, int] = field(default_factory=dict)

    def next_block_id(self, block_type: DfmBlockType) -> str:
        """Generate the next sequential block ID for a given type."""
        prefix = BLOCK_ID_PREFIXES.get(block_type, "x")
        count = self._id_counters.get(prefix, 0) + 1
        self._id_counters[prefix] = count
        return f"{prefix}{count:03d}"

    def add_block(self, block: DfmBlock) -> None:
        """Add a block to the IR."""
        self.blocks.append(block)

    def find_block(self, block_id: str) -> DfmBlock | None:
        """Find a block by its ID."""
        for block in self.blocks:
            if block.id == block_id:
                return block
        return None

    def get_blocks_by_type(self, block_type: DfmBlockType) -> list[DfmBlock]:
        """Get all blocks of a specific type."""
        return [b for b in self.blocks if b.block_type == block_type]

    @property
    def editable_blocks(self) -> list[DfmBlock]:
        """Get all editable blocks."""
        return [b for b in self.blocks if b.is_editable]

    @property
    def protected_blocks(self) -> list[DfmBlock]:
        """Get all protected blocks."""
        return [b for b in self.blocks if b.is_protected]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the IR contents."""
        type_counts: dict[str, int] = {}
        for block in self.blocks:
            key = block.block_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        return {
            "doc_id": self.doc_id,
            "source": self.source_filename,
            "total_blocks": len(self.blocks),
            "editable_blocks": len(self.editable_blocks),
            "protected_blocks": len(self.protected_blocks),
            "block_types": type_counts,
            "assets": len(self.assets),
            "preserved_parts": list(self.preserved_parts.keys()),
        }
