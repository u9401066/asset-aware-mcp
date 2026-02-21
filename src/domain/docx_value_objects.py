"""
Domain Layer - Docx Value Objects

Immutable value objects for the DFM (Docx-Flavored Markdown) module.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal


class DfmBlockType(str, Enum):
    """DFM block types — classifies each element in a docx."""

    # Editable blocks (rendered as native Markdown)
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    LIST_ITEM = "list_item"

    # Editable with format metadata
    FORMAT = "format"  # Mixed-format paragraph (multi-font/color runs)
    TABLE = "table"  # Table (simple or merged)
    IMAGE = "image"  # Inline/anchored image
    CAPTION = "caption"  # Figure/table caption
    FOOTNOTE = "footnote"  # Footnote content
    CITATION = "citation"  # Bibliography citation field

    # Protected blocks (read-only, binary or XML preserved)
    CHART = "chart"  # Embedded Excel chart
    TOC = "toc"  # Table of Contents field
    HEADER = "header"  # Page header
    FOOTER = "footer"  # Page footer
    FIELD = "field"  # Field code (PAGE, REF, etc.)
    BREAK = "break"  # Page/section break
    MACRO = "macro"  # VBA macro
    OLE = "ole"  # OLE embedded object
    BOOKMARK = "bookmark"  # Bookmark anchor
    REVISION = "revision"  # Track changes revision

    # Meta blocks
    STYLES = "styles"  # Document-level style definitions

    @property
    def is_editable(self) -> bool:
        """Whether this block type allows text editing."""
        return self in _EDITABLE_TYPES

    @property
    def is_protected(self) -> bool:
        """Whether this block is fully protected (binary/XML)."""
        return self in _PROTECTED_TYPES

    @property
    def dfm_tag(self) -> str:
        """The tag name used in DFM HTML comments."""
        return self.value


_EDITABLE_TYPES = frozenset(
    {
        DfmBlockType.PARAGRAPH,
        DfmBlockType.HEADING,
        DfmBlockType.LIST_ITEM,
        DfmBlockType.FORMAT,
        DfmBlockType.TABLE,
        DfmBlockType.IMAGE,
        DfmBlockType.CAPTION,
        DfmBlockType.FOOTNOTE,
        DfmBlockType.CITATION,
    }
)

_PROTECTED_TYPES = frozenset(
    {
        DfmBlockType.CHART,
        DfmBlockType.TOC,
        DfmBlockType.HEADER,
        DfmBlockType.FOOTER,
        DfmBlockType.FIELD,
        DfmBlockType.MACRO,
        DfmBlockType.OLE,
    }
)


class BreakType(str, Enum):
    """Types of document breaks."""

    PAGE = "page"
    SECTION_NEXT_PAGE = "section_next_page"
    SECTION_CONTINUOUS = "section_continuous"
    SECTION_EVEN_PAGE = "section_even_page"
    SECTION_ODD_PAGE = "section_odd_page"
    COLUMN = "column"


class ImageAnchorType(str, Enum):
    """How an image is anchored in the document."""

    INLINE = "inline"
    FLOATING = "floating"


class TableCellAlign(str, Enum):
    """Table cell text alignment."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class FieldType(str, Enum):
    """Common Word field types."""

    PAGE = "PAGE"
    NUMPAGES = "NUMPAGES"
    REF = "REF"
    TOC = "TOC"
    HYPERLINK = "HYPERLINK"
    SEQ = "SEQ"
    CITATION = "CITATION"
    BIBLIOGRAPHY = "BIBLIOGRAPHY"
    DATE = "DATE"
    OTHER = "OTHER"


# Block ID prefix conventions
BLOCK_ID_PREFIXES: dict[DfmBlockType, str] = {
    DfmBlockType.PARAGRAPH: "p",
    DfmBlockType.HEADING: "h",
    DfmBlockType.LIST_ITEM: "l",
    DfmBlockType.FORMAT: "p",
    DfmBlockType.TABLE: "t",
    DfmBlockType.IMAGE: "i",
    DfmBlockType.CAPTION: "cap",
    DfmBlockType.FOOTNOTE: "fn",
    DfmBlockType.CITATION: "cite",
    DfmBlockType.CHART: "c",
    DfmBlockType.TOC: "toc",
    DfmBlockType.HEADER: "hdr",
    DfmBlockType.FOOTER: "ftr",
    DfmBlockType.FIELD: "f",
    DfmBlockType.BREAK: "br",
    DfmBlockType.MACRO: "m",
    DfmBlockType.OLE: "ole",
    DfmBlockType.BOOKMARK: "bm",
    DfmBlockType.REVISION: "rev",
    DfmBlockType.STYLES: "sty",
}


# Orientation type for page setup
OrientationType = Literal["portrait", "landscape"]

# Page size type
PageSizeType = Literal["A4", "Letter", "Legal", "A3", "B5", "custom"]
