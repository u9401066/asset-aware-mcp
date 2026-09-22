"""OpenFormula reference edits, without evaluating formulas or rewriting literals.

This is a structural-edit primitive, not an ODS package editor. Each edit addresses
the preceding state. Callers must separately map native cells, names, drawings and
other dependent XML and preserve the original revision's evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

from src.domain.native_ods import MAX_ODS_COLUMNS, MAX_ODS_ROWS, ods_text

if TYPE_CHECKING:
    from collections.abc import Mapping

OPENFORMULA = "urn:oasis:names:tc:opendocument:xmlns:of:1.2"
MAX_REFERENCE_TEXT = 65_536
COORDINATE = re.compile(r"(?:(\$?)([A-Z]{1,8}))?(?:(\$?)([1-9][0-9]{0,9}))?")


def _name(value: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 1024:
        raise ValueError("ODS sheet identity requires 1-1024 characters")
    ods_text(value)


@dataclass(frozen=True)
class ODSAxisEdit:
    sheet: str
    axis: Literal["rows", "columns"]
    operation: Literal["insert", "delete"]
    index: int
    count: int
    # These are explicit editor grid bounds, not limits in the ODF specification.
    row_limit: int = MAX_ODS_ROWS
    column_limit: int = MAX_ODS_COLUMNS

    def __post_init__(self) -> None:
        _name(self.sheet)
        if self.axis not in {"rows", "columns"} or self.operation not in {
            "insert",
            "delete",
        }:
            raise ValueError("Require a row/column insertion or deletion")
        for value, maximum in (
            (self.row_limit, MAX_ODS_ROWS),
            (self.column_limit, MAX_ODS_COLUMNS),
        ):
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError("Invalid ODS reference grid bounds")
        limit = self.row_limit if self.axis == "rows" else self.column_limit
        if (
            type(self.index) is not int
            or type(self.count) is not int
            or not 0 <= self.index < limit
            or not 1 <= self.count <= limit - self.index
        ):
            raise ValueError("ODS axis edit exceeds its explicit grid bounds")


@dataclass(frozen=True)
class ODSSheetRename:
    sheet: str
    new_name: str

    def __post_init__(self) -> None:
        _name(self.sheet)
        _name(self.new_name)


@dataclass(frozen=True)
class ODSSheetDelete:
    sheet: str

    def __post_init__(self) -> None:
        _name(self.sheet)


ODSReferenceEdit = ODSAxisEdit | ODSSheetRename | ODSSheetDelete


def quoted_end(text: str, start: int) -> int:
    """Return the end of an ODF single/double quoted token, including its quotes."""
    quote = text[start]
    position = start + 1
    while position < len(text):
        if text[position] == quote:
            if position + 1 < len(text) and text[position + 1] == quote:
                position += 2
                continue
            return position + 1
        position += 1
    raise ValueError("Unterminated ODS quoted token")


def _split(text: str, separator: str) -> list[str]:
    parts, start, index = [], 0, 0
    while index < len(text):
        if text[index] == "'":
            index = quoted_end(text, index)
            continue
        if text[index] == separator:
            parts.append(text[start:index])
            start = index + 1
        index += 1
    return [*parts, text[start:]]


def _sheet_name(token: str) -> str:
    raw = token.removeprefix("$")
    if raw.startswith("'"):
        if quoted_end(raw, 0) != len(raw):
            raise ValueError("Invalid ODS quoted sheet identity")
        value = raw[1:-1].replace("''", "'")
    else:
        if re.search(r"[\s.\[\]#$':]", raw):
            raise ValueError("Invalid ODS unquoted sheet identity")
        value = raw
    _name(value)
    return value


def _column(value: str) -> int:
    result = 0
    for char in value:
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def _letters(value: int) -> str:
    result = ""
    while value >= 0:
        value, remainder = divmod(value, 26)
        result = chr(ord("A") + remainder) + result
        value -= 1
    return result


@dataclass(frozen=True)
class ODSEndpoint:
    sheet_token: str
    subtable_tokens: tuple[str, ...]
    column: int | None
    row: int | None
    absolute_column: bool
    absolute_row: bool

    @property
    def sheet(self) -> str | None:
        return _sheet_name(self.sheet_token) if self.sheet_token else None

    def render(self) -> str:
        coordinate = ""
        if self.column is not None:
            coordinate += ("$" if self.absolute_column else "") + _letters(self.column)
        if self.row is not None:
            coordinate += ("$" if self.absolute_row else "") + str(self.row + 1)
        return ".".join((self.sheet_token, *self.subtable_tokens, coordinate))


def _endpoint(text: str) -> ODSEndpoint:
    parts = _split(text, ".")
    if len(parts) < 2:
        raise ValueError("ODS references require a sheet separator before coordinates")
    sheet, *subtables, coordinate = parts
    if sheet:
        _sheet_name(sheet)
    elif subtables:
        raise ValueError("ODS subtable references require an explicit sheet")
    for subtable in subtables:
        if subtable.startswith("'"):
            _sheet_name(subtable)
        elif not re.fullmatch(r"\$?[A-Z]{1,8}\$?[1-9][0-9]{0,9}", subtable):
            raise ValueError("Invalid ODS subtable locator")
    match = COORDINATE.fullmatch(coordinate)
    if not match or not coordinate:
        raise ValueError("Invalid ODS row/column coordinate")
    return ODSEndpoint(
        sheet,
        tuple(subtables),
        _column(match[2]) if match[2] else None,
        int(match[4]) - 1 if match[4] else None,
        bool(match[1]),
        bool(match[3]),
    )


@dataclass(frozen=True)
class ODSReference:
    lexical: str
    source: str | None
    start: ODSEndpoint | None
    end: ODSEndpoint | None


def parse_ods_reference(text: str) -> ODSReference:
    """Parse the content of one [...] reference, or a native ODF range address."""
    if not isinstance(text, str) or not 1 <= len(text) <= MAX_REFERENCE_TEXT:
        raise ValueError("ODS reference exceeds its inspection budget")
    ods_text(text)
    if text == "#REF!":
        return ODSReference(text, None, None, None)
    source, remaining = None, text
    if text.startswith("'"):
        quote_end = quoted_end(text, 0)
        if text[quote_end : quote_end + 1] == "#":
            source, remaining = text[: quote_end + 1], text[quote_end + 1 :]
    parts = _split(remaining, ":")
    if not 1 <= len(parts) <= 2:
        raise ValueError("ODS reference requires one point or one range")
    start = _endpoint(parts[0])
    end = _endpoint(parts[1]) if len(parts) == 2 else None
    if end is None:
        if start.row is None or start.column is None:
            raise ValueError("Whole-row/column ODS references require two endpoints")
    elif (start.row is None, start.column is None) != (
        end.row is None,
        end.column is None,
    ):
        raise ValueError("ODS range endpoints must have the same dimensionality")
    return ODSReference(text, source, start, end)


def _rename(endpoint: ODSEndpoint, name: str) -> ODSEndpoint:
    raw = endpoint.sheet_token.removeprefix("$")
    quoted = raw.startswith("'") or bool(re.search(r"[\s.\[\]#$':]", name))
    token = "'" + name.replace("'", "''") + "'" if quoted else name
    if endpoint.sheet_token.startswith("$"):
        token = "$" + token
    return replace(endpoint, sheet_token=token)


def _interval(
    start: int, end: int, edit: ODSAxisEdit, limit: int, *, is_range: bool
) -> tuple[int, int] | None:
    reverse = end < start
    low, high = sorted((start, end))
    if high >= limit:
        raise ValueError("ODS reference exceeds the selected editor grid")
    # A range covering the entire editor axis denotes the entire axis after edits.
    if is_range and low == 0 and high == limit - 1:
        return start, end
    pinned_end = is_range and low < high and high == limit - 1
    index, count = edit.index, edit.count
    if edit.operation == "insert":
        low += count if low >= index else 0
        high += count if high >= index else 0
        if low >= limit:
            return None
        high = min(high, limit - 1)
    else:
        stop = index + count
        # Retain the surviving original cells and contract the deleted interval.
        if index <= low and high < stop:
            return None
        low = low if low < index else max(index, low - count)
        high = high if high < index else max(index - 1, high - count)
        if pinned_end:
            high = limit - 1
    return (high, low) if reverse else (low, high)


def rewrite_ods_reference(
    text: str, *, formula_sheet: str, edit: ODSReferenceEdit
) -> str:
    """Map one static reference; retain dollar flags and untouched lexical bytes.

    Native property owners must decide how to represent a returned #REF!; it is
    not a valid replacement for every XML address property. External sources are
    left untouched, never loaded. A same-document URI fragment requires a separate
    source resolver. Multi-sheet or nested-table axis edits need a mapping context.
    """
    _name(formula_sheet)
    reference = parse_ods_reference(text)
    if reference.source is not None:
        source_iri = reference.source[1:-2].replace("''", "'")
        if not source_iri or source_iri.startswith("#"):
            raise ValueError(
                "ODS same-document source references require a source resolver"
            )
        return text
    if reference.start is None:
        return text
    start, end = reference.start, reference.end
    first_sheet = start.sheet or formula_sheet
    last_sheet = (end.sheet or first_sheet) if end else first_sheet
    if isinstance(edit, ODSSheetRename):
        if first_sheet == edit.sheet and start.sheet is not None:
            start = _rename(start, edit.new_name)
        if end and last_sheet == edit.sheet and end.sheet is not None:
            end = _rename(end, edit.new_name)
    elif isinstance(edit, ODSSheetDelete):
        if first_sheet != last_sheet:
            raise ValueError("ODS sheet-range deletion requires the full sheet order")
        if first_sheet == edit.sheet:
            return "#REF!"
    else:
        if first_sheet != last_sheet:
            raise ValueError("ODS multi-sheet axis edits require a sheet-range map")
        if first_sheet != edit.sheet:
            return text
        if start.subtable_tokens or (end and end.subtable_tokens):
            raise ValueError("ODS nested-table edits require a subtable coordinate map")
        axis = "row" if edit.axis == "rows" else "column"
        limit = edit.row_limit if edit.axis == "rows" else edit.column_limit
        left = getattr(start, axis)
        right = getattr(end, axis) if end else left
        if left is None:
            return text  # A whole-axis range on the orthogonal axis.
        mapped = _interval(left, right, edit, limit, is_range=end is not None)
        if mapped is None:
            return "#REF!"
        start = (
            replace(start, row=mapped[0])
            if axis == "row"
            else replace(start, column=mapped[0])
        )
        if end:
            end = (
                replace(end, row=mapped[1])
                if axis == "row"
                else replace(end, column=mapped[1])
            )
    if start == reference.start and end == reference.end:
        return text
    return start.render() + (":" + end.render() if end else "")


@dataclass(frozen=True)
class ODSReferenceChange:
    # Unicode offsets address the ORIGINAL formula, without namespace rewriting.
    start: int
    end: int
    before: str
    after: str


def rewrite_ods_formula(
    formula: str,
    *,
    formula_sheet: str,
    edit: ODSReferenceEdit,
    namespaces: Mapping[str | None, str],
) -> tuple[str, list[ODSReferenceChange]]:
    """Rewrite bracketed references only; quoted values/labels remain exact."""
    if not isinstance(formula, str) or not 2 <= len(formula) <= MAX_REFERENCE_TEXT:
        raise ValueError("ODS formula exceeds its inspection budget")
    _name(formula_sheet)
    ods_text(formula)
    if formula.startswith("="):
        index = 1
    else:
        prefix, separator, expression = formula.partition(":")
        if (
            not separator
            or not prefix
            or namespaces.get(prefix) != OPENFORMULA
            or not expression.startswith("=")
            or len(expression) < 2
        ):
            raise ValueError(
                "ODS structural edits require a known OpenFormula namespace"
            )
        index = len(prefix) + 2
    changes: list[ODSReferenceChange] = []
    pieces: list[str] = []
    copied, output_length = 0, len(formula)
    while index < len(formula):
        char = formula[index]
        if char in "\"'":
            index = quoted_end(formula, index)
            continue
        if char == "]":
            raise ValueError("Unmatched ODS formula reference delimiter")
        if char != "[":
            index += 1
            continue
        start = index
        index += 1
        while index < len(formula) and formula[index] != "]":
            if formula[index] == "'":
                index = quoted_end(formula, index)
            elif formula[index] in '["':
                raise ValueError("Invalid nested ODS formula reference")
            else:
                index += 1
        if index == len(formula):
            raise ValueError("Unterminated ODS formula reference")
        index += 1
        before = formula[start:index]
        after = (
            "["
            + rewrite_ods_reference(
                before[1:-1], formula_sheet=formula_sheet, edit=edit
            )
            + "]"
        )
        if before != after:
            output_length += len(after) - len(before)
            if output_length > MAX_REFERENCE_TEXT:
                raise ValueError("Rewritten ODS formula exceeds its inspection budget")
            changes.append(ODSReferenceChange(start, index, before, after))
            pieces.extend((formula[copied:start], after))
            copied = index
    pieces.append(formula[copied:])
    return "".join(pieces), changes
