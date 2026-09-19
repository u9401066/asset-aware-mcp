"""An auditor must reject missing prior reads and forged revision transitions."""

import json
from copy import deepcopy

import pytest

from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_native_workbook.audit import workbook_reads


def trace():
    target = {
        "asset_id": "file_" + "a" * 32,
        "history": [{"sha256": str(i) * 64} for i in range(7)],
    }
    calls = []
    operations = [
        "add_worksheets",
        "update",
        "rename_worksheet",
        "reorder_worksheets",
        "delete_worksheets",
    ]
    for index in range(1, 7):
        revision = str(index) * 64
        record = {
            "asset_id": target["asset_id"],
            "revision": revision,
            "references": [],
        }
        text = canonical(record).decode()
        args = {
            "op": "read_workbook",
            "asset_id": target["asset_id"],
            "revision": revision,
            "workbook_view": "references",
        }
        result = {
            "inspected_revision": revision,
            "text_excerpt": text,
            "text_sha256": digest(text.encode()),
            "excerpt_char_range": [0, len(text)],
            "next_text_offset": None,
        }
        calls.append(call(args, result))
        if index < 6:
            args = {
                "op": operations[index - 1],
                "asset_id": target["asset_id"],
                "expected_revision": revision,
                "edits": [{"sheet": "Review"}],
            }
            calls.append(call(args, {"asset": {"revision": str(index + 1) * 64}}))
    return calls, target


def call(args, result):
    return {
        "arguments": {"native_request": args},
        "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
    }


def test_workbook_audit_requires_prior_complete_reference_read():
    calls, target = trace()
    assert len(workbook_reads(calls, target)) == 6
    bad = deepcopy(calls)
    bad[0], bad[1] = bad[1], bad[0]
    with pytest.raises(ValueError, match="precedes complete"):
        workbook_reads(bad, target)


def test_workbook_audit_rejects_forged_revision_result_and_read_hash():
    calls, target = trace()
    bad = deepcopy(calls)
    bad[1] = call(
        bad[1]["arguments"]["native_request"], {"asset": {"revision": "f" * 64}}
    )
    with pytest.raises(ValueError, match="exact revision chain"):
        workbook_reads(bad, target)
    bad = deepcopy(calls)
    result = json.loads(bad[0]["result"]["content"][0]["text"])
    result["text_sha256"] = "f" * 64
    bad[0] = call(bad[0]["arguments"]["native_request"], result)
    with pytest.raises(ValueError, match="hash mismatch"):
        workbook_reads(bad, target)
