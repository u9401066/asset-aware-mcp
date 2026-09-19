"""Reject partial/forged native story evidence and unreviewed actual pages."""

import json

import pytest

from src.application.native_docx_story_operations import attach_story_evidence
from src.infrastructure.native_docx_stories import NativeDocxStories
from tests.codex_docx_stories.audit import PARTS, REQUIRED, calls_from, validate_reads
from tests.codex_native_pdf.trace import digest
from tests.native_docx_stories_helpers import HEADER_PART, story_document
from tests.unit.test_codex_docx_grid_audit import call
from tests.unit.test_codex_docx_layout_audit import section


@pytest.mark.parametrize(
    "fault", [None, "shell", "writeback", "missing", "unfinished", "foreign"]
)
def test_story_audit_restricts_actual_workflow(fault):
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
        events[1]["item"]["server"] = "another"
    if fault:
        with pytest.raises(ValueError):
            calls_from(events)
    else:
        assert len(calls_from(events)) == len(REQUIRED)


@pytest.mark.parametrize(
    "fault,match",
    [
        ("missing_receipt", "Full table receipt"),
        ("no_images", "Initial pages"),
        ("partial_images", "Initial pages"),
        ("hash", "hash/length"),
        ("range", "Read range"),
        ("xml", "native story XML"),
        ("text", "native text paths"),
    ],
)
def test_story_edits_require_independent_complete_records_and_images(
    tmp_path, fault, match
):
    data = story_document()
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
    calls = [
        call(
            "read_docx_stories",
            {
                "inspected_revision": revision,
                "story": section(json.dumps(adapter.inspect(data))),
            },
            asset_id=asset_id,
            revision=revision,
        )
    ]
    reference = None
    for part in sorted(PARTS):
        record = adapter.read(data, part)
        attach_story_evidence(record, asset_id, revision)
        record["operation_result"] = None
        if part == HEADER_PART:
            reference = record["evidence"]
            if fault == "missing_receipt":
                del record["operation_result"]
            elif fault == "xml":
                record["xml"] = record["xml"].replace("SOURCE", "FORGED")
            elif fault == "text":
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
    if fault == "partial_images":
        image = call(
            "render_docx_page",
            {"inspected_revision": revision, "page_count": 3},
            asset_id=asset_id,
            revision=revision,
            docx_page_index=0,
        )
        image["result"]["content"].append({"type": "image"})
        calls.append(image)
    calls.append(
        call(
            "update_docx_story",
            {},
            asset_id=asset_id,
            expected_revision=revision,
            docx_story_reference=reference,
            docx_story_update={
                "part": HEADER_PART,
                "shared_scope": "all_sections_using_part",
            },
        )
    )
    with pytest.raises(ValueError, match=match):
        validate_reads(calls, tmp_path, asset)
