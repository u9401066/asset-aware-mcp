"""Whole-story references, complete paging, immutable Wiki and atomic updates."""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.application.native_docx_bridge import NativeDocxBridge
from src.infrastructure.native_asset_store import FileNativeAssetRepository
from src.infrastructure.native_docx_stories import NativeDocxStories
from src.infrastructure.native_docx_workspace import FileNativeDocxWorkspaces
from src.infrastructure.native_spreadsheet import SpreadsheetFileAdapter
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_docx_helpers import call
from tests.native_docx_stories_helpers import HEADER_PART, HEADER_TEXT, story_document


def complete(service, **fields):
    chunks, offset, digest = [], 0, None
    while True:
        item = call(service, **fields, text_offset=offset, text_limit=777)["story"]
        assert item["excerpt_char_range"][0] == offset
        assert digest is None or digest == item["text_sha256"]
        digest = item["text_sha256"]
        chunks.append(item["text_excerpt"])
        offset = item["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


@pytest.fixture
def stack(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(story_document())
    service = NativeDocumentService(
        FileNativeAssetRepository(tmp_path / "assets"),
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher(),
        NativeDocxBridge(FileNativeDocxWorkspaces()),
        docx_stories=NativeDocxStories(),
    )
    asset = call(service, op="register", source_path=str(source))["asset"]
    return service, asset, source


def read(service, asset, part=HEADER_PART):
    return complete(
        service,
        op="read_docx_story",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        docx_story_part=part,
    )


def update(service, asset, reference, edits):
    return call(
        service,
        op="update_docx_story",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        docx_story_reference=reference,
        docx_story_update={
            "part": HEADER_PART,
            "shared_scope": "all_sections_using_part",
            "edits": edits,
        },
    )


def test_shared_story_crud_full_receipts_selection_history_and_wiki(stack, tmp_path):
    service, asset, source = stack
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    contract = call(service, op="contract", for_op="update_docx_story")
    assert contract["docx_stories_enabled"]
    assert "read_docx_stories" in contract["formats"]["docx"]
    legacy = call(
        service,
        op="read_docx",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        limit=100,
    )
    old_ref = next(b["evidence"] for b in legacy["blocks"] if b["type"] == "footer")
    catalog = complete(service, **legacy["header_footer_request"])
    assert len(catalog["stories"]) == 3
    before = read(service, asset)
    ref = before["evidence"]
    wiki = call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )
    old_dir = Path(wiki["output_dir"])
    old_files = {
        p.relative_to(old_dir): p.read_bytes()
        for p in old_dir.rglob("*")
        if p.is_file()
    }
    assert wiki["story_count"] == 3
    manifest = json.loads((old_dir / "manifest.json").read_text())
    assert manifest["projection"] == "docx-stories-v1"
    records = [
        json.loads(line)
        for line in (old_dir / "stories.jsonl").read_text().splitlines()
    ]
    assert (
        next(r for r in records if r["locator"]["part"] == HEADER_PART)["evidence"]
        == ref
    )
    node = next(n for n in before["text_nodes"] if n["text"] == HEADER_TEXT)
    edits = [
        {"op": "set_text", "path": node["path"], "text": "CORRECTED 007 µg END-HEADER"}
    ]
    changed = update(service, asset, ref, edits)
    current = changed["asset"]
    assert changed["operation_result"]["committed"]
    after = complete(service, **changed["review_request"])
    assert after["operation_result"]["changes"][0]["before"] == HEADER_TEXT
    assert after["operation_result"]["changes"][0]["after"] == edits[0]["text"]
    assert read(service, asset) == before
    assert call(service, op="verify", reference=ref)["valid"]
    assert call(service, op="verify", reference=old_ref)["valid"]
    selection = call(
        service, op="read_selection", reference=ref, selection={"pointer": "/text"}
    )["evidence"]
    assert call(service, op="verify", reference=selection)["valid"]
    same = update(service, current, after["evidence"], edits)
    assert not same["operation_result"]["committed"]
    assert len(service.repository.load(asset["asset_id"]).history) == 2
    assert complete(service, **same["review_request"]) == after
    later = call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(tmp_path / "wiki"),
        citation_contract={"preset": "source"},
    )
    assert later["output_dir"] != str(old_dir)
    assert {
        p.relative_to(old_dir): p.read_bytes()
        for p in old_dir.rglob("*")
        if p.is_file()
    } == old_files
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime


@pytest.mark.parametrize(
    "failure", ["hash", "asset", "revision", "part", "batch", "scope"]
)
def test_stale_or_tampered_plan_leaves_history_and_source_intact(stack, failure):
    service, asset, source = stack
    before = read(service, asset)
    ref = deepcopy(before["evidence"])
    node = before["text_nodes"][0]
    edits = [{"op": "set_text", "path": node["path"], "text": "changed"}]
    if failure == "hash":
        ref["value_sha256"] = "0" * 64
    elif failure == "asset":
        ref["asset_id"] = "file_" + "0" * 32
    elif failure == "revision":
        ref["revision"] = "0" * 64
    elif failure == "part":
        ref["locator"]["part"] = "word/footer1.xml"
    elif failure == "batch":
        edits.append({"op": "delete_blocks", "index": 20000, "count": 1})
    else:
        edits.append({"op": "set_text", "path": [], "text": "invalid"})
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    with pytest.raises(ValueError):
        update(service, asset, ref, edits)
    assert len(service.repository.load(asset["asset_id"]).history) == 1
    assert read(service, asset) == before
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime


def test_no_stories_retains_legacy_wiki_projection(tmp_path):
    import io

    from docx import Document

    buf = io.BytesIO()
    Document().save(buf)
    source = tmp_path / "body.docx"
    source.write_bytes(buf.getvalue())
    service = NativeDocumentService(
        FileNativeAssetRepository(tmp_path / "assets"),
        SpreadsheetFileAdapter(),
        FileNativeWikiPublisher(),
        NativeDocxBridge(FileNativeDocxWorkspaces()),
        docx_stories=NativeDocxStories(),
    )
    asset = call(service, op="register", source_path=str(source))["asset"]
    result = call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(tmp_path / "wiki"),
    )
    assert "story_count" not in result
    assert (
        json.loads((Path(result["output_dir"]) / "manifest.json").read_text())[
            "projection"
        ]
        == "docx-blocks-v1"
    )


def test_review_budget_failure_happens_before_commit(stack, monkeypatch):
    import src.application.native_docx_story_operations as module

    service, asset, _ = stack
    record = read(service, asset)
    original = module.record_text

    def reject(value):
        if value.get("operation_result") is not None:
            raise ValueError("simulated complete review budget")
        return original(value)

    monkeypatch.setattr(module, "record_text", reject)
    with pytest.raises(ValueError, match="review budget"):
        update(
            service,
            asset,
            record["evidence"],
            [
                {
                    "op": "set_text",
                    "path": record["text_nodes"][0]["path"],
                    "text": "changed",
                }
            ],
        )
    assert len(service.repository.load(asset["asset_id"]).history) == 1


def test_story_citation_locator_and_native_derivation_union(stack):
    from pydantic import TypeAdapter

    from src.application.citation_format_service import render_citation
    from src.domain.citation_format import CitationMetadata, resolve_citation_format
    from src.domain.native_derivation import NativeReference

    service, asset, _ = stack
    record = read(service, asset)
    reference = TypeAdapter(NativeReference).validate_python(record["evidence"])
    assert call(service, op="verify", reference=reference.model_dump())["valid"]
    display = render_citation(
        resolve_citation_format({"preset": "source"}),
        CitationMetadata(),
        source_id=asset["asset_id"],
        asset_id=asset["asset_id"],
        title="Study",
        locator=reference.locator.model_dump(),
    )
    assert "header: " + HEADER_PART in display["inline"]
