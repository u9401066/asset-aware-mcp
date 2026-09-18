"""The live auditor requires complete, correctly bound MCP citation responses."""

from __future__ import annotations

import copy
import hashlib
import json

import pytest

from tests.codex_pdf.citation_readback import validate_citation_readbacks


def fixture():
    table = {
        "id": "tbl_test",
        "row_ids": ["row_1"],
        "rows": [{"Reading": "0007"}],
        "citations": {
            "rid:row_1:Reading": {
                "refs": [
                    {
                        "source_type": "figure",
                        "doc_id": "doc_pdf",
                        "asset_id": "fig_3_1",
                        "page": 3,
                    }
                ],
                "notes": "µ μ\n" * 100,
            }
        },
    }
    record = {
        "schema_version": "a2t-cell-citation-v1",
        "table_id": "tbl_test",
        "row_id": "row_1",
        "column_name": "Reading",
        "value": "0007",
        "citation": table["citations"]["rid:row_1:Reading"],
    }
    return table, page_calls(record)


def page_calls(record):
    text = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(text.encode()).hexdigest()
    calls = []
    for start in range(0, len(text), 200):
        end = min(start + 200, len(text))
        page = {
            "schema_version": "a2t-citation-page-v1",
            "citation_sha256": digest,
            "text_excerpt": text[start:end],
            "text_length": len(text),
            "excerpt_char_range": [start, end],
            "next_text_offset": end if end < len(text) else None,
            "representation_complete": start == 0 and end == len(text),
        }
        calls.append(
            {
                "tool": "table_cite",
                "arguments": {
                    "operation": "read",
                    "table_id": record["table_id"],
                    "row_id": "row_1",
                    "column_name": "Reading",
                    "text_offset": start,
                    "citation_sha256": digest if start else "",
                },
                "result": {"content": [{"type": "text", "text": json.dumps(page)}]},
            }
        )
    return calls


def test_complete_readbacks_and_identical_retries_pass():
    table, calls = fixture()
    validate_citation_readbacks(table, [calls[0], *calls], require_paging=True)


def test_required_paging_cannot_pass_on_only_complete_inline_records():
    table, calls = fixture()
    pages = [json.loads(call["result"]["content"][0]["text"]) for call in calls]
    full = "".join(page["text_excerpt"] for page in pages)
    pages[0].update(
        text_excerpt=full,
        excerpt_char_range=[0, len(full)],
        next_text_offset=None,
        representation_complete=True,
    )
    calls[0]["result"]["content"][0]["text"] = json.dumps(pages[0])
    validate_citation_readbacks(table, [calls[0]])
    with pytest.raises(ValueError, match="continuation"):
        validate_citation_readbacks(table, [calls[0]], require_paging=True)


@pytest.mark.parametrize(
    "mutation", ["missing", "summary", "stale", "wrong_row", "wrong_table", "unpinned"]
)
def test_agent_cannot_substitute_partial_or_wrong_readbacks(mutation):
    table, calls = fixture()
    if mutation == "missing":
        calls.pop()
    elif mutation == "summary":
        for call in calls:
            call["arguments"]["operation"] = "get"
    elif mutation == "stale":
        calls.append(
            {
                "tool": "table_cite",
                "arguments": {"table_id": table["id"], "operation": "add"},
            }
        )
    elif mutation == "wrong_table":
        for call in calls:
            call["arguments"]["table_id"] = "other"
    elif mutation == "wrong_row":
        calls[0]["arguments"]["row_id"] = "wrong_row"
    else:
        calls[1]["arguments"]["citation_sha256"] = ""
    with pytest.raises(ValueError):
        validate_citation_readbacks(table, calls)


@pytest.mark.parametrize(
    "field,value",
    [
        ("text_excerpt", "fake"),
        ("citation_sha256", "a" * 64),
        ("next_text_offset", None),
        ("representation_complete", True),
        ("excerpt_char_range", [1, 201]),
        ("schema_version", "preview-v1"),
    ],
)
def test_corrupted_pages_fail(field, value):
    table, calls = fixture()
    page = json.loads(calls[0]["result"]["content"][0]["text"])
    page[field] = value
    calls[0]["result"]["content"][0]["text"] = json.dumps(page)
    with pytest.raises(ValueError):
        validate_citation_readbacks(table, calls)


@pytest.mark.parametrize("field", ["value", "citation"])
def test_delivered_snapshot_must_equal_final_persisted_state(field):
    table, calls = fixture()
    if field == "value":
        table["rows"][0]["Reading"] = "7"
    else:
        table = copy.deepcopy(table)
        table["citations"]["rid:row_1:Reading"]["refs"][0]["page"] = 2
    with pytest.raises(ValueError, match="final persisted"):
        validate_citation_readbacks(table, calls)
