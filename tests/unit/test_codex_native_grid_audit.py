"""Grid evaluation fails on forged histories, incomplete reads and wrong cell mapping."""

import io
import json
from copy import deepcopy

import pytest
import xlsxwriter

from tests.codex_native_grid.audit import complete_workbook_reads, validate_values
from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_pdf.fixtures import COLUMNS, PAGE_ROWS
from tests.unit.test_codex_workbook_audit import call


def trace():
    target = {
        "asset_id": "file_" + "a" * 32,
        "revision": "3" * 64,
        "history": [{"sha256": str(index) * 64} for index in range(4)],
    }
    calls = []
    for index in range(1, 4):
        revision = str(index) * 64
        text = canonical(
            {"asset_id": target["asset_id"], "revision": revision, "references": []}
        ).decode()
        calls.append(
            call(
                {
                    "op": "read_workbook",
                    "asset_id": target["asset_id"],
                    "revision": revision,
                    "workbook_view": "references",
                },
                {
                    "inspected_revision": revision,
                    "text_excerpt": text,
                    "text_sha256": digest(text.encode()),
                    "excerpt_char_range": [0, len(text)],
                    "next_text_offset": None,
                },
            )
        )
        if index < 3:
            operation = "insert" if index == 1 else "delete"
            calls.append(
                call(
                    {
                        "op": "update_worksheet_grid",
                        "asset_id": target["asset_id"],
                        "expected_revision": revision,
                        "worksheet_grid": {
                            "worksheet": {
                                "sheet_id": "1",
                                "part": "xl/worksheets/sheet1.xml",
                            },
                            "edits": [
                                {"axis": "row", "operation": operation, "at": 2},
                                {"axis": "column", "operation": operation, "at": 3},
                            ],
                        },
                    },
                    {"asset": {"revision": str(index + 1) * 64}},
                )
            )
    return calls, target


@pytest.mark.parametrize(
    "tamper", ["read_order", "hash", "revision", "location", "final_read", "receipt"]
)
def test_trace_audit_rejects_incomplete_or_forged_grid_proof(tamper):
    calls, target = trace()
    complete_workbook_reads(calls, target)
    bad = deepcopy(calls)
    if tamper == "read_order":
        bad[0], bad[1] = bad[1], bad[0]
    elif tamper == "hash":
        result = json.loads(bad[0]["result"]["content"][0]["text"])
        result["text_sha256"] = "f" * 64
        bad[0] = call(bad[0]["arguments"]["native_request"], result)
    elif tamper == "revision":
        bad[1] = call(
            bad[1]["arguments"]["native_request"], {"asset": {"revision": "f" * 64}}
        )
    elif tamper == "location":
        bad[1]["arguments"]["native_request"]["worksheet_grid"]["edits"][0]["at"] = 1
    elif tamper == "receipt":
        target["history"][1]["result"] = {"checks": ["forged"]}
    else:
        bad.pop()
    with pytest.raises(ValueError):
        complete_workbook_reads(bad, target)


def value_fixture(*, bad_blank=False, wrong_row=False):
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        sheet = book.add_worksheet("Sheet1")
        rows = [list(COLUMNS), *[list(row) for row in PAGE_ROWS[0]]]
        rows[1][1] = "008"
        for index, row in enumerate(rows):
            for column, value in enumerate(row):
                destination_row = index + int(index >= 1)
                if wrong_row and index == 1:
                    destination_row -= 1
                sheet.write_string(destination_row, column + int(column >= 2), value)
        if bad_blank:
            sheet.write_string("C2", "unexpected")
    return output.getvalue()


def test_independent_package_reader_checks_all_shifted_literals_and_inserted_blanks():
    validate_values(value_fixture(), 2)
    with pytest.raises(ValueError, match="literal or blank"):
        validate_values(value_fixture(bad_blank=True), 2)
    with pytest.raises(ValueError, match="literal or blank"):
        validate_values(value_fixture(wrong_row=True), 2)


def test_exploratory_unpinned_read_cannot_replace_required_pinned_read():
    calls, target = trace()
    exploratory = deepcopy(calls[0])
    exploratory["arguments"]["native_request"].pop("revision")
    complete_workbook_reads([exploratory, *calls], target)
    with pytest.raises(ValueError, match="precedes complete"):
        complete_workbook_reads([exploratory, *calls[1:]], target)


def test_restored_content_hash_requires_a_new_final_receipt_read():
    calls, target = trace()
    target["revision"] = target["history"][3]["sha256"] = "1" * 64
    calls[3] = call(
        calls[3]["arguments"]["native_request"], {"asset": {"revision": "1" * 64}}
    )
    original_result = {"operation": "original_update"}
    restored_result = {"operation": "restore_grid"}
    target["history"][1]["result"] = original_result
    target["history"][3]["result"] = restored_result
    for index, receipt in ((0, original_result), (4, restored_result)):
        args = calls[index]["arguments"]["native_request"]
        args["revision"] = "1" * 64
        text = canonical(
            {
                "asset_id": target["asset_id"],
                "revision": "1" * 64,
                "references": [],
                "operation_result": receipt,
            }
        ).decode()
        calls[index] = call(
            args,
            {
                "inspected_revision": "1" * 64,
                "text_excerpt": text,
                "text_sha256": digest(text.encode()),
                "excerpt_char_range": [0, len(text)],
                "next_text_offset": None,
            },
        )
    complete_workbook_reads(calls, target)
    with pytest.raises(ValueError, match="Final grid receipt"):
        complete_workbook_reads(calls[:-1], target)
