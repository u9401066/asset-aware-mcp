"""Malformed grids, partial ranges and corruption cannot publish structural edits."""

from __future__ import annotations

import pytest
from docx.oxml.ns import qn
from lxml import etree

from src.domain.native_docx_structure import NativeDocxCreate, NativeDocxInsert
from src.infrastructure import native_docx_structure as structure
from src.infrastructure.native_docx_workspace import MAIN_PART, checked_docx
from src.infrastructure.native_ooxml import xml_bytes
from tests.native_docx_helpers import build_docx, replace_parts
from tests.native_docx_structure_helpers import creation


@pytest.mark.parametrize(
    "fault",
    [
        "xml",
        "carriage",
        "margin",
        "grid",
        "covered",
        "overlap",
        "bounds",
        "header",
        "height",
        "font",
    ],
)
def test_invalid_typed_content_is_rejected(fault):
    request = creation().model_dump()
    table = request["blocks"][1]
    if fault == "xml":
        request["blocks"][0]["runs"][0]["text"] = "bad\x00"
    elif fault == "carriage":
        request["blocks"][0]["runs"][0]["text"] = "bad\rtext"
    elif fault == "margin":
        request["margin_left_twips"] = 12240
    elif fault == "grid":
        table["cells"][0].pop()
    elif fault == "covered":
        table["cells"][0][1]["paragraphs"][0]["runs"] = [{"text": "lost"}]
    elif fault == "overlap":
        table["merges"].append(table["merges"][0])
    elif fault == "bounds":
        table["merges"][0]["end_column"] = 4
    elif fault == "header":
        table["merges"][0]["end_row"] = 1
    elif fault == "height":
        table["row_heights_twips"].pop()
    else:
        request["blocks"][0]["runs"][0]["font_size_pt"] = 11.25
    with pytest.raises(ValueError):
        NativeDocxCreate.model_validate(request)


@pytest.mark.parametrize(
    "name",
    [
        "bookmarkStart",
        "commentRangeStart",
        "sectPr",
        "footnoteReference",
        "sdt",
        "drawing",
        "fldSimple",
    ],
)
def test_deletion_rejects_known_dependencies(name):
    data = build_docx()
    root = checked_docx(data).xml(MAIN_PART)
    structure.body_of(root)[1].append(etree.Element(qn("w:" + name)))
    modified = replace_parts(data, {MAIN_PART: xml_bytes(root)})
    with pytest.raises(ValueError, match="dependencies"):
        structure.NativeDocxStructure().delete(modified, [1])


def test_insertion_and_deletion_inside_multi_paragraph_field_are_rejected():
    data = build_docx()
    root = checked_docx(data).xml(MAIN_PART)
    body = structure.body_of(root)
    for index, kind in ((0, "begin"), (2, "end")):
        run = etree.SubElement(body[index], qn("w:r"))
        field = etree.SubElement(run, qn("w:fldChar"))
        field.set(qn("w:fldCharType"), kind)
    modified = replace_parts(data, {MAIN_PART: xml_bytes(root)})
    adapter = structure.NativeDocxStructure()
    with pytest.raises(ValueError, match="inside a field"):
        adapter.insert(modified, creation().blocks, 1)
    with pytest.raises(ValueError, match="dependencies"):
        adapter.delete(modified, [1])
    adapter.insert(modified, creation().blocks, "end")


@pytest.mark.parametrize(
    "fault",
    [
        "protected",
        "signed",
        "section_order",
        "unclosed_field",
        "duplicate_delete",
        "section_delete",
        "position",
        "budget",
    ],
)
def test_package_and_structure_guards(fault, monkeypatch):
    data = build_docx()
    root = checked_docx(data).xml(MAIN_PART)
    body = structure.body_of(root)
    if fault == "protected":
        settings = checked_docx(data).xml("word/settings.xml")
        settings.append(etree.Element(qn("w:documentProtection")))
        data = replace_parts(data, {"word/settings.xml": xml_bytes(settings)})
    elif fault == "signed":
        data = replace_parts(data, {"_xmlsignatures/sig1.xml": b"<Signature/>"})
    elif fault == "section_order":
        body.insert(0, body[-1])
    elif fault == "unclosed_field":
        field = etree.SubElement(body[0], qn("w:fldChar"))
        field.set(qn("w:fldCharType"), "begin")
    elif fault == "budget":
        monkeypatch.setattr(structure, "MAX_COMPONENTS", 1)
    if fault in {"section_order", "unclosed_field"}:
        data = replace_parts(data, {MAIN_PART: xml_bytes(root)})
    adapter = structure.NativeDocxStructure()
    with pytest.raises(ValueError):
        if fault == "duplicate_delete":
            adapter.delete(data, [0, 0])
        elif fault == "section_delete":
            adapter.delete(data, [len(body) - 1])
        else:
            adapter.insert(
                data, creation().blocks, 999 if fault == "position" else "end"
            )


@pytest.mark.parametrize("fault", ["text", "cell width", "complex script size"])
def test_serialized_check_catches_corrupted_new_content(monkeypatch, fault):
    original = structure.build_blocks

    def corrupt(blocks):
        nodes = original(blocks)
        if fault == "text":
            nodes[0].find(".//" + qn("w:t")).text = "wrong"
        elif fault == "cell width":
            nodes[1].find(".//" + qn("w:tcW")).set(qn("w:w"), "1")
        else:
            nodes[0].find(".//" + qn("w:szCs")).set(qn("w:val"), "30")
        return nodes

    monkeypatch.setattr(structure, "build_blocks", corrupt)
    with pytest.raises(ValueError, match=fault):
        structure.NativeDocxStructure().insert(build_docx(), creation().blocks, "end")


def test_before_after_requires_anchor():
    for position in ("before", "after"):
        with pytest.raises(ValueError, match="anchor"):
            NativeDocxInsert(position=position, blocks=creation().blocks)
