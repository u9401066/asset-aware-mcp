"""Header/footer content CRUD must retain native formatting and precise bindings."""

import pytest
from lxml import etree

from src.domain.native_docx_stories import DocxStoryUpdate
from src.infrastructure.native_docx_stories import NativeDocxStories
from src.infrastructure.native_docx_workspace import checked_docx
from src.infrastructure.native_ooxml import xml_bytes
from tests.native_docx_stories_helpers import HEADER_PART, HEADER_TEXT, story_document


def test_complete_native_story_and_actual_inherited_bindings():
    adapter = NativeDocxStories()
    data = story_document()
    listing = adapter.inspect(data)
    assert len(listing["sections"]) == 2
    record = adapter.read(data, HEADER_PART)
    assert HEADER_TEXT in record["text"] and "END-HEADER" in record["xml"]
    assert "KEEP-ITALIC" in record["text"] and "-0.50 mg/L" in record["text"]
    bindings = record["bindings"]
    assert [
        (b["section_index"], b["variant"], b["inherited_from"]) for b in bindings
    ] == [(0, "default", None), (1, "default", 0)]
    first = adapter.read(data, "word/header1.xml")
    assert {b["variant"] for b in first["bindings"]} == {"first"}
    assert [b["enabled"] for b in first["bindings"]] == [True, False]


def test_story_text_insert_delete_preserve_native_xml_and_other_parts():
    adapter = NativeDocxStories()
    data = story_document()
    before = adapter.read(data, HEADER_PART)
    node = next(n for n in before["text_nodes"] if n["text"] == HEADER_TEXT)
    plan = DocxStoryUpdate.model_validate(
        {
            "part": HEADER_PART,
            "shared_scope": "all_sections_using_part",
            "edits": [
                {
                    "op": "set_text",
                    "path": node["path"],
                    "text": "CORRECTED 007 µg END-HEADER",
                },
                {
                    "op": "insert_blocks",
                    "index": 3,
                    "blocks": [
                        {
                            "kind": "paragraph",
                            "runs": [{"text": "NEW EVIDENCE 1,234.50", "bold": True}],
                        }
                    ],
                },
                {"op": "delete_blocks", "index": 2, "count": 1},
            ],
        }
    )
    updated, receipt = adapter.edit(data, plan)
    after = adapter.read(updated, HEADER_PART)
    assert "CORRECTED 007 µg END-HEADER" in after["text"]
    assert "NEW EVIDENCE 1,234.50" in after["text"]
    assert "REMOVE THIS PARAGRAPH" not in after["text"]
    assert after["bindings"] == before["bindings"]
    assert receipt.changed_parts == [HEADER_PART]
    original, result = checked_docx(data), checked_docx(updated)
    assert all(
        result.parts[p] == b for p, b in original.parts.items() if p != HEADER_PART
    )
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    assert result.xml(HEADER_PART).find(".//" + w + "b") is not None
    assert result.xml(HEADER_PART).find(".//" + w + "i") is not None
    assert original.xml(HEADER_PART).find(w + "tbl") is not None
    assert receipt.changes[0]["before"] == HEADER_TEXT
    assert receipt.changes[0]["after"] == "CORRECTED 007 µg END-HEADER"


def test_noop_is_exact_bytes():
    adapter = NativeDocxStories()
    data = story_document()
    node = adapter.read(data, HEADER_PART)["text_nodes"][0]
    updated, result = adapter.edit(
        data,
        DocxStoryUpdate.model_validate(
            {
                "part": HEADER_PART,
                "shared_scope": "all_sections_using_part",
                "edits": [{"op": "set_text", **node}],
            }
        ),
    )
    assert updated == data and result.changed_parts == []


def test_fields_cannot_be_changed_as_ordinary_text():
    adapter = NativeDocxStories()
    data = story_document()
    field = next(
        n
        for n in adapter.read(data, "word/footer1.xml")["text_nodes"]
        if n["text"] == "1"
    )
    with pytest.raises(ValueError, match="field"):
        adapter.edit(
            data,
            DocxStoryUpdate.model_validate(
                {
                    "part": "word/footer1.xml",
                    "shared_scope": "all_sections_using_part",
                    "edits": [{"op": "set_text", "path": field["path"], "text": "99"}],
                }
            ),
        )


def test_explicit_shared_scope_and_typed_edits_required():
    with pytest.raises(ValueError):
        DocxStoryUpdate.model_validate(
            {
                "part": HEADER_PART,
                "edits": [{"op": "delete_blocks", "index": 0, "count": 1}],
            }
        )


@pytest.mark.parametrize("wrapper", ["locked", "bound", "ins", "fldSimple"])
def test_guarded_native_text_is_not_silently_rewritten(wrapper):
    adapter = NativeDocxStories()
    data = story_document()
    package = checked_docx(data)
    root = package.xml(HEADER_PART)
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraph = root[0]
    root.remove(paragraph)
    if wrapper in {"locked", "bound"}:
        container = etree.SubElement(root, w + "sdt")
        properties = etree.SubElement(container, w + "sdtPr")
        etree.SubElement(
            properties, w + ("lock" if wrapper == "locked" else "dataBinding")
        )
        etree.SubElement(container, w + "sdtContent").append(paragraph)
    else:
        container = etree.SubElement(root, w + wrapper)
        container.append(paragraph)
    data = package.replace({HEADER_PART: xml_bytes(root)})
    node = next(
        n
        for n in adapter.read(data, HEADER_PART)["text_nodes"]
        if n["text"] == HEADER_TEXT
    )
    with pytest.raises(ValueError, match=r"field|revision|control"):
        adapter.edit(
            data,
            DocxStoryUpdate.model_validate(
                {
                    "part": HEADER_PART,
                    "shared_scope": "all_sections_using_part",
                    "edits": [
                        {"op": "set_text", "path": node["path"], "text": "wrong"}
                    ],
                }
            ),
        )


@pytest.mark.parametrize(
    "tag", ["bookmarkStart", "commentRangeStart", "drawing", "footnoteReference"]
)
def test_deletion_preserves_ranged_and_related_native_content(tag):
    data = story_document()
    package = checked_docx(data)
    root = package.xml(HEADER_PART)
    etree.SubElement(
        root[0], "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}" + tag
    )
    data = package.replace({HEADER_PART: xml_bytes(root)})
    with pytest.raises(ValueError, match="dependencies"):
        NativeDocxStories().edit(
            data,
            DocxStoryUpdate.model_validate(
                {
                    "part": HEADER_PART,
                    "shared_scope": "all_sections_using_part",
                    "edits": [{"op": "delete_blocks", "index": 0, "count": 1}],
                }
            ),
        )


def test_injected_unrelated_xml_change_is_rejected(monkeypatch):
    import src.infrastructure.native_docx_story_edits as module

    real = module.build_blocks

    def corrupted(blocks):
        result = real(blocks)
        result[0].find(
            ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
        ).text = "wrong"
        return result

    monkeypatch.setattr(module, "build_blocks", corrupted)
    with pytest.raises(ValueError):
        NativeDocxStories().edit(
            story_document(),
            DocxStoryUpdate.model_validate(
                {
                    "part": HEADER_PART,
                    "shared_scope": "all_sections_using_part",
                    "edits": [
                        {
                            "op": "insert_blocks",
                            "index": 0,
                            "blocks": [
                                {"kind": "paragraph", "runs": [{"text": "intended"}]}
                            ],
                        }
                    ],
                }
            ),
        )


def test_invalid_relationship_is_not_guessed_from_filename():
    package = checked_docx(story_document())
    root = package.xml("word/document.xml")
    ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    root.find(
        ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}headerReference"
    ).set(ns + "id", "missing")
    with pytest.raises(ValueError, match="reference"):
        NativeDocxStories().inspect(
            package.replace({"word/document.xml": xml_bytes(root)})
        )


def test_comments_have_process_independent_tags():
    package = checked_docx(story_document())
    root = package.xml(HEADER_PART)
    root.insert(0, etree.Comment("keep this comment"))
    data = package.replace({HEADER_PART: xml_bytes(root)})
    assert NativeDocxStories().read(data, HEADER_PART)["blocks"][0]["tag"] == "#comment"


def test_default_content_type_and_unbound_story_are_discovered():
    import io
    import zipfile

    package = checked_docx(story_document())
    types = package.xml("[Content_Types].xml")
    etree.SubElement(
        types,
        "{http://schemas.openxmlformats.org/package/2006/content-types}Default",
        Extension="headerpart",
        ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
    )
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in package.parts.items():
            z.writestr(
                name, xml_bytes(types) if name == "[Content_Types].xml" else data
            )
        z.writestr("alternate.headerpart", package.parts[HEADER_PART])
    record = NativeDocxStories().read(result.getvalue(), "alternate.headerpart")
    assert record["bindings"] == [] and HEADER_TEXT in record["text"]


def test_native_table_insertion_and_removal_is_exact_noop():
    data = story_document()
    request = DocxStoryUpdate.model_validate(
        {
            "part": HEADER_PART,
            "shared_scope": "all_sections_using_part",
            "edits": [
                {
                    "op": "insert_blocks",
                    "index": 1,
                    "blocks": [
                        {
                            "kind": "table",
                            "column_widths_twips": [2000],
                            "cells": [
                                [
                                    {
                                        "paragraphs": [
                                            {"runs": [{"text": "007", "bold": True}]}
                                        ]
                                    }
                                ]
                            ],
                        }
                    ],
                },
                {"op": "delete_blocks", "index": 1, "count": 1},
            ],
        }
    )
    result, receipt = NativeDocxStories().edit(data, request)
    assert result == data and receipt.changed_parts == []


def test_sequential_paths_follow_the_intermediate_tree():
    data = story_document()
    adapter = NativeDocxStories()
    path = adapter.read(data, HEADER_PART)["text_nodes"][0]["path"]
    request = DocxStoryUpdate.model_validate(
        {
            "part": HEADER_PART,
            "shared_scope": "all_sections_using_part",
            "edits": [
                {
                    "op": "insert_blocks",
                    "index": 0,
                    "blocks": [{"kind": "paragraph", "runs": [{"text": "temporary"}]}],
                },
                {
                    "op": "set_text",
                    "path": [path[0] + 1, *path[1:]],
                    "text": "intended original paragraph",
                },
                {"op": "delete_blocks", "index": 0, "count": 1},
            ],
        }
    )
    result, _ = adapter.edit(data, request)
    record = adapter.read(result, HEADER_PART)
    assert record["text_nodes"][0]["text"] == "intended original paragraph"
    assert "temporary" not in record["text"]
