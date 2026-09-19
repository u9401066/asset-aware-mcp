"""Independent proof audit rejects omitted chunks, altered receipts and non-MCP work."""

import hashlib
import json

import pytest

from tests.codex_workbook_rendition.audit import calls_from, receipts


def receipt_call(text, start, end, digest, next_offset):
    return {
        "arguments": {
            "native_request": {
                "op": "read_rendition",
                "asset_id": "asset",
                "revision": "revision",
                "text_offset": start,
            }
        },
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "inspected_revision": "revision",
                            "text_sha256": digest,
                            "excerpt_char_range": [start, end],
                            "text_excerpt": text[start:end],
                            "next_text_offset": next_offset,
                        }
                    ),
                }
            ]
        },
    }


@pytest.mark.parametrize(
    "fault", ["missing", "unfinished", "altered_hash", "wrong_revision"]
)
def test_incomplete_or_inconsistent_receipt_is_not_proof(fault):
    text = '{"value":"原文"}'
    digest = hashlib.sha256(text.encode()).hexdigest()
    calls = [
        receipt_call(text, 0, 5, digest, 5),
        receipt_call(text, 5, len(text), digest, None),
    ]
    assert receipts(calls) == {("asset", "revision"): {"value": "原文"}}
    if fault == "missing":
        calls = calls[1:]
    elif fault == "unfinished":
        calls = calls[:1]
    elif fault == "altered_hash":
        calls = [receipt_call(text, 0, len(text), "0" * 64, None)]
    else:
        calls[0]["arguments"]["native_request"]["revision"] = "other"
    with pytest.raises(ValueError):
        receipts(calls)


def test_agent_prose_or_shell_cannot_substitute_for_native_calls():
    for item in (
        {"type": "agent_message", "text": "Everything passed"},
        {"type": "command_execution"},
    ):
        with pytest.raises(ValueError):
            calls_from(
                [{"type": "turn.completed"}, {"type": "item.completed", "item": item}]
            )
