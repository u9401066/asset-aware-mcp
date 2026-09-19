"""Missing pages, wrong hashes and omitted current receipts cannot count as proof."""

import json
from copy import deepcopy

import pytest

from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_table_grid.audit import (
    _check_receipts,
    _identity_check,
    expected_values,
)
from tests.codex_table_grid.reads import read_events
from tests.unit.test_codex_table_audit import call


def workspace_pages():
    table = {"id": "tbl_test", "rows": [{"A": "007"}]}
    value = canonical({"table": table}).decode()
    table_sha, text_sha = digest(canonical(table)), digest(value.encode())
    split = len(value) // 2
    calls = []
    for start, end in [(0, split), (split, len(value))]:
        calls.append(
            call(
                {
                    "op": "read_table_workspace",
                    "table_id": "tbl_test",
                    "table_sha256": table_sha,
                    "text_offset": start,
                },
                {
                    "table_id": "tbl_test",
                    "table_sha256": table_sha,
                    "text_sha256": text_sha,
                    "text_excerpt": value[start:end],
                    "excerpt_char_range": [start, end],
                    "next_text_offset": end if end < len(value) else None,
                },
            )
        )
    return calls


def test_complete_workspace_pages_and_omitted_completion():
    calls = workspace_pages()
    assert len(list(read_events(calls))) == 1
    assert list(read_events(calls[:1])) == []
    with pytest.raises(ValueError, match="Noncontiguous"):
        list(read_events(calls[1:]))


@pytest.mark.parametrize("field", ["text_sha256", "table_sha256", "text_excerpt"])
def test_structural_read_proof_rejects_forged_values(field):
    calls = workspace_pages()
    result = json.loads(calls[1]["result"]["content"][0]["text"])
    result[field] = "f" * 64
    calls[1] = call(calls[1]["arguments"]["native_request"], result)
    with pytest.raises(ValueError):
        list(read_events(calls))


def test_current_receipt_and_before_read_are_both_required():
    receipt = {"changes": [{"op": "apply_table_workspace"}]}
    target = {
        "asset_id": "file_test",
        "revision": "new",
        "history": [{"sha256": "old"}, {"sha256": "new", "result": receipt}],
    }
    request = {
        "op": "read_workbook",
        "asset_id": "file_test",
        "workbook_view": "references",
    }
    reads = [
        (0, request, {"references": []}, "old"),
        (2, request, {"references": [], "operation_result": receipt}, "new"),
    ]
    _check_receipts(reads, 1, target)
    for index in (0, 1):
        with pytest.raises(ValueError, match="Missing complete"):
            _check_receipts(
                [item for i, item in enumerate(reads) if i != index], 1, target
            )
    bad = deepcopy(reads)
    bad[1][2]["operation_result"] = {"changes": []}
    with pytest.raises(ValueError, match="receipt differs"):
        _check_receipts(bad, 1, target)


def test_recreated_rows_and_columns_do_not_reuse_source_identities():
    original = {
        "row_ids": ["r1", "r2", "r3"],
        "column_ids": list("abcde"),
        "native_binding": {},
        "rows": [
            dict(
                zip(
                    "ABCDE",
                    [{"kind": "string", "value": value} for value in row],
                    strict=True,
                )
            )
            for row in expected_values(False)
        ],
    }
    names = ["A", "B", "C", "D", "Review"]
    current = {
        "row_ids": ["r1", "r2", "r4", "r5"],
        "column_ids": list("abcdf"),
        "native_binding": {},
        "columns": [{"name": name} for name in names],
        "rows": [
            dict(
                zip(
                    names,
                    [{"kind": "string", "value": value} for value in row],
                    strict=True,
                )
            )
            for row in expected_values(True)
        ],
    }
    _identity_check(original, current)
    for field, index, old_id in [("row_ids", 2, "r3"), ("column_ids", 4, "e")]:
        bad = deepcopy(current)
        bad[field][index] = old_id
        with pytest.raises(ValueError, match="identity reused"):
            _identity_check(original, bad)
