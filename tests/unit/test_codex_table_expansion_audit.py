"""Incomplete or altered trace evidence cannot certify native Table expansion."""

from copy import deepcopy

import pytest

from tests.codex_native_pdf.trace import digest
from tests.codex_table_expansion.audit import (
    check_historical_cell,
    check_transcription_read,
)
from tests.unit.test_codex_table_audit import call


def historical_trace():
    target = {
        "asset_id": "file_test",
        "history": [{"sha256": "template"}, {"sha256": "baseline"}],
    }
    reference = {
        "asset_id": "file_test",
        "revision": "baseline",
        "locator": {"cell": "B2"},
    }
    args = {
        "op": "read_cell",
        "asset_id": "file_test",
        "revision": "baseline",
        "cell": "B2",
    }
    record = {
        "cell": {
            "cell": "B2",
            "representation_complete": True,
            "next_text_offset": None,
            "excerpt_char_range": [0, 3],
            "value_excerpt": "007",
            "value_text_sha256": digest(b"007"),
            "evidence": reference,
        }
    }
    return (
        target,
        args,
        record,
        [
            call(args, record),
            {"tool": "table_data"},
            call(args, record),
            call(
                {"op": "verify", "reference": reference},
                {"valid": True, "is_current_managed_revision": False},
            ),
        ],
    )


@pytest.mark.parametrize(
    "case",
    ["initial", "reread", "verification", "value", "hash", "partial", "reference"],
)
def test_historical_cell_requires_complete_matching_reads_and_verification(case):
    target, args, record, calls = historical_trace()
    check_historical_cell(calls, 1, target)
    if case in {"initial", "reread", "verification"}:
        calls[{"initial": 0, "reread": 2, "verification": 3}[case]] = {
            "tool": "table_data"
        }
    else:
        altered = deepcopy(record)
        if case == "value":
            altered["cell"]["value_excerpt"] = "008"
        elif case == "hash":
            altered["cell"]["value_text_sha256"] = digest(b"008")
        elif case == "partial":
            altered["cell"]["next_text_offset"] = 3
        else:
            altered["cell"]["evidence"]["revision"] = "current"
        calls[2] = call(args, altered)
    with pytest.raises(ValueError, match=r"Historical|historical"):
        check_historical_cell(calls, 1, target)


@pytest.mark.parametrize("case", ["missing", "late", "unpinned", "duplicate_update"])
def test_transcription_requires_complete_original_references_and_one_exact_update(case):
    target = {"asset_id": "file_test"}
    expected = {"template_sha256": "template"}
    request = {
        "op": "read_workbook",
        "asset_id": "file_test",
        "workbook_view": "references",
    }
    reads = [(0, request, {"references": []}, "template")]
    calls = [
        {"tool": "table_data"},
        call(
            {"op": "update", "asset_id": "file_test", "expected_revision": "template"},
            {},
        ),
    ]
    check_transcription_read(calls, reads, target, expected)
    if case == "missing":
        reads = []
    elif case == "late":
        reads[0] = (2, *reads[0][1:])
    elif case == "unpinned":
        calls[-1]["arguments"]["native_request"].pop("expected_revision")
    else:
        calls.append(calls[-1])
    with pytest.raises((ValueError, KeyError)):
        check_transcription_read(calls, reads, target, expected)
