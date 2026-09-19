"""Native byte preservation and logical CSV structure across messy real-world syntax."""

import codecs
import csv
import hashlib
import io
import random
from copy import deepcopy

import pytest
from pydantic import TypeAdapter

from src.domain.native_delimited import (
    NativeDelimitedCreate,
    NativeDelimitedDialect,
    NativeDelimitedUpdate,
    attach_delimited_evidence,
)
from src.infrastructure.native_delimited import NativeDelimited
from src.infrastructure.native_delimited_document import csv_options
from src.infrastructure.native_delimited_process import ProcessNativeDelimited


@pytest.fixture
def adapter():
    limit = csv.field_size_limit()
    try:
        yield NativeDelimited()
    finally:
        csv.field_size_limit(limit)


def edit(adapter, data, dialect, **request):
    return adapter.update(
        data, dialect, TypeAdapter(NativeDelimitedUpdate).validate_python(request)
    )


def reference(adapter, data, dialect, row, column):
    cell = adapter.read_cell(data, dialect, row, column)
    attach_delimited_evidence(
        cell, "file_" + "a" * 32, hashlib.sha256(data).hexdigest()
    )
    return cell["evidence"]


@pytest.mark.parametrize(
    "encoding,bom",
    [
        ("utf-8", b""),
        ("utf-8", codecs.BOM_UTF8),
        ("utf-16-le", codecs.BOM_UTF16_LE),
        ("utf-16-be", codecs.BOM_UTF16_BE),
        ("cp950", b""),
        ("cp1252", b""),
        ("latin-1", b""),
    ],
)
def test_native_field_spans_multiline_mixed_eol_and_exact_replacement(
    adapter, encoding, bom
):
    name = (
        "研究" if encoding in {"cp950", "utf-8", "utf-16-le", "utf-16-be"} else "étude"
    )
    text = f'"{name}",code\r\n"first\r\nsecond","007"\n\rsolo,tail'
    data = bom + text.encode(encoding)
    dialect = NativeDelimitedDialect(encoding=encoding)
    info = adapter.inspect(data, dialect)
    assert info["row_lengths"] == [2, 2, 0, 2]
    assert info["record_separators"] == ["\r\n", "\n", "\r", ""]
    field = adapter.read_cell(data, dialect, 1, 0)
    assert field["value"] == "first\r\nsecond"
    assert field["line_range"] == [1, 3]
    loc = field["locator"]
    assert (
        data[loc["byte_start"] : loc["byte_end"]].decode(encoding)
        == '"first\r\nsecond"'
    )
    assert text[loc["char_start"] : loc["char_end"]] == field["raw"]
    ref = reference(adapter, data, dialect, 1, 1)
    changed, report = edit(
        adapter,
        data,
        dialect,
        operation="set_cells",
        cells=[{"reference": ref, "value": "008"}],
    )
    assert changed == bom + text.replace('"007"', '"008"').encode(encoding)
    assert report.checks and report.changes[0]["patches"][0]["removed_bytes"] == len(
        '"007"'.encode(encoding)
    )
    same, _ = edit(
        adapter,
        data,
        dialect,
        operation="set_cells",
        cells=[{"reference": ref, "value": "007"}],
    )
    assert same == data


def test_cp950_alias_bytes_survive_unrelated_edits(adapter):
    data = b"code,\xa2\xcc\r\n007,keep"
    assert data.decode("cp950").encode("cp950") != data
    dialect = NativeDelimitedDialect(encoding="cp950")
    ref = reference(adapter, data, dialect, 0, 0)
    changed, _ = edit(
        adapter,
        data,
        dialect,
        operation="set_cells",
        cells=[{"reference": ref, "value": "sample"}],
    )
    assert changed == b"sample,\xa2\xcc\r\n007,keep"
    field = adapter.read_cell(changed, dialect, 0, 1)
    assert (
        changed[field["locator"]["byte_start"] : field["locator"]["byte_end"]]
        == b"\xa2\xcc"
    )


@pytest.mark.parametrize(
    "options",
    [
        {},
        {"delimiter": "\t"},
        {"delimiter": ";", "quotechar": "'"},
        {"escapechar": "\\", "doublequote": False},
        {"quotechar": None, "escapechar": "\\"},
    ],
)
def test_native_locator_scanner_agrees_with_stdlib_csv(adapter, options):
    dialect = NativeDelimitedDialect(**options)
    randomizer = random.Random(243)  # noqa: S311 -- reproducible non-secret fixture
    alphabet = [
        "007",
        "-0.50",
        "comma,",
        "semi;",
        'quote"',
        "single'",
        "CR\rLF\nend",
        "tab\t",
        "back\\slash",
        "中文😀",
        "=SUM(A1:A2)",
        "",
    ]
    rows = [
        [randomizer.choice(alphabet) for _ in range(randomizer.randint(2, 7))]
        for _ in range(40)
    ]
    stream = io.StringIO(newline="")
    csv.writer(stream, **{**csv_options(dialect), "lineterminator": "\r\n"}).writerows(
        rows
    )
    data = stream.getvalue().encode()
    assert (
        list(csv.reader(io.StringIO(data.decode(), newline=""), **csv_options(dialect)))
        == rows
    )
    records = adapter.decompose(data, dialect)
    assert [r["value"] for r in records] == [v for row in rows for v in row]
    for record in records:
        loc = record["locator"]
        assert data[loc["byte_start"] : loc["byte_end"]].decode() == record["raw"]


def test_row_crud_preserves_existing_bytes_and_zero_field_records(adapter):
    dialect = NativeDelimitedDialect()
    data = b'"head",number\r\n\r"x","007"\nlast,tail'
    added, _ = edit(
        adapter,
        data,
        dialect,
        operation="insert_rows",
        index=1,
        rows=[["new", "001"], []],
        record_separator="\n",
    )
    assert added == b'"head",number\r\nnew,001\n\n\r"x","007"\nlast,tail'
    restored, _ = edit(
        adapter, added, dialect, operation="delete_rows", index=1, count=2
    )
    assert restored == data
    appended, report = edit(
        adapter,
        data,
        dialect,
        operation="insert_rows",
        index=4,
        rows=[["end", "002"]],
        record_separator="\r",
    )
    assert appended == data + b"\rend,002\r"
    assert report.repairs
    emptied, _ = edit(adapter, data, dialect, operation="delete_rows", index=0, count=4)
    assert emptied == b""
    born, _ = edit(
        adapter,
        emptied,
        dialect,
        operation="insert_rows",
        index=0,
        rows=[[], ["only"]],
        record_separator="\n",
    )
    assert born == b"\nonly\n" and adapter.inspect(born, dialect)["row_lengths"] == [
        0,
        1,
    ]


@pytest.mark.parametrize("index", [0, 1, 2])
def test_column_insertion_deletion_roundtrip_preserves_lexemes(adapter, index):
    dialect = NativeDelimitedDialect()
    data = b'"name",code\r\n"a,b","007"\nplain,"-0.50"'
    changed, _ = edit(
        adapter,
        data,
        dialect,
        operation="insert_column",
        index=index,
        values=["unit", "mg/L", ""],
    )
    restored, _ = edit(
        adapter, changed, dialect, operation="delete_columns", index=index, count=1
    )
    assert restored == data
    assert adapter.inspect(changed, dialect)["row_lengths"] == [3, 3, 3]


def test_all_columns_deleted_keep_final_empty_record(adapter):
    dialect = NativeDelimitedDialect()
    data = b'"a"\r\n"b"'
    changed, report = edit(
        adapter,
        data,
        dialect,
        operation="delete_columns",
        index=0,
        count=1,
        record_separator="\n",
    )
    assert changed == b"\r\n\n"
    assert adapter.inspect(changed, dialect)["row_lengths"] == [0, 0]
    assert report.repairs
    inserted, _ = edit(
        adapter,
        changed,
        dialect,
        operation="insert_column",
        index=0,
        values=["", "007"],
    )
    assert inserted == b'""\r\n007\n'


def test_ragged_rows_remain_readable_and_edits_do_not_pad(adapter):
    dialect = NativeDelimitedDialect()
    data = b"a,b\nx\n\n"
    assert adapter.inspect(data, dialect)["row_lengths"] == [2, 1, 0]
    for request in (
        {"operation": "insert_column", "index": 1, "values": ["1", "2", "3"]},
        {"operation": "delete_columns", "index": 0, "count": 1},
    ):
        with pytest.raises(ValueError, match=r"ragged|every"):
            edit(adapter, data, dialect, **request)
    changed, _ = edit(
        adapter,
        data,
        dialect,
        operation="insert_column",
        index=0,
        values=["1", "2", ""],
    )
    assert changed == b'1,a,b\n2,x\n""\n'


@pytest.mark.parametrize(
    "data", [b'"unterminated', b'"quoted"bad,x\n', b'"quoted" ,x\n']
)
def test_malformed_csv_fails_strictly(adapter, data):
    with pytest.raises((ValueError, csv.Error)):
        adapter.inspect(data, NativeDelimitedDialect())


def test_reference_and_encoding_conflicts_fail_before_edit(adapter):
    dialect = NativeDelimitedDialect()
    data = b'a,"007"\n'
    ref = reference(adapter, data, dialect, 0, 1)
    for field in ("value_sha256", "revision", "locator", "dialect"):
        bad = deepcopy(ref)
        if field in {"revision", "value_sha256"}:
            bad[field] = "0" * 64
        elif field == "locator":
            bad[field]["byte_start"] += 1
        else:
            bad[field]["delimiter"] = ";"
        with pytest.raises(ValueError):
            edit(
                adapter,
                data,
                dialect,
                operation="set_cells",
                cells=[{"reference": bad, "value": "008"}],
            )
    with pytest.raises(ValueError, match="twice"):
        edit(
            adapter,
            data,
            dialect,
            operation="set_cells",
            cells=[{"reference": ref, "value": "008"}] * 2,
        )
    with pytest.raises(ValueError, match="BOM"):
        adapter.inspect(
            codecs.BOM_UTF8 + data, NativeDelimitedDialect(encoding="cp950")
        )
    with pytest.raises(UnicodeDecodeError):
        adapter.inspect(b"\xff", dialect)
    data = b"a,b\n"
    legacy = NativeDelimitedDialect(encoding="cp1252")
    with pytest.raises(UnicodeEncodeError):
        edit(
            adapter,
            data,
            legacy,
            operation="set_cells",
            cells=[
                {"reference": reference(adapter, data, legacy, 0, 0), "value": "中文"}
            ],
        )


def test_creation_retains_string_types_bom_and_final_separator_policy(adapter):
    data, report = adapter.create(
        NativeDelimitedCreate(
            name="table.tsv",
            rows=[["007", "-0.50", "=1+2"], ["中文", "", "x\ny"]],
            dialect=NativeDelimitedDialect(delimiter="\t", encoding="utf-16-le"),
            bom=True,
            record_separator="\n",
            final_separator=False,
        )
    )
    assert data.startswith(codecs.BOM_UTF16_LE)
    assert data[2:].decode("utf-16-le") == '007\t-0.50\t=1+2\n中文\t\t"x\ny"'
    assert report.review_required
    with pytest.raises(ValueError, match="final separator"):
        adapter.create(NativeDelimitedCreate(rows=[[]], final_separator=False))


def test_worker_large_field_does_not_change_parent_csv_limit():
    limit = csv.field_size_limit()
    value = "a" * 200_000
    result = ProcessNativeDelimited().read_cell(
        (value + ",007\n").encode(), NativeDelimitedDialect(), 0, 0
    )
    assert result["value"] == value and csv.field_size_limit() == limit


@pytest.mark.parametrize(
    "data,index", [(b"remove,\n", 0), (b",remove\r\n", 1), (b"remove,", 0)]
)
def test_deleting_column_retains_one_empty_field_not_zero_field_row(
    adapter, data, index
):
    changed, report = edit(
        adapter,
        data,
        NativeDelimitedDialect(),
        operation="delete_columns",
        index=index,
        count=1,
    )
    assert list(csv.reader(io.StringIO(changed.decode(), newline=""))) == [[""]]
    assert changed.startswith(b'""')
    assert "one-field logical row" in report.repairs[0]


def test_independent_codex_auditor_rejects_rehashed_wrong_field_span(adapter):
    from tests.codex_delimited.audit import check_field, expected_revisions
    from tests.codex_native_pdf.trace import canonical, digest

    data = expected_revisions()[0]
    field = adapter.read_cell(data, NativeDelimitedDialect(), 1, 0)
    attach_delimited_evidence(field, "file_" + "a" * 32, digest(data))
    check_field(field, data)
    changed = deepcopy(field)
    changed["locator"]["byte_start"] += 1
    changed["evidence"]["locator"] = dict(changed["locator"])
    changed["evidence"]["value_sha256"] = digest(
        canonical({k: v for k, v in changed.items() if k != "evidence"})
    )
    with pytest.raises(ValueError, match="span"):
        check_field(changed, data)
    changed = deepcopy(field)
    changed["value"] = "7"
    changed["evidence"]["value_sha256"] = digest(
        canonical({k: v for k, v in changed.items() if k != "evidence"})
    )
    with pytest.raises(ValueError, match="transcription"):
        check_field(changed, data)
