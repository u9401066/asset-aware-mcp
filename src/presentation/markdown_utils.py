"""Small Markdown formatting helpers for presentation-layer output."""

from __future__ import annotations


def escape_table_cell(value: object) -> str:
    """Escape characters that would break a Markdown table cell."""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r\n", " ")
        .replace("\n", " ")
        .replace("\r", " ")
    )
