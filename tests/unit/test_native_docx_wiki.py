"""Revision-pinned DOCX blocks and exact OOXML parts become portable wiki assets."""

from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

import pytest

from src.application.native_document_service import NativeDocumentService
from src.infrastructure.native_wiki_publisher import FileNativeWikiPublisher
from tests.native_docx_helpers import call, read_dfm
from tests.native_docx_helpers import native_docx as native_docx


def export(service, asset, root, **kwargs):
    return call(
        service,
        op="export_wiki",
        asset_id=asset["asset_id"],
        output_dir=str(root),
        **kwargs,
    )


def records(root):
    return [
        json.loads(line)
        for line in (root / "records.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_every_docx_package_part_and_reference_survives_wiki_export(
    native_docx, tmp_path
):
    service, asset, source = native_docx
    before, mtime = source.read_bytes(), source.stat().st_mtime_ns
    result = export(service, asset, tmp_path / "wiki")
    root = Path(result["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert result["success"] and result["cell_count"] == 0 and result["block_count"] > 0
    assert manifest["projection"] == "docx-blocks-v1"
    assert manifest["representation"] == "docx_blocks"
    assert (root / manifest["source_attachment"]).read_bytes() == before
    with zipfile.ZipFile(io.BytesIO(before)) as package:
        assert set(manifest["part_attachments"]) == set(package.namelist())
        for name, attachment in manifest["part_attachments"].items():
            value = (root / attachment["attachment"]).read_bytes()
            assert value == package.read(name)
            assert hashlib.sha256(value).hexdigest() == attachment["sha256"]
    assert set(manifest["files"]) | {"manifest.json"} == {
        p.name for p in root.iterdir()
    }
    for name, info in manifest["files"].items():
        value = (root / name).read_bytes()
        assert info == {
            "sha256": hashlib.sha256(value).hexdigest(),
            "size_bytes": len(value),
        }
    for record in records(root):
        assert call(service, op="verify", reference=record["evidence"])["valid"]
        assert (
            record["source_part_attachment"]
            == manifest["part_attachments"][record["locator"]["part"]]["attachment"]
        )
    for note in root.glob("*.md"):
        text = note.read_text(encoding="utf-8")
        assert len(re.findall(r"^# ", text, flags=re.M)) == 1
        for target in re.findall(r"(?<!\\)\[\[([^]|]+)", text):
            assert (root / (target + ".md")).exists()
        for target in re.findall(r"(?<!\\)\]\(([^)]+)\)", text):
            assert (root / target).exists()
    assert result["review_required"] == [
        "semantic_accuracy",
        "rendered_layout",
        "fields_and_revisions",
    ]
    assert source.read_bytes() == before and source.stat().st_mtime_ns == mtime
    assert export(service, asset, tmp_path / "wiki")["reused"] is True


def test_component_projection_preserves_legacy_opaque_docx_and_curated_edits(
    native_docx, tmp_path
):
    service, asset, _ = native_docx
    legacy = NativeDocumentService(
        service.repository, service.spreadsheets, FileNativeWikiPublisher()
    )
    old = export(legacy, asset, tmp_path / "wiki")
    old_root = Path(old["output_dir"])
    (old_root / old["index_note"]).write_text("Human annotation", encoding="utf-8")
    before = {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in old_root.iterdir()
    }
    current = export(service, asset, tmp_path / "wiki")
    assert current["output_dir"] != old["output_dir"]
    assert before == {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in old_root.iterdir()
    }
    current_root = Path(current["output_dir"])
    note = current_root / current["index_note"]
    note.write_text("Curated new note", encoding="utf-8")
    with pytest.raises(ValueError, match="modified"):
        export(service, asset, tmp_path / "wiki")
    assert note.read_text(encoding="utf-8") == "Curated new note"


def test_citation_display_changes_neither_evidence_nor_note_identity(
    native_docx, tmp_path
):
    service, asset, _ = native_docx
    plain = export(service, asset, tmp_path / "wiki")
    styled = export(
        service,
        asset,
        tmp_path / "styled",
        citation_contract={
            "inline_template": "{authors} / {year} / {locator}",
            "reference_template": "{title}",
        },
        citation_metadata={"authors": "Lin", "year": "2026"},
    )
    old, new = records(Path(plain["output_dir"])), records(Path(styled["output_dir"]))
    assert [(r["note"], r["evidence"]) for r in old] == [
        (r["note"], r["evidence"]) for r in new
    ]
    for record in new:
        locator = record["locator"]
        assert (
            record["citation_presentation"]["inline"]
            == f"Lin / 2026 / {locator['part']}#{locator['block_id']}"
        )


def test_new_revision_preserves_old_docx_notes_and_references(native_docx, tmp_path):
    service, asset, _ = native_docx
    old = export(service, asset, tmp_path / "wiki")
    root = Path(old["output_dir"])
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    current = call(
        service,
        op="update_docx",
        asset_id=asset["asset_id"],
        expected_revision=asset["revision"],
        docx_edit={"dfm_text": read_dfm(service, asset).replace("原始段落", "新段落")},
    )["asset"]
    new = export(service, current, tmp_path / "wiki")
    assert new["output_dir"] != old["output_dir"]
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    assert export(service, asset, tmp_path / "wiki", revision=asset["revision"])[
        "reused"
    ]
    for record in records(root):
        assert call(service, op="verify", reference=record["evidence"])["valid"]


@pytest.mark.parametrize(
    "limit, error",
    [
        ("src.application.native_docx_wiki.MAX_WIKI_PARTS", "package-part limit"),
        ("src.application.native_docx_wiki.MAX_WIKI_CELLS", "block-record limit"),
        ("src.application.native_wiki_format.MAX_WIKI_BYTES", "byte limit"),
        ("src.application.native_docx_bridge.MAX_DOCX_BLOCKS", "20000-block limit"),
    ],
)
def test_docx_export_limits_leave_no_partial_snapshot(
    native_docx, tmp_path, monkeypatch, limit, error
):
    service, asset, _ = native_docx
    monkeypatch.setattr(limit, 1)
    with pytest.raises(ValueError, match=error):
        export(service, asset, tmp_path / "wiki")
    assert not (tmp_path / "wiki").exists()


def test_unparsed_parts_are_retained_and_source_text_cannot_inject_wiki_links(
    native_docx, tmp_path
):
    from docx import Document

    from tests.native_docx_helpers import replace_parts

    service, _, source = native_docx
    document = Document(io.BytesIO(source.read_bytes()))
    document.paragraphs[1].text = "# Fake title\n[[missing-note]] <script>bad</script>"
    document.save(source)
    opaque = b"unparsed custom binary object\x00\xff"
    source.write_bytes(
        replace_parts(source.read_bytes(), {"customXml/unparsed.dat": opaque})
    )
    asset = call(service, op="register", source_path=str(source))["asset"]
    result = export(service, asset, tmp_path / "wiki")
    root = Path(result["output_dir"])
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    attachment = manifest["part_attachments"]["customXml/unparsed.dat"]["attachment"]
    assert attachment.endswith(".bin") and (root / attachment).read_bytes() == opaque
    record = next(
        r for r in records(root) if "Fake title" in r["representation"]["text"]
    )
    note = (root / record["note"]).read_text(encoding="utf-8")
    assert len(re.findall(r"^# ", note, flags=re.M)) == 1
    assert "[[missing-note]]" not in note and "<script>" not in note
    assert call(service, op="verify", reference=record["evidence"])["valid"]
