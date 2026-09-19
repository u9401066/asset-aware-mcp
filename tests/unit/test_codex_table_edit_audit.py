"""Actual Table audit accepts real schema discovery and rejects incomplete proof."""

from copy import deepcopy

import pytest

from tests.codex_native_pdf.trace import digest
from tests.codex_table_edit.audit import (
    calls_from,
    check_header_evidence,
    check_original_receipt,
)
from tests.unit.test_codex_table_audit import call


def workflow_events():
    events = [{"type": "turn.completed"}]
    for op in (
        "register",
        "contract",
        "schema",
        "read_pdf_page",
        "render_pdf_page",
        "update",
        "update_workbook_table",
        "read_workbook",
        "read_cell",
        "verify",
        "history",
        "publish",
        "export_wiki",
    ):
        item = call({"op": op}, {})
        item.update(
            type="mcp_tool_call", server="asset_aware_under_test", status="completed"
        )
        item["arguments"]["op"] = "native"
        events.append({"type": "item.completed", "item": item})
    return events


def test_real_schema_discovery_is_allowed_but_source_writeback_is_not():
    events = workflow_events()
    assert any(
        c["arguments"]["native_request"]["op"] == "schema" for c in calls_from(events)
    )
    extra = deepcopy(events[-1])
    extra["item"]["arguments"]["native_request"]["op"] = "writeback"
    with pytest.raises(ValueError, match="Unexpected native operation"):
        calls_from([*events, extra])


def test_formula_receipt_cannot_substitute_a_renamed_intermediate_for_original():
    cells = {
        location: {
            "before": {"value": "=LEN([[#This Row],Count])"},
            "after": {"value": "=LEN([@Quantity])+1"},
        }
        for location in ("F2", "F3")
    }
    check_original_receipt(cells)
    cells["F2"]["before"]["value"] = "=LEN([[#This Row],Quantity])"
    with pytest.raises(ValueError, match="original revision"):
        check_original_receipt(cells)


@pytest.mark.parametrize(
    "case", ["missing", "partial", "range", "hash", "current_proof"]
)
def test_header_evidence_needs_complete_historical_reads_and_exact_proof(case):
    target = {"asset_id": "file_test"}
    reference = {
        "asset_id": "file_test",
        "revision": "baseline",
        "locator": {"cell": "B1"},
    }
    args = {
        "op": "read_cell",
        "asset_id": "file_test",
        "revision": "baseline",
        "cell": "B1",
    }
    record = {
        "cell": {
            "representation_complete": True,
            "next_text_offset": None,
            "excerpt_char_range": [0, 5],
            "value_excerpt": "Count",
            "value_text_sha256": digest(b"Count"),
            "evidence": reference,
        }
    }
    calls = [
        call(args, record),
        call({"op": "inspect"}, {}),
        call(args, record),
        call(
            {"op": "verify", "reference": reference},
            {"valid": True, "is_current_managed_revision": False},
        ),
    ]
    check_header_evidence(calls, 1, target, "baseline")
    altered = deepcopy(record)
    if case == "missing":
        calls[2] = call({"op": "inspect"}, {})
    elif case == "current_proof":
        calls[3] = call(
            {"op": "verify", "reference": reference},
            {"valid": True, "is_current_managed_revision": True},
        )
    else:
        key, value = {
            "partial": ("next_text_offset", 5),
            "range": ("excerpt_char_range", [1, 6]),
            "hash": ("value_text_sha256", digest(b"Quantity")),
        }[case]
        altered["cell"][key] = value
        calls[2] = call(args, altered)
    with pytest.raises(ValueError, match=r"[Hh]istorical"):
        check_header_evidence(calls, 1, target, "baseline")
