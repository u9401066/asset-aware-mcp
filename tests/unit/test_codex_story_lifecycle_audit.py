"""Reject partial lifecycle evidence and invented or incomplete actual page review."""

import json

import pytest

from src.application.native_docx_story_operations import attach_story_evidence
from src.infrastructure.native_docx_stories import NativeDocxStories
from tests.codex_native_pdf.trace import canonical, digest
from tests.codex_story_lifecycle.audit import (
    REQUIRED,
    calls_from,
    intent_bytes,
    validate_reads,
)
from tests.native_docx_story_lifecycle_helpers import (
    HEADER_PART,
    OBSOLETE,
    source_document,
    structure_edits,
)
from tests.unit.test_codex_docx_grid_audit import call
from tests.unit.test_codex_docx_layout_audit import section


def test_intent_comparison_accepts_equivalent_json_numbers_but_not_changed_values():
    assert intent_bytes({"font_size_pt": 9}) == intent_bytes({"font_size_pt": 9.0})
    assert intent_bytes({"font_size_pt": 9}) != intent_bytes({"font_size_pt": 9.5})
    assert intent_bytes({"section_index": 1}) != intent_bytes({"section_index": True})


@pytest.mark.parametrize(
    "fault", [None, "shell", "writeback", "missing", "unfinished", "foreign"]
)
def test_lifecycle_audit_restricts_actual_workflow(fault):
    events = [
        {"type": "turn.completed"},
        *[{"type": "item.completed", "item": call(op)} for op in sorted(REQUIRED)],
    ]
    if fault == "shell":
        events.append({"type": "item.completed", "item": {"type": "command_execution"}})
    if fault == "writeback":
        events.append({"type": "item.completed", "item": call("writeback")})
    if fault == "missing":
        events.pop()
    if fault == "unfinished":
        events.pop(0)
    if fault == "foreign":
        events[1]["item"]["server"] = "another"
    if fault:
        with pytest.raises(ValueError):
            calls_from(events)
    else:
        assert len(calls_from(events)) == len(REQUIRED)


@pytest.mark.parametrize(
    "fault,match",
    [
        ("receipt", "Full table receipt"),
        ("catalog", "section catalog"),
        ("text", "text paths"),
        ("hash", "hash/length"),
        ("range", "Read range"),
        ("images", "Initial pages"),
    ],
)
def test_lifecycle_audit_requires_complete_native_reads_before_edit(
    tmp_path, fault, match
):
    data = source_document()
    revision = digest(data)
    asset_id = "file_" + "1" * 32
    root = tmp_path / "data/native-assets" / asset_id / "revisions"
    root.mkdir(parents=True)
    (root / revision).write_bytes(data)
    asset = {
        "asset_id": asset_id,
        "revision": revision,
        "history": [{"sha256": revision, "result": None}],
    }
    adapter = NativeDocxStories()
    catalog = adapter.inspect(data)
    metadata = section(
        json.dumps(
            {
                "docx_story_structure_enabled": True,
                "docx_story_structure_policy": "explicit inherited scope",
            }
        )
    )
    calls = [
        call("contract_details", metadata, contract_sha256=metadata["text_sha256"])
    ]
    structure = {
        "catalog": catalog,
        "catalog_sha256": digest(canonical(catalog)),
        "operation_result": None,
    }
    if fault == "catalog":
        structure["catalog"]["sections"][1]["bindings"][0]["declared"] = True
    calls.append(
        call(
            "read_docx_story_structure",
            {
                "inspected_revision": revision,
                "story_structure": section(json.dumps(structure)),
            },
            asset_id=asset_id,
            revision=revision,
        )
    )
    records = {}
    for item in adapter.inspect(data)["stories"]:
        part = item["locator"]["part"]
        record = adapter.read(data, part)
        attach_story_evidence(record, asset_id, revision)
        record["operation_result"] = None
        records[part] = record
        if part == HEADER_PART:
            if fault == "receipt":
                del record["operation_result"]
            if fault == "text":
                record["text_nodes"] = []
        page = section(json.dumps(record))
        if part == HEADER_PART and fault == "hash":
            page["text_sha256"] = "0" * 64
        if part == HEADER_PART and fault == "range":
            page["excerpt_char_range"][1] += 1
        calls.append(
            call(
                "read_docx_story",
                {"inspected_revision": revision, "story": page},
                asset_id=asset_id,
                revision=revision,
                docx_story_part=part,
            )
        )
    calls.append(
        call(
            "update_docx_story_structure",
            {"asset": {"revision": "new"}},
            asset_id=asset_id,
            expected_revision=revision,
            docx_story_structure={
                "scope": "sections_and_following_inheritors",
                "expected_catalog_sha256": structure["catalog_sha256"],
                "edits": structure_edits(
                    records[HEADER_PART], records[OBSOLETE], "word/footer1.xml"
                ),
            },
        )
    )
    with pytest.raises(ValueError, match=match):
        validate_reads(calls, tmp_path, asset)
