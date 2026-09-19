"""Evaluation cannot accept unauthorized edits, incomplete reads or unviewed pages."""

from __future__ import annotations

import io
import json
from zipfile import ZipFile

import pytest
from lxml import etree

from tests.codex_docx_layout.audit import REQUIRED, W, calls_from, validate_reads
from tests.codex_native_pdf.trace import digest
from tests.native_docx_layout_helpers import ROWS, clipped_document
from tests.unit.test_codex_docx_grid_audit import call


@pytest.mark.parametrize(
    "fault", [None, "shell", "writeback", "missing", "unfinished", "foreign"]
)
def test_layout_agent_audit_requires_restricted_completed_workflow(fault):
    events = [
        {"type": "turn.completed"},
        *[{"type": "item.completed", "item": call(op)} for op in sorted(REQUIRED)],
    ]
    if fault == "shell":
        events.append({"type": "item.completed", "item": {"type": "command_execution"}})
    elif fault == "writeback":
        events.append({"type": "item.completed", "item": call("writeback")})
    elif fault == "missing":
        events.pop()
    elif fault == "unfinished":
        events.pop(0)
    elif fault == "foreign":
        events[1]["item"]["server"] = "other"
    if fault:
        with pytest.raises(ValueError):
            calls_from(events)
    else:
        events.append({"type": "item.completed", "item": call("schema")})
        assert len(calls_from(events)) == len(REQUIRED) + 1


def section(text):
    return {
        "text_excerpt": text,
        "excerpt_char_range": [0, len(text)],
        "text_length": len(text),
        "text_sha256": digest(text.encode()),
        "next_text_offset": None,
    }


@pytest.mark.parametrize(
    "fault",
    [
        "missing_receipt",
        "no_images",
        "partial_images",
        "incomplete_dfm",
        "hash",
        "range",
    ],
)
def test_layout_correction_requires_full_source_and_page_review(tmp_path, fault):
    data = clipped_document()
    revision = digest(data)
    asset_id = "test"
    root = tmp_path / "data/native-assets" / asset_id / "revisions"
    root.mkdir(parents=True)
    (root / revision).write_bytes(data)
    asset = {
        "asset_id": asset_id,
        "revision": revision,
        "history": [{"sha256": revision, "result": None}],
    }
    ref = {"asset_id": asset_id, "revision": revision, "locator": {}}
    with ZipFile(io.BytesIO(data)) as archive:
        table = etree.fromstring(archive.read("word/document.xml")).find(
            W + "body/" + W + "tbl"
        )
    record = {
        "evidence": ref,
        "native_xml": etree.tostring(table, encoding="unicode"),
        "rows": ROWS + 2,
        "columns": 2,
        "operation_result": None,
    }
    if fault == "missing_receipt":
        record.pop("operation_result")
    dfm = section("{}")
    if fault == "incomplete_dfm":
        dfm["next_text_offset"] = 2
    page = section(json.dumps(record))
    if fault == "hash":
        page["text_sha256"] = "invalid"
    elif fault == "range":
        page["excerpt_char_range"][1] += 1
    calls = [
        call(
            "read_docx",
            {"inspected_revision": revision, "blocks": [{"evidence": ref}], "dfm": dfm},
            asset_id=asset_id,
            revision=revision,
        ),
        call(
            "read_docx_table",
            {"inspected_revision": revision, "table": page},
            asset_id=asset_id,
            revision=revision,
            docx_table_reference=ref,
        ),
    ]
    if fault == "partial_images":
        calls.append(
            call(
                "render_docx_page",
                {"page_count": 2},
                asset_id=asset_id,
                revision=revision,
                docx_page_index=0,
            )
        )
    calls.append(
        call(
            "update_docx_table_grid",
            {"review_request": {"docx_table_reference": ref}},
            asset_id=asset_id,
            expected_revision=revision,
            docx_table_grid={"reference": ref},
        )
    )
    with pytest.raises(ValueError):
        validate_reads(calls, tmp_path, asset)
