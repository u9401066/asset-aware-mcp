"""Lifecycle source CAS, complete receipts, immutable story evidence and Wikis."""

import hashlib
import json
from pathlib import Path

import pytest

from src.application.native_docx_table_operations import record_text
from tests.native_docx_helpers import call
from tests.unit import test_native_docx_story_service as story_tests
from tests.unit.test_native_docx_story_lifecycle import NEW, binding, clone
from tests.unit.test_native_docx_story_service import read


@pytest.fixture(name="stack")
def make_stack(tmp_path):
    return story_tests.stack.__wrapped__(tmp_path)


def complete(service, asset):
    chunks, offset, digest = [], 0, None
    while True:
        page = call(
            service,
            op="read_docx_story_structure",
            asset_id=asset["asset_id"],
            revision=asset["revision"],
            text_offset=offset,
            text_limit=1000,
        )["story_structure"]
        assert digest is None or digest == page["text_sha256"]
        digest = page["text_sha256"]
        chunks.append(page["text_excerpt"])
        assert page["excerpt_char_range"][0] == offset
        offset = page["next_text_offset"]
        if offset is None:
            break
    text = "".join(chunks)
    assert hashlib.sha256(text.encode()).hexdigest() == digest
    return json.loads(text)


def update(service, asset, edits, digest=None):
    record = complete(service, asset)
    return call(
        service,
        op="update_docx_story_structure",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        docx_story_structure={
            "expected_catalog_sha256": digest or record["catalog_sha256"],
            "scope": "sections_and_following_inheritors",
            "edits": edits,
        },
    )


def test_full_lifecycle_receipts_history_source_and_old_wikis(stack, tmp_path):
    service, asset, source = stack
    original, mtime = source.read_bytes(), source.stat().st_mtime_ns
    historical = read(service, asset)["evidence"]
    old = call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        revision=asset["revision"],
        output_dir=str(tmp_path / "wiki"),
    )
    old_root = Path(old["output_dir"])
    old_files = {
        p.relative_to(old_root): p.read_bytes()
        for p in old_root.rglob("*")
        if p.is_file()
    }
    before = complete(service, asset)
    assert (
        before["catalog_sha256"]
        == hashlib.sha256(record_text(before["catalog"]).encode()).hexdigest()
    )
    with pytest.raises(ValueError, match="catalog hash"):
        update(service, asset, [clone(original), binding(1, NEW)], "f" * 64)
    result = update(service, asset, [clone(original), binding(1, NEW)])
    current = result["asset"]
    record = complete(service, current)
    assert len(record["operation_result"]["changes"]) == 2
    assert (
        record["operation_result"]["changes"][1]["after_catalog"] == record["catalog"]
    )
    ref = read(service, current, NEW)["evidence"]
    assert call(service, op="verify", reference=historical)["valid"]
    assert call(service, op="verify", reference=ref)["valid"]
    with pytest.raises(ValueError, match="stale"):
        update(service, asset, [binding(1, None)])
    same = update(service, current, [binding(1, NEW)])
    assert not same["operation_result"]["committed"]
    assert complete(service, same["asset"]) == record
    new_wiki = call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        revision=current["revision"],
        output_dir=str(tmp_path / "wiki"),
    )
    assert new_wiki["story_count"] == 4
    new_story = read(service, current, NEW)
    final = update(
        service,
        current,
        [
            binding(1, None),
            {
                "op": "delete",
                "part": NEW,
                "expected_part_sha256": new_story["raw_part_sha256"],
            },
        ],
    )["asset"]
    assert complete(service, final)["catalog"] == before["catalog"]
    assert call(service, op="verify", reference=ref)["valid"]
    assert len(service.repository.load(asset["asset_id"]).history) == 3
    assert source.read_bytes() == original and source.stat().st_mtime_ns == mtime
    assert old_files == {
        p.relative_to(old_root): p.read_bytes()
        for p in old_root.rglob("*")
        if p.is_file()
    }


def test_receipt_size_failure_rejects_before_commit(stack, monkeypatch):
    from src.application import native_docx_story_structure_operations as module

    service, asset, source = stack
    original = module.record_text

    def oversized(record):
        if record.get("operation_result"):
            raise ValueError("injected complete receipt budget failure")
        return original(record)

    monkeypatch.setattr(module, "record_text", oversized)
    with pytest.raises(ValueError, match="budget"):
        update(service, asset, [clone(source.read_bytes()), binding(1, NEW)])
    assert service.repository.load(asset["asset_id"]).revision == asset["revision"]
    assert len(service.repository.load(asset["asset_id"]).history) == 1
