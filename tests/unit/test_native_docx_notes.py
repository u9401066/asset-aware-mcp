"""Notes are separate native identities, never inferred display numbers."""

import pytest
from lxml import etree

from src.domain.native_docx_notes import (
    DocxNoteLocator,
    DocxNotesUpdate,
    DocxNoteUpdate,
)
from src.infrastructure.native_docx_notes import NativeDocxNotes
from tests.native_docx_notes_helpers import (
    END,
    FOOT,
    W,
    canonical_record,
    digest,
    locator,
    package,
    parts,
    source_document,
    xml,
)


def read(data, kind="footnote", identity=2):
    return NativeDocxNotes().read(data, DocxNoteLocator(**locator(kind, identity)))


def test_complete_notes_include_roles_body_paths_and_native_parts():
    data = source_document()
    catalog = NativeDocxNotes().inspect(data)
    assert {p["part"] for p in catalog["parts"]} == {FOOT, END}
    normal = [n for n in catalog["notes"] if n["note_type"] == "normal"]
    assert {n["locator"]["note_id"] for n in normal} == {2, 8, 5}
    assert len(catalog["references"]) == 3
    assert catalog["body"]["raw_part_sha256"] == digest(
        parts(data)["word/document.xml"]
    )
    note = read(data)
    assert "007 µg -0.50 mg/L" in note["text"]
    assert len(note["references"]) == 1
    assert note["locator"] == locator()
    assert "<w:b" in note["xml"] and "footnoteRef" in note["xml"]
    assert note["note_xml_sha256"] == digest(note["xml"].encode())


def test_content_edit_preserves_other_notes_xml_marker_and_package_bytes():
    data = source_document()
    before = read(data)
    target = next(n for n in before["text_nodes"] if "FOOTNOTE" in n["text"])
    request = DocxNoteUpdate.model_validate(
        {
            "locator": locator(),
            "shared_scope": "all_native_references",
            "edits": [
                {
                    "op": "set_text",
                    "path": target["path"],
                    "text": " VERIFIED 007 µg -0.50 mg/L",
                }
            ],
        }
    )
    updated, result = NativeDocxNotes().edit(data, request)
    assert result.changed_parts == [FOOT]
    assert read(updated)["references"] == before["references"]
    stable_old, stable_new = read(data, identity=8), read(updated, identity=8)
    stable_old.pop("raw_part_sha256")
    stable_new.pop("raw_part_sha256")
    assert stable_new == stable_old
    assert read(updated, "endnote", 5) == read(data, "endnote", 5)
    assert {k: v for k, v in parts(data).items() if k != FOOT} == {
        k: v for k, v in parts(updated).items() if k != FOOT
    }
    assert "VERIFIED" in read(updated)["text"] and "<w:b" in read(updated)["xml"]
    with pytest.raises(ValueError, match="reference mark"):
        NativeDocxNotes().edit(
            data,
            DocxNoteUpdate.model_validate(
                {
                    "locator": locator(),
                    "shared_scope": "all_native_references",
                    "edits": [{"op": "delete_blocks", "index": 0, "count": 1}],
                }
            ),
        )


def test_create_mid_run_and_delete_preserve_literal_body_text_and_historical_source():
    data = source_document()
    adapter = NativeDocxNotes()
    catalog = adapter.inspect(data)
    target = next(
        n for n in catalog["body"]["text_nodes"] if n["text"].startswith("Source")
    )
    request = DocxNotesUpdate.model_validate(
        {
            "expected_catalog_sha256": digest(canonical_record(catalog)),
            "scope": "definitions_and_native_body_references",
            "edits": [
                {
                    "op": "create",
                    "note_kind": "footnote",
                    "part": FOOT,
                    "anchor": {
                        "text_path": target["path"],
                        "character_offset": 10,
                        "expected_text_sha256": digest(target["text"].encode()),
                    },
                    "blocks": [
                        {
                            "kind": "paragraph",
                            "runs": [{"text": "NEW NOTE 007 µg", "italic": True}],
                        }
                    ],
                }
            ],
        }
    )
    updated, receipt = adapter.change_structure(data, request)
    created = receipt.changes[0]["created_note"]
    assert created["note_id"] not in {0, 2, 8}
    assert read(updated, identity=created["note_id"])["text"].endswith(
        "NEW NOTE 007 µg"
    )
    old_main = etree.fromstring(parts(data)["word/document.xml"])
    new_main = etree.fromstring(parts(updated)["word/document.xml"])
    assert "".join(old_main.itertext()) == "".join(new_main.itertext())
    old_run = old_main.find(".//" + W + "r")
    new_para = new_main.find(".//" + W + "p")
    assert new_para[0].find(W + "rPr").find(W + "b") is not None
    assert new_para[2].find(W + "rPr").find(W + "b") is not None
    assert (
        new_para[0].find(W + "t").text + new_para[2].find(W + "t").text
    ) == old_run.find(W + "t").text
    current = adapter.inspect(updated)
    record = read(updated, identity=created["note_id"])
    final, _ = adapter.change_structure(
        updated,
        DocxNotesUpdate.model_validate(
            {
                "expected_catalog_sha256": digest(canonical_record(current)),
                "scope": "definitions_and_native_body_references",
                "edits": [
                    {
                        "op": "delete",
                        "locator": created,
                        "expected_note_sha256": record["note_xml_sha256"],
                        "literal_body_text": "preserve",
                    }
                ],
            }
        ),
    )
    assert len(adapter.inspect(final)["references"]) == 3
    assert read(data)["text"] == read(final)["text"]
    assert "NEW NOTE" not in parts(data)[FOOT].decode()


def test_note_role_uses_type_not_reserved_id_conventions():
    values = parts(source_document())
    root = etree.fromstring(values[FOOT])
    root[1].set(W + "id", "7")
    root[2].set(W + "id", "0")
    main = etree.fromstring(values["word/document.xml"])
    next(main.iter(W + "footnoteReference")).set(W + "id", "0")
    values[FOOT], values["word/document.xml"] = xml(root), xml(main)
    catalog = NativeDocxNotes().inspect(package(values))
    entries = {
        n["locator"]["note_id"]: n
        for n in catalog["notes"]
        if n["locator"]["part"] == FOOT
    }
    assert entries[0]["note_type"] == "normal"
    assert entries[7]["note_type"] == "continuationSeparator"
