"""CSV semantic parsing plus exact native token boundaries; no whole-file rewrite."""

from __future__ import annotations

import bisect
import csv
import hashlib
import io
import re
from array import array
from dataclasses import dataclass
from typing import Any

from src.domain.native_delimited import MAX_DELIMITED_FIELDS, NativeDelimitedDialect
from src.infrastructure.native_text_encoding import decode_source


def csv_options(dialect: NativeDelimitedDialect) -> dict[str, Any]:
    return {
        "delimiter": dialect.delimiter,
        "quotechar": dialect.quotechar,
        "escapechar": dialect.escapechar,
        "doublequote": dialect.doublequote,
        "quoting": csv.QUOTE_MINIMAL
        if dialect.quotechar is not None
        else csv.QUOTE_NONE,
        "skipinitialspace": False,
        "strict": True,
    }


@dataclass
class DelimitedRow:
    start: int
    end: int
    separator: str
    fields: list[tuple[int, int]]
    values: list[str]


def field_spans(
    text: str, start: int, end: int, dialect: NativeDelimitedDialect
) -> tuple[list[tuple[int, int]], str]:
    """Only locate source tokens; Python csv independently supplies decoded values."""
    fields: list[tuple[int, int]] = []
    position, field_start, quoted = start, start, False
    while position < end:
        char = text[position]
        if dialect.escapechar is not None and char == dialect.escapechar:
            position += 2
            continue
        if quoted:
            if char == dialect.quotechar:
                if (
                    dialect.doublequote
                    and position + 1 < end
                    and text[position + 1] == char
                ):
                    position += 2
                    continue
                quoted = False
        elif position == field_start and char == dialect.quotechar:
            quoted = True
        elif char == dialect.delimiter:
            fields.append((field_start, position))
            field_start = position + 1
        elif char in "\r\n":
            separator = "\r\n" if text[position : position + 2] == "\r\n" else char
            if position + len(separator) != end:
                raise ValueError(
                    "CSV source boundaries disagree with logical row parsing"
                )
            if position > start:
                fields.append((field_start, position))
            return fields, separator
        position += 1
    if quoted or position > end:
        raise ValueError("Incomplete quoted or escaped CSV field")
    if end > start:
        fields.append((field_start, end))
    return fields, ""


class DelimitedDocument:
    def __init__(self, data: bytes, dialect: NativeDelimitedDialect):
        self.source = decode_source(data, dialect.encoding)
        self.dialect = dialect.model_copy(update={"encoding": self.source.encoding})
        self.rows: list[DelimitedRow] = []
        self.line_ends = array(
            "I", (m.end() for m in re.finditer(r"\r\n|\r|\n", self.source.text))
        )
        stream = io.StringIO(self.source.text, newline="")
        reader = csv.reader(stream, **csv_options(self.dialect))
        start, field_count = 0, 0
        for values in reader:
            end = stream.tell()
            fields, separator = field_spans(self.source.text, start, end, self.dialect)
            if len(fields) != len(values):
                raise ValueError("CSV field boundaries disagree with decoded values")
            field_count += len(fields)
            if (
                len(self.rows) >= MAX_DELIMITED_FIELDS
                or field_count > MAX_DELIMITED_FIELDS
            ):
                raise ValueError("Delimited table exceeds the row/field budget")
            self.rows.append(DelimitedRow(start, end, separator, fields, values))
            start = end
        if start != len(self.source.text):
            raise ValueError("CSV reader did not consume the complete source")

    def inspect(self) -> dict[str, Any]:
        widths = [len(row.fields) for row in self.rows]
        return {
            "schema_version": "native-delimited-table-v1",
            "dialect": self.dialect.model_dump(mode="json"),
            "bom_hex": self.source.bom.hex(),
            "size_bytes": len(self.source.data),
            "text_length": len(self.source.text),
            "decoded_text_sha256": hashlib.sha256(
                self.source.text.encode()
            ).hexdigest(),
            "row_count": len(self.rows),
            "field_count": sum(widths),
            "row_lengths": widths,
            "rectangular": len(set(widths)) <= 1,
            "record_separators": [row.separator for row in self.rows],
            "header_policy": "No inferred header; every field is an exact string",
            "coordinate_system": "Zero-based logical row/column; byte spans include BOM, character spans exclude BOM; physical lines may span multiple lines per record",
        }

    def cell(self, row: int, column: int) -> dict[str, Any]:
        if not 0 <= row < len(self.rows) or not 0 <= column < len(
            self.rows[row].fields
        ):
            raise ValueError("Delimited field locator is outside the logical table")
        start, end = self.rows[row].fields[column]
        byte_start, byte_end = self.source.byte_span(start, end)
        raw = self.source.text[start:end]
        raw_bytes = self.source.data[byte_start:byte_end]
        if raw_bytes.decode(self.source.encoding) != raw:
            raise ValueError(
                "CSV character locator disagrees with original source bytes"
            )
        return {
            "schema_version": "native-delimited-cell-v1",
            "dialect": self.dialect.model_dump(mode="json"),
            "locator": {
                "row": row,
                "column": column,
                "byte_start": byte_start,
                "byte_end": byte_end,
                "char_start": start,
                "char_end": end,
            },
            "kind": "string",
            "value": self.rows[row].values[column],
            "raw": raw,
            "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "line_range": [
                bisect.bisect_right(self.line_ends, start),
                bisect.bisect_right(self.line_ends, max(start, end - 1)) + 1,
            ],
            "context": {
                "prefix": self.source.text[max(0, start - 48) : start],
                "suffix": self.source.text[end : end + 48],
            },
            "verification_scope": "Native string value and exact source spelling/position; no header/type/meaning inference",
        }


def encode_row(
    values: list[str],
    dialect: NativeDelimitedDialect,
    separator: str,
    *,
    force_quote: bool = False,
) -> str:
    stream = io.StringIO(newline="")
    options = csv_options(dialect)
    if force_quote and dialect.quotechar is not None:
        options["quoting"] = csv.QUOTE_ALL
    # Both newline characters must trigger escaping, independent of chosen separator.
    writer = csv.writer(stream, **{**options, "lineterminator": "\r\n"})
    writer.writerow(values)
    encoded = stream.getvalue()
    if not encoded.endswith("\r\n"):
        raise ValueError("CSV writer did not produce its declared record boundary")
    return encoded[:-2] + separator
