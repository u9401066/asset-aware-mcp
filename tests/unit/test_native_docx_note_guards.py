"""Preserve run children and isolate the actual relationship owner of each note."""

import io
from copy import deepcopy

import pytest
from docx import Document
from lxml import etree

from src.domain.native_docx_notes import DocxNotesUpdate
from src.infrastructure.native_docx_notes import NativeDocxNotes
from tests.native_docx_notes_helpers import (
    FOOT,
    REL,
    TYPE,
    R,
    W,
    canonical_record,
    digest,
    locator,
    package,
    parts,
    source_document,
    xml,
)
from tests.unit.test_native_docx_notes import read


def change(data, edits):
    adapter = NativeDocxNotes()
    return adapter.change_structure(
        data,
        DocxNotesUpdate.model_validate(
            {
                "expected_catalog_sha256": digest(
                    canonical_record(adapter.inspect(data))
                ),
                "scope": "definitions_and_native_body_references",
                "edits": edits,
            }
        ),
    )


def creation(data, *, text=None, kind="footnote", part=FOOT, offset=0):
    nodes = NativeDocxNotes().inspect(data)["body"]["text_nodes"]
    target = next(n for n in nodes if text is None or n["text"] == text)
    return {
        "op": "create",
        "note_kind": kind,
        "part": part,
        "anchor": {
            "text_path": target["path"],
            "character_offset": offset,
            "expected_text_sha256": digest(target["text"].encode()),
        },
        "blocks": [{"kind": "paragraph", "runs": [{"text": "NEW NOTE 007 µg"}]}],
    }


def deletion(data, identity=2):
    return {
        "op": "delete",
        "locator": locator(identity=identity),
        "expected_note_sha256": read(data, identity=identity)["note_xml_sha256"],
        "literal_body_text": "preserve",
    }


@pytest.mark.parametrize("offset", [0, 1, 3, 4, 5, 7])
def test_split_preserves_unicode_rich_run_children_and_exact_formatting(offset):
    values = parts(source_document())
    main = etree.fromstring(values["word/document.xml"])
    run = main.find(".//" + W + "r")
    run.find(W + "t").text = "BEFORE"
    etree.SubElement(run, W + "tab")
    text = " A😀e\u0301中 "
    node = etree.SubElement(run, W + "t")
    node.text, node.tail = text, "\n "
    etree.SubElement(run, W + "br")
    etree.SubElement(run, W + "t").text = "AFTER"
    values["word/document.xml"] = xml(main)
    data = package(values)
    result, _ = change(data, [creation(data, text=text, offset=offset)])
    paragraph = etree.fromstring(parts(result)["word/document.xml"]).find(
        ".//" + W + "p"
    )
    left, mark, right = paragraph[:3]
    assert [c.tag for c in left] == [W + x for x in ("rPr", "t", "tab", "t")]
    assert [c.tag for c in right] == [W + x for x in ("rPr", "t", "br", "t")]
    assert (left[-1].text or "") == text[:offset]
    assert (right[1].text or "") == text[offset:]
    assert right[-1].text == "AFTER" and left[1].text == "BEFORE"
    assert left[-1].tail is None and right[1].tail == "\n "
    assert etree.tostring(left[0]) == etree.tostring(right[0])
    assert mark[1].tag == W + "footnoteReference"


@pytest.mark.parametrize("kind", ["footnote", "endnote"])
def test_create_first_note_builds_relationship_and_native_special_definitions(kind):
    doc = Document()
    doc.add_paragraph("FIRST NOTE 007 µg")
    buf = io.BytesIO()
    doc.save(buf)
    data, part = buf.getvalue(), "word/annotations/new-" + kind + "s.xml"
    result, checks = change(data, [creation(data, kind=kind, part=part, offset=5)])
    listing = NativeDocxNotes().inspect(result)
    assert [n["note_type"] for n in listing["notes"]] == [
        "separator",
        "continuationSeparator",
        "normal",
    ]
    assert listing["references"][0]["target_part"] == part
    assert listing["references"][0]["resolved_normal_note"]
    assert set(checks.changed_parts) == {
        part,
        "word/document.xml",
        "word/_rels/document.xml.rels",
        "[Content_Types].xml",
    }
    assert parts(data)["word/settings.xml"] == parts(result)["word/settings.xml"]


def test_glossary_reference_resolves_its_own_note_not_the_main_note():
    values = parts(source_document())
    owner, target = "word/glossary/document.xml", "word/glossary/footnotes.xml"
    root = etree.Element(W + "glossaryDocument", nsmap={"w": W[1:-1]})
    etree.SubElement(root, W + "footnoteReference", {W + "id": "2"})
    values[owner], values[target] = xml(root), values[FOOT]
    rels = etree.Element("{" + R + "}Relationships")
    etree.SubElement(
        rels,
        "{" + R + "}Relationship",
        Id="notes",
        Type=REL + "footnotes",
        Target="footnotes.xml",
    )
    values["word/glossary/_rels/document.xml.rels"] = xml(rels)
    types = etree.fromstring(values["[Content_Types].xml"])
    etree.SubElement(
        types,
        "{" + TYPE + "}Override",
        PartName="/" + target,
        ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
    )
    values["[Content_Types].xml"] = xml(types)
    data = package(values)
    other = next(
        r for r in NativeDocxNotes().inspect(data)["references"] if r["part"] == owner
    )
    assert other["target_part"] == target and not other["main_body_reference"]
    result, _ = change(data, [deletion(data)])
    assert (
        parts(result)[owner] == values[owner]
        and parts(result)[target] == values[target]
    )
    rels[0].set("Target", "../annotations/source-footnotes.xml")
    values["word/glossary/_rels/document.xml.rels"] = xml(rels)
    shared = package(values)
    with pytest.raises(ValueError, match="outside the main body"):
        change(shared, [deletion(shared)])


@pytest.mark.parametrize(
    "mutation", ["hash", "offset", "id", "part", "revision", "field"]
)
def test_invalid_anchor_and_identity_fail_without_modifying_input(mutation):
    data = source_document()
    if mutation in {"revision", "field"}:
        values = parts(data)
        root = etree.fromstring(values["word/document.xml"])
        p = root.find(".//" + W + "p")
        run = p[0]
        p.remove(run)
        wrapper = etree.Element(W + ("ins" if mutation == "revision" else "fldSimple"))
        wrapper.append(run)
        p.insert(0, wrapper)
        values["word/document.xml"] = xml(root)
        data = package(values)
    edit = creation(data)
    if mutation == "hash":
        edit["anchor"]["expected_text_sha256"] = "0" * 64
    elif mutation == "offset":
        edit["anchor"]["character_offset"] = 1_000_000
    elif mutation == "id":
        edit["note_id"] = 2
    elif mutation == "part":
        edit["part"] = "word/another.xml"
    before = digest(data)
    with pytest.raises(ValueError):
        change(data, [edit])
    assert digest(data) == before


def test_custom_marks_and_multiple_references_preserve_all_literal_text_on_delete():
    values = parts(source_document())
    main = etree.fromstring(values["word/document.xml"])
    ref = next(main.iter(W + "footnoteReference"))
    ref.set(W + "customMarkFollows", "1")
    etree.SubElement(ref.getparent(), W + "t").text = "* KEEP CUSTOM MARK"
    ref.getparent().insert(1, deepcopy(ref))
    values["word/document.xml"] = xml(main)
    data = package(values)
    updated, receipt = change(data, [deletion(data)])
    final = etree.fromstring(parts(updated)["word/document.xml"])
    assert [n.text for n in final.iter(W + "t")] == [n.text for n in main.iter(W + "t")]
    assert len(receipt.changes[0]["removed_references"]) == 2
    assert [n.get(W + "id") for n in final.iter(W + "footnoteReference")] == ["8"]


def test_corrupt_serialized_note_change_is_rejected(monkeypatch):
    import src.infrastructure.native_docx_note_lifecycle as module

    original = module.write_package

    def corrupt(package, values):
        roots = dict(values)
        main = etree.fromstring(roots["word/document.xml"])
        next(main.iter(W + "t")).text = "CORRUPTED"
        roots["word/document.xml"] = xml(main)
        return original(package, roots)

    data = source_document()
    monkeypatch.setattr(module, "write_package", corrupt)
    with pytest.raises(ValueError, match="Serialized note structure"):
        change(data, [creation(data)])


def test_definition_insertion_follows_body_order_without_renumbering_old_ids():
    data = source_document()
    edit = creation(data, offset=5)
    edit["note_id"] = 11
    result, receipt = change(data, [edit])
    root = etree.fromstring(parts(result)[FOOT])
    assert [n.get(W + "id") for n in root] == ["-1", "0", "11", "2", "8"]
    original = etree.fromstring(parts(data)[FOOT])
    for node in original:
        same = next(n for n in root if n.get(W + "id") == node.get(W + "id"))
        assert etree.tostring(node, method="c14n", exclusive=True) == etree.tostring(
            same, method="c14n", exclusive=True
        )
    assert receipt.changes[0]["definition_insertion_index"] == 2


@pytest.mark.parametrize(
    "bad", ["duplicate", "unresolved", "special-reference", "ambiguous-role"]
)
def test_ambiguous_or_dangling_native_graph_cannot_commit(bad):
    values = parts(source_document())
    root = etree.fromstring(values[FOOT])
    main = etree.fromstring(values["word/document.xml"])
    if bad == "duplicate":
        copied = deepcopy(root[2])
        copied.set(W + "id", "+0002")
        root.append(copied)
    elif bad == "ambiguous-role":
        root[2].set(W + "type", "invented")
    else:
        next(main.iter(W + "footnoteReference")).set(
            W + "id", "100" if bad == "unresolved" else "-1"
        )
    values[FOOT], values["word/document.xml"] = xml(root), xml(main)
    data = package(values)
    with pytest.raises(ValueError):
        change(data, [creation(data)])
