"""Shared OpenXML constants and scalar converters for DOCX infrastructure."""

from __future__ import annotations

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

REVISION_TAG_TYPES = {
    "ins": "insert",
    "del": "delete",
    "moveFrom": "move_from",
    "moveTo": "move_to",
    "rPrChange": "format",
    "pPrChange": "paragraph_format",
}
NON_VISIBLE_REVISION_TAGS = {"del", "moveFrom"}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
DOCX_LOCATOR_VERSION = "docx-dfm-locator-v1"

EMU_PER_CM = 360000
TWIPS_PER_CM = 567
HALF_POINTS_TO_PT = 0.5


def emu_to_cm(emu: int) -> float:
    """Convert EMU (English Metric Units) to centimeters."""
    return round(emu / EMU_PER_CM, 2)


def cm_to_emu(cm: float) -> int:
    """Convert centimeters to EMU."""
    return int(cm * EMU_PER_CM)


def twips_to_cm(twips: int) -> float:
    """Convert twips to centimeters."""
    return round(twips / TWIPS_PER_CM, 2)


def half_pt_to_pt(half_pt: int) -> float:
    """Convert half-points to points."""
    return half_pt * HALF_POINTS_TO_PT


def safe_int(value: str | None, default: int | None = None) -> int | None:
    """Parse an OpenXML integer attribute without trusting converted DOCX."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
