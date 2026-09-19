"""Layout proof requires complete revision- and sheet-bound MCP records."""

import hashlib
import json

import pytest

from tests.codex_workbook_layout.audit import calls_from, layouts
from tests.unit.test_codex_rendition_audit import receipt_call


@pytest.mark.parametrize(
    "fault", ["missing", "unfinished", "altered_hash", "wrong_sheet", "wrong_revision"]
)
def test_layout_audit_rejects_incomplete_or_misattributed_records(fault):
    key = {"sheet_id": "1", "part": "xl/worksheets/sheet1.xml"}
    record = {"revision": "revision", "worksheet": {"key": key}, "layout": {}}
    text = json.dumps(record)
    digest = hashlib.sha256(text.encode()).hexdigest()
    calls = [
        receipt_call(text, 0, 5, digest, 5),
        receipt_call(text, 5, len(text), digest, None),
    ]
    for call in calls:
        call["arguments"]["native_request"].update(
            op="read_worksheet_layout", worksheet_key=dict(key)
        )
    assert layouts(calls) == {("asset", "revision", key["part"]): record}
    if fault == "missing":
        calls = calls[1:]
    elif fault == "unfinished":
        calls = calls[:1]
    elif fault == "wrong_sheet":
        for call in calls:
            call["arguments"]["native_request"]["worksheet_key"]["sheet_id"] = "2"
    elif fault == "wrong_revision":
        calls[0]["arguments"]["native_request"]["revision"] = "other"
    else:
        result = json.loads(calls[0]["result"]["content"][0]["text"])
        result["text_sha256"] = "0" * 64
        calls[0]["result"]["content"][0]["text"] = json.dumps(result)
    with pytest.raises(ValueError):
        layouts(calls)


def test_layout_agent_prose_is_not_an_operation_receipt():
    for item in (
        {"type": "agent_message", "text": "All fixed"},
        {"type": "command_execution"},
    ):
        with pytest.raises(ValueError):
            calls_from(
                [{"type": "turn.completed"}, {"type": "item.completed", "item": item}]
            )
