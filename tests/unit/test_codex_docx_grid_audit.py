"""Evaluation rejects unauthorized tools, missing operations and incomplete reads."""

from __future__ import annotations

import json

import pytest

from tests.codex_docx_grid.audit import calls_from, validate_reads, validate_receipt


@pytest.mark.parametrize("fault", [None, "missing", "truncated", "earlier"])
def test_complete_receipt_audit_checks_latest_matching_history(fault):
    old = {"changes": [{"request": "first"}]}
    latest = {"changes": [{"request": "later"}]}
    target = {
        "history": [
            {"sha256": "same", "result": old},
            {"sha256": "same", "result": latest},
        ]
    }
    record = {"operation_result": latest}
    if fault == "missing":
        record = {}
    elif fault == "truncated":
        record = {"operation_result": {"changes": []}}
    elif fault == "earlier":
        record = {"operation_result": old}
    if fault:
        with pytest.raises(ValueError, match="receipt"):
            validate_receipt(record, target, "same")
    else:
        validate_receipt(record, target, "same")


OPS = [
    "contract",
    "register",
    "render_pdf_page",
    "read_pdf_page",
    "create_docx",
    "read_docx",
    "read_docx_table",
    "update_docx_table_grid",
    "render_docx_page",
    "verify",
    "publish",
    "export_wiki",
    "history",
]


def call(op, result=None, **fields):
    return {
        "type": "mcp_tool_call",
        "server": "asset_aware_under_test",
        "tool": "document",
        "arguments": {"op": "native", "native_request": {"op": op, **fields}},
        "status": "completed",
        "result": {
            "content": [
                {"type": "text", "text": json.dumps(result or {"success": True})}
            ]
        },
    }


@pytest.mark.parametrize(
    "fault", [None, "shell", "other_server", "writeback", "missing", "unfinished"]
)
def test_grid_evaluation_requires_real_restricted_complete_workflow(fault):
    events = [
        {"type": "turn.completed"},
        *({"type": "item.completed", "item": call(op)} for op in OPS),
    ]
    if fault == "shell":
        events.append({"type": "item.completed", "item": {"type": "command_execution"}})
    elif fault == "other_server":
        events[1]["item"]["server"] = "unrelated"
    elif fault == "writeback":
        events.append({"type": "item.completed", "item": call("writeback")})
    elif fault == "missing":
        events.pop(OPS.index("update_docx_table_grid") + 1)
    elif fault == "unfinished":
        events.pop(0)
    if fault:
        with pytest.raises(ValueError):
            calls_from(events)
    else:
        events.append({"type": "item.completed", "item": call("schema")})
        assert len(calls_from(events)) == len(OPS) + 1


@pytest.mark.parametrize(
    "fault",
    ["unpinned", "range", "gap", "hash", "continuation", "mutation_before_read"],
)
def test_grid_read_audit_rejects_incomplete_or_unbound_evidence(tmp_path, fault):
    section = {
        "text_excerpt": "{}",
        "excerpt_char_range": [0, 2],
        "text_length": 2,
        "text_sha256": "incorrect",
        "next_text_offset": None,
    }
    fields = {"asset_id": "target", "revision": "revision"}
    if fault == "unpinned":
        fields.pop("revision")
    elif fault == "range":
        section["excerpt_char_range"] = [0, 3]
    elif fault == "gap":
        section["excerpt_char_range"] = [2, 4]
        fields["text_offset"] = 2
    elif fault == "continuation":
        section["next_text_offset"] = 3
    item = call(
        "read_docx_table",
        {"asset_id": "target", "inspected_revision": "revision", "table": section},
        **fields,
    )
    if fault == "mutation_before_read":
        item = call(
            "update_docx_table_grid",
            docx_table_grid={"reference": {}},
            asset_id="target",
            expected_revision="revision",
        )
    with pytest.raises(ValueError):
        validate_reads([item], tmp_path, {"asset_id": "target"}, {"asset_id": "source"})
