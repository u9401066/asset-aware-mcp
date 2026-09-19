"""Bridge audit rejects missing prior reads and invented snapshot hashes."""

import json
from copy import deepcopy

import pytest

from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_native_table.audit import workspace_reads


def call(args, result):
    return {
        "tool": "document",
        "arguments": {"native_request": args},
        "result": {"content": [{"type": "text", "text": json.dumps(result)}]},
    }


def trace():
    table_id = "tbl_test"
    calls = []
    for value in ("007", "008"):
        table = {"id": table_id, "rows": [{"B": {"kind": "string", "value": value}}]}
        text = canonical({"table": table}).decode()
        sha = digest(canonical(table))
        read = call(
            {"op": "read_table_workspace", "table_id": table_id},
            {
                "table_id": table_id,
                "table_sha256": sha,
                "text_sha256": digest(text.encode()),
                "text_excerpt": text,
                "excerpt_char_range": [0, len(text)],
                "next_text_offset": None,
            },
        )
        calls.append(read)
        if value == "007":
            calls.append(
                {
                    "tool": "table_data",
                    "arguments": {"operation": "update_cell", "table_id": table_id},
                }
            )
    reference = {"asset_id": "file_" + "a" * 32, "revision": sha}
    args = {
        "op": "apply_table_workspace",
        "table_id": table_id,
        "expected_table_sha256": sha,
    }
    result = {"table_sha256": sha, "workspace_reference": reference}
    calls.append(call(args, result))
    frozen = deepcopy(read)
    frozen["arguments"]["native_request"]["workspace_reference"] = reference
    calls.append(frozen)
    calls.append(call({"op": "verify", "reference": reference}, {"valid": True}))
    calls.append(
        call(
            {
                **args,
                "op": "create_workbook_from_table",
                "workspace_reference": reference,
            },
            result,
        )
    )
    return calls


def test_workspace_audit_requires_prior_full_read_and_frozen_proof():
    calls = trace()
    assert len(workspace_reads(calls)[0]) == 2
    bad = deepcopy(calls)
    bad[0], bad[1] = bad[1], bad[0]
    with pytest.raises(ValueError, match="A2T edit precedes"):
        workspace_reads(bad)
    bad = deepcopy(calls)
    bad[2], bad[3] = bad[3], bad[2]
    with pytest.raises(ValueError, match="Native mutation precedes"):
        workspace_reads(bad)
    for omitted in (4, 5):
        with pytest.raises(ValueError, match="Creation precedes"):
            workspace_reads(
                [value for index, value in enumerate(calls) if index != omitted]
            )


def test_workspace_audit_rejects_forged_read_and_snapshot_hashes():
    for index, field, message in (
        (0, "text_sha256", "read hash"),
        (3, "table_sha256", "snapshot hash"),
    ):
        bad = trace()
        result = json.loads(bad[index]["result"]["content"][0]["text"])
        result[field] = "f" * 64
        bad[index] = call(bad[index]["arguments"]["native_request"], result)
        with pytest.raises(ValueError, match=message):
            workspace_reads(bad)
