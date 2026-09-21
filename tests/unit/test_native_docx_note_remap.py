"""Explicit note ID corrections preserve content and historical identity inputs."""

from copy import deepcopy

import pytest
from lxml import etree

from tests.native_docx_notes_helpers import (
    FOOT,
    REL,
    R,
    W,
    locator,
    package,
    parts,
    source_document,
    xml,
)
from tests.unit.test_native_docx_note_guards import change


def remap(*pairs, part=FOOT, kind="footnote"):
    return {
        "op": "remap_ids",
        "part": part,
        "note_kind": kind,
        "mappings": [{"note_id": old, "new_note_id": new} for old, new in pairs],
    }


def canonical(node):
    return etree.tostring(node, method="c14n", exclusive=True)


def test_atomic_id_swap_preserves_definitions_order_text_and_source():
    data = source_document()
    before = parts(data)
    result, receipt = change(data, [remap((2, 8), (8, 2))])
    after = parts(result)
    assert receipt.changed_parts == [FOOT, "word/document.xml"]
    assert all(before[p] == after[p] for p in before if p not in receipt.changed_parts)
    for part in [FOOT, "word/document.xml"]:
        root = etree.fromstring(after[part])
        for n in root.iter(W + ("footnote" if part == FOOT else "footnoteReference")):
            if n.get(W + "id") in {"2", "8"}:
                n.set(W + "id", {"2": "8", "8": "2"}[n.get(W + "id")])
        assert canonical(root) == canonical(etree.fromstring(before[part]))
    details = receipt.changes[0]
    assert [(m["before"], m["after"]) for m in details["mappings"]] == [
        (locator(identity=2), locator(identity=8)),
        (locator(identity=8), locator(identity=2)),
    ]
    assert len(details["reference_changes"]) == 2
    assert parts(data) == before


def test_identity_mapping_is_a_byte_identical_noop():
    data = source_document()
    result, receipt = change(data, [remap((2, 2))])
    assert result == data and receipt.changed_parts == []


@pytest.mark.parametrize(
    "fault",
    [
        "collision",
        "duplicate_old",
        "duplicate_new",
        "special",
        "missing",
        "part",
        "kind",
        "negative",
        "overflow",
    ],
)
def test_invalid_mapping_cannot_change_input(fault):
    data = source_document()
    pairs = {
        "collision": [(2, 8)],
        "duplicate_old": [(2, 1), (2, 3)],
        "duplicate_new": [(2, 1), (8, 1)],
        "special": [(-1, 1)],
        "missing": [(99, 1)],
        "negative": [(2, -2)],
        "overflow": [(2, 2**31)],
    }.get(fault, [(2, 1)])
    edit = remap(*pairs)
    if fault == "part":
        edit["part"] = "word/other.xml"
    if fault == "kind":
        edit["note_kind"] = "endnote"
    before = parts(data)
    with pytest.raises(ValueError):
        change(data, [edit])
    assert parts(data) == before


def test_all_custom_body_references_change_but_literal_marks_stay():
    values = parts(source_document())
    main = etree.fromstring(values["word/document.xml"])
    node = next(main.iter(W + "footnoteReference"))
    node.set(W + "customMarkFollows", "1")
    etree.SubElement(node.getparent(), W + "t").text = "* KEEP MARK"
    node.getparent().append(deepcopy(node))
    values["word/document.xml"] = xml(main)
    updated, receipt = change(package(values), [remap((2, 17))])
    root = etree.fromstring(parts(updated)["word/document.xml"])
    assert [n.get(W + "id") for n in root.iter(W + "footnoteReference")] == [
        "17",
        "17",
        "8",
    ]
    assert "* KEEP MARK" in "".join(n.text or "" for n in root.iter(W + "t"))
    assert len(receipt.changes[0]["reference_changes"]) == 2


@pytest.mark.parametrize("wrapper", ["ins", "fldSimple", "txbxContent"])
def test_ambiguous_body_reference_scope_blocks_remapping(wrapper):
    values = parts(source_document())
    main = etree.fromstring(values["word/document.xml"])
    node = next(main.iter(W + "footnoteReference"))
    run = node.getparent()
    parent = run.getparent()
    index = parent.index(run)
    parent.remove(run)
    container = etree.Element(W + wrapper)
    container.append(run)
    parent.insert(index, container)
    values["word/document.xml"] = xml(main)
    with pytest.raises(ValueError):
        change(package(values), [remap((2, 17))])


def test_unreferenced_normal_definition_can_be_remapped():
    values = parts(source_document())
    main = etree.fromstring(values["word/document.xml"])
    ref = next(main.iter(W + "footnoteReference"))
    ref.getparent().remove(ref)
    values["word/document.xml"] = xml(main)
    updated, receipt = change(package(values), [remap((2, 17))])
    assert receipt.changed_parts == [FOOT]
    assert parts(updated)["word/document.xml"] == values["word/document.xml"]
    assert receipt.changes[0]["reference_changes"] == []


def test_shared_relationship_owner_cannot_be_silently_left_stale():
    values = parts(source_document())
    owner = etree.Element(W + "glossaryDocument", nsmap={"w": W[1:-1]})
    etree.SubElement(owner, W + "footnoteReference", {W + "id": "2"})
    values["word/glossary/document.xml"] = xml(owner)
    rels = etree.Element("{" + R + "}Relationships")
    etree.SubElement(
        rels,
        "{" + R + "}Relationship",
        Id="notes",
        Type=REL + "footnotes",
        Target="../annotations/source-footnotes.xml",
    )
    values["word/glossary/_rels/document.xml.rels"] = xml(rels)
    with pytest.raises(ValueError, match="outside the main body"):
        change(package(values), [remap((2, 17))])


def test_positive_special_id_is_also_reserved():
    values = parts(source_document())
    root = etree.fromstring(values[FOOT])
    root[0].set(W + "id", "17")
    values[FOOT] = xml(root)
    with pytest.raises(ValueError, match="collide"):
        change(package(values), [remap((2, 17))])


def test_noop_preserves_noncanonical_id_spelling():
    values = parts(source_document())
    for part, tag in [(FOOT, "footnote"), ("word/document.xml", "footnoteReference")]:
        root = etree.fromstring(values[part])
        for node in root.iter(W + tag):
            if node.get(W + "id") == "2":
                node.set(W + "id", "+0002")
        values[part] = xml(root)
    data = package(values)
    updated, receipt = change(data, [remap((2, 2))])
    assert updated == data and receipt.changed_parts == []
