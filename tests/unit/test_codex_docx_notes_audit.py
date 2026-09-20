"""The note audit rejects forged XML, missing references and forbidden actions."""

from copy import deepcopy

import pytest

from src.application.native_docx_note_operations import attach_note_evidence
from src.domain.native_docx_notes import DocxNoteLocator
from src.infrastructure.native_docx_notes import NativeDocxNotes
from tests.codex_docx_notes.audit import REQUIRED, calls_from
from tests.codex_docx_notes.records import check_catalog, check_note
from tests.native_docx_notes_helpers import digest, locator, source_document
from tests.unit.test_codex_docx_grid_audit import call


@pytest.mark.parametrize(
    "fault", [None, "shell", "writeback", "missing", "unfinished", "foreign"]
)
def test_note_audit_restricts_actual_workflow(fault):
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
    "fault", [None, "xml", "text", "paths", "references", "hash", "role", "revision"]
)
def test_record_audit_uses_independent_native_bytes(fault):
    data = source_document()
    asset_id, revision = "file_" + "1" * 32, digest(data)
    record = NativeDocxNotes().read(data, DocxNoteLocator(**locator()))
    attach_note_evidence(record, asset_id, revision)
    if fault == "xml":
        record["xml"] = record["xml"].replace("FOOTNOTE", "FORGED")
    elif fault == "text":
        record["text"] += "FORGED"
    elif fault == "paths":
        record["text_nodes"][0]["path"] = [999]
    elif fault == "references":
        record["references"] = []
    elif fault == "hash":
        record["note_xml_sha256"] = "0" * 64
    elif fault == "role":
        record["note_type"] = "separator"
    elif fault == "revision":
        record["evidence"]["revision"] = "0" * 64
    if fault:
        with pytest.raises(ValueError):
            check_note(record, data, asset_id, revision)
    else:
        check_note(record, data, asset_id, revision)


@pytest.mark.parametrize("key", ["parts", "notes", "references", "body"])
def test_catalog_audit_rejects_omitted_or_forged_native_inventory(key):
    data = source_document()
    catalog = NativeDocxNotes().inspect(data)
    check_catalog(catalog, data)
    altered = deepcopy(catalog)
    if key == "body":
        altered[key]["text_nodes"][0]["text_sha256"] = "0" * 64
    else:
        altered[key].pop()
    with pytest.raises(ValueError):
        check_catalog(altered, data)
