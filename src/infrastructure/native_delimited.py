"""Byte-preserving CSV/TSV mutations with independent decoded-value readback."""

from __future__ import annotations

import csv
import hashlib
from typing import Any

from src.domain.native_asset_models import NativeEditResult
from src.domain.native_delimited import (
    DELIMITED_REVIEW,
    MAX_DELIMITED_BYTES,
    NativeDelimitedCreate,
    NativeDelimitedDialect,
    NativeDelimitedUpdate,
    attach_delimited_evidence,
)
from src.infrastructure.native_delimited_document import DelimitedDocument, encode_row
from src.infrastructure.native_text_encoding import BOMS


def _field(
    value: str,
    document: DelimitedDocument,
    *,
    quoted: bool = False,
    single: bool = False,
) -> str:
    if value == "" and not quoted and not single:
        return ""
    return encode_row([value], document.dialect, "", force_quote=quoted)


def _apply(
    document: DelimitedDocument, patches: list[tuple[int, int, str]]
) -> tuple[bytes, list[dict[str, Any]]]:
    encoded = [
        (a, b, value.encode(document.source.encoding, errors="strict"))
        for a, b, value in patches
    ]
    encoded.sort(key=lambda p: (p[0], p[1]))
    data, position = document.source.data, 0
    pieces: list[bytes] = []
    receipt: list[dict[str, Any]] = []
    if (
        len(data) + sum(len(value) - (end - start) for start, end, value in encoded)
        > MAX_DELIMITED_BYTES
    ):
        raise ValueError("Delimited mutation exceeds the byte budget")
    for start, end, value in encoded:
        if start < position or not start <= end <= len(data):
            raise ValueError("Delimited mutation contains overlapping or invalid spans")
        pieces.extend((data[position:start], value))
        receipt.append(
            {
                "byte_range": [start, end],
                "removed_sha256": hashlib.sha256(data[start:end]).hexdigest(),
                "inserted_sha256": hashlib.sha256(value).hexdigest(),
                "removed_bytes": end - start,
                "inserted_bytes": len(value),
            }
        )
        position = end
    pieces.append(data[position:])
    return b"".join(pieces), receipt


class NativeDelimited:
    """Construct inside ProcessNativeDelimited; CSV's global field limit stays there."""

    def __init__(self) -> None:
        csv.field_size_limit(MAX_DELIMITED_BYTES)

    def inspect(self, data: bytes, dialect: NativeDelimitedDialect) -> dict[str, Any]:
        return DelimitedDocument(data, dialect).inspect()

    def read_cell(
        self, data: bytes, dialect: NativeDelimitedDialect, row: int, column: int
    ) -> dict[str, Any]:
        return DelimitedDocument(data, dialect).cell(row, column)

    def decompose(
        self, data: bytes, dialect: NativeDelimitedDialect
    ) -> list[dict[str, Any]]:
        document = DelimitedDocument(data, dialect)
        return [
            document.cell(i, j)
            for i, row in enumerate(document.rows)
            for j in range(len(row.fields))
        ]

    def create(self, request: NativeDelimitedCreate) -> tuple[bytes, NativeEditResult]:
        dialect = request.dialect or NativeDelimitedDialect(
            delimiter="\t" if request.name.lower().endswith(".tsv") else ","
        )
        encoding = dialect.encoding or "utf-8"
        if request.bom and encoding not in BOMS:
            raise ValueError("This encoding does not support a Unicode BOM")
        text = "".join(
            encode_row(row, dialect, request.record_separator) for row in request.rows
        )
        if not request.final_separator and request.rows:
            text = text[: -len(request.record_separator)]
        data = (BOMS[encoding] if request.bom else b"") + text.encode(
            encoding, errors="strict"
        )
        checked = DelimitedDocument(
            data, dialect.model_copy(update={"encoding": encoding})
        )
        if [row.values for row in checked.rows] != request.rows:
            raise ValueError(
                "Requested rows cannot round-trip with this final separator policy"
            )
        return data, NativeEditResult(
            changed_parts=["file"],
            preserved_parts=0,
            changes=[
                {
                    "operation": "create_delimited",
                    "dialect": checked.dialect.model_dump(mode="json"),
                    "row_count": len(request.rows),
                }
            ],
            checks=[
                "strict_encoding_and_dialect",
                "all_string_values_reparsed",
                "row_and_field_budgets",
            ],
            review_required=DELIMITED_REVIEW,
        )

    def update(
        self,
        data: bytes,
        dialect: NativeDelimitedDialect,
        request: NativeDelimitedUpdate,
    ) -> tuple[bytes, NativeEditResult]:
        document = DelimitedDocument(data, dialect)
        expected = [list(row.values) for row in document.rows]
        patches: list[tuple[int, int, str]] = []
        repairs: list[str] = []

        def patch(start: int, end: int, value: str) -> None:
            a, b = document.source.byte_span(start, end)
            patches.append((a, b, value))

        if request.operation == "set_cells":
            revision = hashlib.sha256(data).hexdigest()
            seen: set[tuple[int, int]] = set()
            for edit in request.cells:
                ref = edit.reference
                if ref.revision != revision or ref.dialect != document.dialect:
                    raise ValueError(
                        "Delimited field reference has a different revision or dialect"
                    )
                location = ref.locator
                key = (location.row, location.column)
                if key in seen:
                    raise ValueError("Cannot edit a delimited field twice")
                seen.add(key)
                record = document.cell(*key)
                attach_delimited_evidence(record, ref.asset_id, ref.revision)
                if record["evidence"] != ref.model_dump(mode="json"):
                    raise ValueError(
                        "Delimited field reference failed integrity verification"
                    )
                if record["value"] != edit.value:
                    quoted = document.dialect.quotechar is not None and record[
                        "raw"
                    ].startswith(document.dialect.quotechar)
                    value = _field(
                        edit.value,
                        document,
                        quoted=quoted,
                        single=len(document.rows[location.row].fields) == 1,
                    )
                    patch(location.char_start, location.char_end, value)
                expected[location.row][location.column] = edit.value
        elif request.operation == "insert_rows":
            if request.index > len(document.rows):
                raise ValueError("Inserted row index exceeds the logical table")
            position = (
                document.rows[request.index].start
                if request.index < len(document.rows)
                else len(document.source.text)
            )
            text = "".join(
                encode_row(row, document.dialect, request.record_separator)
                for row in request.rows
            )
            if (
                request.index == len(document.rows)
                and document.rows
                and not document.rows[-1].separator
            ):
                text = request.record_separator + text
                repairs.append(
                    "Inserted explicit separator after the former unterminated final row"
                )
            patch(position, position, text)
            expected[request.index : request.index] = request.rows
        elif request.operation == "delete_rows":
            end = request.index + request.count
            if end > len(document.rows):
                raise ValueError("Deleted row range exceeds the logical table")
            patch(document.rows[request.index].start, document.rows[end - 1].end, "")
            del expected[request.index : end]
        elif request.operation == "insert_column":
            if len(request.values) != len(document.rows):
                raise ValueError(
                    "Inserted column requires one exact string per logical row"
                )
            for index, row in enumerate(document.rows):
                if request.index > len(row.fields):
                    raise ValueError(
                        "Inserted column is outside at least one ragged row"
                    )
                value = _field(request.values[index], document, single=not row.fields)
                if request.index < len(row.fields):
                    position = row.fields[request.index][0]
                    value += document.dialect.delimiter
                elif row.fields:
                    position = row.fields[-1][1]
                    value = document.dialect.delimiter + value
                else:
                    position = row.start
                patch(position, position, value)
                expected[index].insert(request.index, request.values[index])
        else:
            end = request.index + request.count
            if not document.rows or any(end > len(row.fields) for row in document.rows):
                raise ValueError("Deleted columns do not exist in every logical row")
            for index, row in enumerate(document.rows):
                if end < len(row.fields):
                    start, stop = row.fields[request.index][0], row.fields[end][0]
                elif request.index:
                    start, stop = row.fields[request.index - 1][1], row.fields[-1][1]
                else:
                    start, stop = row.start, row.fields[-1][1]
                replacement = ""
                if request.count == len(row.fields) and not row.separator:
                    replacement = request.record_separator
                    repairs.append(
                        "Inserted explicit final separator to retain the zero-field logical row"
                    )
                remaining = row.fields[: request.index] + row.fields[end:]
                if len(remaining) == 1 and remaining[0][0] == remaining[0][1]:
                    replacement = encode_row([""], document.dialect, "")
                    repair = (
                        "Quoted surviving empty field to retain a one-field logical row"
                    )
                    if repair not in repairs:
                        repairs.append(repair)
                patch(start, stop, replacement)
                del expected[index][request.index : end]
        changed, receipt = _apply(document, patches)
        checked = DelimitedDocument(changed, document.dialect)
        if [row.values for row in checked.rows] != expected:
            raise ValueError(
                "Delimited mutation changed unexpected values or logical row correspondence"
            )
        return changed, NativeEditResult(
            changed_parts=["file"] if changed != data else [],
            preserved_parts=0,
            changes=[
                {
                    "operation": request.operation,
                    "dialect": document.dialect.model_dump(mode="json"),
                    "patches": receipt,
                    "row_count_before": len(document.rows),
                    "row_count_after": len(checked.rows),
                }
            ],
            checks=[
                "strict_encoding_and_dialect",
                "exact_source_byte_spans",
                "untouched_bytes_preserved_by_splices",
                "all_expected_string_values_reparsed",
                "logical_row_correspondence",
                "row_field_and_byte_budgets",
            ],
            repairs=repairs,
            review_required=DELIMITED_REVIEW,
        )
