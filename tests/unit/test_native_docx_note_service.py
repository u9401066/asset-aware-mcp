"""Revision-pinned note operations, complete receipts and immutable evidence."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.application.native_docx_bridge import NativeDocxBridge
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_docx_notes import NativeDocxNotes
from src.infrastructure.native_docx_stories import NativeDocxStories
from src.infrastructure.native_docx_workspace import FileNativeDocxWorkspaces
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_docx_helpers import call
from tests.native_docx_notes_helpers import locator, source_document
from tests.unit.test_native_docx_note_guards import creation


def complete(service, **fields):
    chunks, offset, digest = [], 0, None
    while True:
        page = call(service, **fields, text_offset=offset, text_limit=511)["note"]
        assert page["excerpt_char_range"][0] == offset
        assert digest is None or digest == page["text_sha256"]
        digest = page["text_sha256"]
        chunks.append(page["text_excerpt"])
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


@pytest.fixture
def stack(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(source_document())
    service = NativeDocumentService(
        FileNativeAssetRepository(tmp_path / "assets"),
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher(),
        NativeDocxBridge(FileNativeDocxWorkspaces()),
        docx_notes=NativeDocxNotes(),
        docx_stories=NativeDocxStories(),
    )
    asset = call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def read(service, asset, identity=2):
    return complete(
        service,
        op="read_docx_note",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        docx_note_locator=locator(identity=identity),
    )


def update(service, asset, reference, edits):
    return call(
        service,
        op="update_docx_note",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        docx_note_reference=reference,
        docx_note_update={
            "locator": locator(),
            "shared_scope": "all_native_references",
            "edits": edits,
        },
    )


def test_note_content_history_selection_and_noop_preserve_source(stack):
    service, asset, source = stack
    raw, mtime = source.read_bytes(), source.stat().st_mtime_ns
    before = read(service, asset)
    reference = before["evidence"]
    target = next(n for n in before["text_nodes"] if "FOOTNOTE" in n["text"])
    edits = [{"op": "set_text", "path": target["path"], "text": "CORRECTED 007 µg"}]
    changed = update(service, asset, reference, edits)
    after = complete(service, **changed["review_request"])
    assert changed["operation_result"]["committed"]
    assert after["operation_result"]["changes"][0]["after"] == edits[0]["text"]
    assert read(service, asset) == before
    assert call(service, op="verify", reference=reference)["valid"]
    selection = call(
        service,
        op="read_selection",
        reference=reference,
        selection={"pointer": "/text"},
    )["evidence"]
    assert call(service, op="verify", reference=selection)["valid"]
    same = update(service, changed["asset"], after["evidence"], edits)
    assert not same["operation_result"]["committed"]
    assert complete(service, **same["review_request"]) == after
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    assert source.read_bytes() == raw and source.stat().st_mtime_ns == mtime


def test_definition_create_delete_full_receipts_and_old_reference(stack):
    service, asset, source = stack
    listing = complete(
        service,
        op="read_docx_notes",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
    )
    old = read(service, asset, identity=8)
    changed = call(
        service,
        op="update_docx_notes",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        docx_notes_update={
            "scope": "definitions_and_native_body_references",
            "expected_catalog_sha256": listing["catalog_sha256"],
            "edits": [
                creation(source.read_bytes(), offset=5),
                {
                    "op": "delete",
                    "locator": locator(identity=8),
                    "expected_note_sha256": old["note_xml_sha256"],
                    "literal_body_text": "preserve",
                },
            ],
        },
    )
    final = complete(service, **changed["review_request"])
    assert len(final["operation_result"]["changes"]) == 2
    assert len(final["catalog"]["references"]) == 3
    assert call(service, op="verify", reference=old["evidence"])["valid"]
    assert read(service, asset, identity=8) == old
    with pytest.raises(ValueError, match="does not exist"):
        read(service, changed["asset"], identity=8)


@pytest.mark.parametrize(
    "failure", ["hash", "asset", "revision", "kind", "id", "part", "batch"]
)
def test_wrong_full_reference_or_batch_never_commits(stack, failure):
    service, asset, source = stack
    before = read(service, asset)
    ref = deepcopy(before["evidence"])
    edits = [
        {"op": "set_text", "path": before["text_nodes"][0]["path"], "text": "changed"}
    ]
    if failure == "hash":
        ref["value_sha256"] = "0" * 64
    elif failure == "asset":
        ref["asset_id"] = "file_" + "0" * 32
    elif failure == "revision":
        ref["revision"] = "0" * 64
    elif failure == "kind":
        ref["locator"]["note_kind"] = "endnote"
    elif failure == "id":
        ref["locator"]["note_id"] = 8
    elif failure == "part":
        ref["locator"]["part"] = "word/footnotes.xml"
    else:
        edits.append({"op": "delete_blocks", "index": 999, "count": 1})
    raw, mtime = source.read_bytes(), source.stat().st_mtime_ns
    with pytest.raises(ValueError):
        update(service, asset, ref, edits)
    assert read(service, asset) == before
    assert len(service.repository.load(asset["asset_id"]).history) == 1
    assert source.read_bytes() == raw and source.stat().st_mtime_ns == mtime


def test_receipt_budget_is_checked_before_any_commit(stack, monkeypatch):
    import src.application.native_docx_note_operations as module

    service, asset, _ = stack
    before = read(service, asset)
    original = module.record_text

    def reject(value):
        if value.get("operation_result") is not None:
            raise ValueError("complete receipt budget exceeded")
        return original(value)

    monkeypatch.setattr(module, "record_text", reject)
    with pytest.raises(ValueError, match="receipt budget"):
        update(
            service,
            asset,
            before["evidence"],
            [
                {
                    "op": "set_text",
                    "path": before["text_nodes"][0]["path"],
                    "text": "changed",
                }
            ],
        )
    assert len(service.repository.load(asset["asset_id"]).history) == 1


def test_note_wiki_exact_records_custom_citations_and_historical_snapshots(
    stack, tmp_path
):
    service, asset, _ = stack
    before = read(service, asset)
    request = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "output_dir": str(tmp_path / "wiki"),
        "citation_contract": {
            "name": "notes",
            "inline_template": "來源【{locator}】",
            "reference_template": "{title} | {locator}",
        },
    }
    first = call(service, **request)
    root = Path(first["output_dir"])
    old_files = {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    manifest = json.loads((root / "manifest.json").read_text())
    assert first["note_count"] == 7 and manifest["projection"] == "docx-notes-v1"
    records = [
        json.loads(line) for line in (root / "notes.jsonl").read_text().splitlines()
    ]
    record = next(r for r in records if r["locator"] == locator())
    assert record["evidence"] == before["evidence"]
    assert (
        "footnote native ID 2: word/annotations/source-footnotes.xml"
        in record["citation_presentation"]["inline"]
    )
    assert all(
        call(service, op="verify", reference=r["evidence"])["valid"] for r in records
    )
    update(
        service,
        asset,
        before["evidence"],
        [
            {
                "op": "set_text",
                "path": before["text_nodes"][0]["path"],
                "text": "REVISED",
            }
        ],
    )
    second = call(service, **request)
    assert second["output_dir"] != first["output_dir"]
    assert old_files == {
        p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    historical = call(service, **request, revision=asset["revision"])
    assert historical["output_dir"] == first["output_dir"]


def test_no_notes_keeps_identical_legacy_snapshot(tmp_path):
    import io

    from docx import Document

    raw = io.BytesIO()
    doc = Document()
    doc.add_paragraph("SAME BODY")
    doc.save(raw)
    source = tmp_path / "ordinary.docx"
    source.write_bytes(raw.getvalue())
    repository = FileNativeAssetRepository(tmp_path / "assets")
    bridge = NativeDocxBridge(FileNativeDocxWorkspaces())
    legacy = NativeDocumentService(
        repository, SpreadsheetFileAdapter(), FileNativeWikiPublisher(), bridge
    )
    current = NativeDocumentService(
        repository,
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher(),
        bridge,
        docx_notes=NativeDocxNotes(),
    )
    asset = call(legacy, op="register", source_path=str(source))["asset"]
    fields = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "output_dir": str(tmp_path / "wiki"),
    }
    old = call(legacy, **fields)
    new = call(current, **fields)
    assert old["output_dir"] == new["output_dir"]
    assert "note_count" not in new


def test_contract_advertises_notes_and_disabled_adapter_refuses_calls(stack):
    service, asset, _ = stack
    contract = call(service, op="contract", for_op="update_docx_notes")
    assert contract["docx_notes_enabled"]
    assert {
        "read_docx_note",
        "read_docx_notes",
        "update_docx_note",
        "update_docx_notes",
    } <= set(contract["formats"]["docx"])
    body = call(
        service, op="read_docx", asset_id=asset["asset_id"], revision=asset["revision"]
    )
    assert body["notes_request"]["op"] == "read_docx_notes"
    complete(service, **body["notes_request"])
    disabled = NativeDocumentService(service.repository, SpreadsheetFileAdapter())
    assert not call(disabled, op="contract")["docx_notes_enabled"]
    with pytest.raises(ValueError, match="not configured"):
        read(disabled, asset)
    with pytest.raises(ValueError, match="read-back bridge"):
        NativeDocumentService(
            service.repository, SpreadsheetFileAdapter(), docx_notes=NativeDocxNotes()
        )


def test_notes_are_typed_derivation_sources_and_csl_evidence(stack, tmp_path):
    from src.application.csl_citation_service import CslCitationService
    from src.application.native_derivation_service import NativeDerivationService
    from src.domain.csl_citations import CslDocument
    from src.infrastructure.csl_processor import NodeCslProcessor
    from src.infrastructure.native_derivation_store import (
        FileNativeDerivationRepository,
    )
    from tests.native_derivation_helpers import record
    from tests.unit.test_csl_processor import document

    service, asset, _ = stack
    service.derivations = NativeDerivationService(
        FileNativeDerivationRepository(tmp_path / "assets", service.repository),
        service.evidence,
    )
    source, target = (
        read(service, asset, identity=8)["evidence"],
        read(service, asset)["evidence"],
    )
    result = record(
        service,
        asset,
        {
            "target": target,
            "sources": [source],
            "agent": "test",
            "activity": "Link literal note evidence",
            "review": {"semantic_accuracy": "not_checked"},
        },
    )
    assert call(
        service,
        op="verify_derivation",
        asset_id=asset["asset_id"],
        derivation_id=result["derivation_id"],
    )["references_valid"]
    raw = document().model_dump()
    raw["sources"] = {"note": source}
    raw["clusters"][0]["cites"][0]["source_keys"] = ["note"]
    csl = CslCitationService(
        NodeCslProcessor(), service.evidence, FileNativeWikiPublisher()
    )
    preview, publication = csl.render(
        CslDocument.model_validate(raw), str(tmp_path / "citations")
    )
    assert preview["sources"]["note"]["reference"] == source
    assert publication["success"]


def test_note_only_adapter_has_distinct_snapshot_identity(stack, tmp_path):
    service, asset, _ = stack
    request = {
        "op": "export_wiki",
        "asset_id": asset["asset_id"],
        "output_dir": str(tmp_path / "wiki"),
    }
    full = call(service, **request)
    original = service.wiki.docx_stories
    service.wiki.docx_stories = None
    limited = call(service, **request)
    assert full["output_dir"] != limited["output_dir"]
    assert (
        json.loads((Path(limited["output_dir"]) / "manifest.json").read_text())[
            "projection"
        ]
        == "docx-notes-content-v1"
    )
    service.wiki.docx_stories = original
    assert call(service, **request)["output_dir"] == full["output_dir"]
