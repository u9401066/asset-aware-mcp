"""Insert a note mark at an exact Unicode boundary without flattening native runs."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from lxml import etree

from src.infrastructure.native_docx_notes import digest
from src.infrastructure.native_docx_stories import W
from src.infrastructure.native_docx_story_edits import editable_text, locate
from src.infrastructure.native_docx_structure import canonical, field_depths

if TYPE_CHECKING:
    from src.domain.native_docx_notes import DocxNoteAnchor

SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def marker_run(kind: str, identity: int | None = None) -> etree._Element:
    run = etree.Element(W + "r")
    properties = etree.SubElement(run, W + "rPr")
    etree.SubElement(properties, W + "vertAlign", {W + "val": "superscript"})
    attrs = {} if identity is None else {W + "id": str(identity)}
    etree.SubElement(
        run, W + kind + ("Ref" if identity is None else "Reference"), attrs
    )
    if identity is None:
        etree.SubElement(run, W + "tab")
    return run


def insert_anchor(
    main: etree._Element, anchor: DocxNoteAnchor, kind: str, identity: int
) -> dict[str, Any]:
    original = deepcopy(main)
    field_depths(main)
    node = locate(main, anchor.text_path)
    editable_text(main, node)
    ancestors = [n.tag for n in node.iterancestors()]
    if W + "body" not in ancestors or W + "txbxContent" in ancestors:
        raise ValueError("Note anchors require main-body text outside text boxes")
    text = node.text or ""
    if digest(
        text.encode()
    ) != anchor.expected_text_sha256 or anchor.character_offset > len(text):
        raise ValueError("Note anchor text hash or Unicode offset differs")
    run = node.getparent()
    if run is None or run.tag != W + "r" or len(anchor.text_path) < 2 or len(node):
        raise ValueError("Note anchor must address direct run text")
    properties = run.findall(W + "rPr")
    if (
        len(properties) > 1
        or (properties and run.index(properties[0]) != 0)
        or set(run.attrib) - {W + n for n in ("rsidR", "rsidRPr", "rsidDel")}
        or any(
            isinstance(n.tag, str) and n.tag.endswith("PrChange")
            for p in properties
            for n in p.iter()
        )
    ):
        raise ValueError("Note run split has ambiguous or revised formatting")
    parent = run.getparent()
    assert parent is not None
    position, child_index = parent.index(run), run.index(node)
    left, right = deepcopy(run), deepcopy(run)
    for child in list(left)[child_index + 1 :]:
        left.remove(child)
    left_node = left[child_index]
    left_node.text = text[: anchor.character_offset]
    left_node.tail = None
    for i, child in reversed(list(enumerate(right))):
        if i < child_index and child.tag != W + "rPr":
            right.remove(child)
    right_node = next(n for n in right if n.tag != W + "rPr")
    right_node.text = text[anchor.character_offset :]
    for fragment in (left_node, right_node):
        value = fragment.text or ""
        if value[:1].isspace() or value[-1:].isspace():
            fragment.set(SPACE, "preserve")
    left.tail = None
    marker = marker_run(kind, identity)
    parent.remove(run)
    for i, child in enumerate((left, marker, right), position):
        parent.insert(i, child)
    restored = deepcopy(main)
    restored_parent = locate(restored, anchor.text_path[:-2])
    for _ in range(3):
        restored_parent.remove(restored_parent[position])
    restored_parent.insert(position, deepcopy(run))
    if canonical(restored) != canonical(original):
        raise ValueError("Note insertion changed XML outside the selected run")
    # The selected run's children must partition exactly around its split w:t;
    # marker placement never rewrites adjacent text, graphics or field nodes.
    if [canonical(p) for p in properties] != [
        canonical(p) for p in right.findall(W + "rPr")
    ] or dict(right.attrib) != dict(run.attrib):
        raise ValueError("Note run split changed native formatting")
    rejoined = deepcopy(left)
    joined = rejoined[child_index]
    joined.text = (left_node.text or "") + (right_node.text or "")
    joined.tail = right_node.tail
    if SPACE in node.attrib:
        joined.set(SPACE, node.attrib[SPACE])
    else:
        joined.attrib.pop(SPACE, None)
    rejoined.extend(deepcopy(n) for n in list(right)[right.index(right_node) + 1 :])
    rejoined.tail = right.tail
    if canonical(rejoined) != canonical(run):
        raise ValueError("Note run split did not retain the complete source text")
    return {
        "source_text_path": anchor.text_path,
        "character_offset": anchor.character_offset,
        "before_run_xml": etree.tostring(run, encoding="unicode"),
        "after_runs_xml": [
            etree.tostring(n, encoding="unicode") for n in (left, marker, right)
        ],
        "reference_path": [*anchor.text_path[:-2], position + 1, 1],
        "offset_unit": "Unicode code points within the selected w:t",
    }
