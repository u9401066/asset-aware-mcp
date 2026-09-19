"""Native merges retain exact rich paragraph XML and never guess split contents."""

from copy import deepcopy

import pytest
from lxml import etree

from src.domain.native_pptx import NativePptxShapeLocator
from src.infrastructure.native_ooxml import (
    DOC_REL_NS,
    REL_NS,
    relationships_path,
    xml_bytes,
)
from src.infrastructure.native_pptx_package import NS, NativePptxPackage
from tests.native_pptx_grid_helpers import edit, grid_fixture, reference, table, texts
from tests.native_workbook_helpers import _replace


def xml(node):
    return etree.tostring(node, method="c14n", exclusive=True, with_tail=False)


def merge(**kwargs):
    return {
        "op": "merge",
        "row": 1,
        "column": 0,
        "end_row": 2,
        "end_column": 1,
        "content_policy": "append_paragraphs",
        **kwargs,
    }


def test_nonempty_rectangle_merge_retains_literals_in_row_major_paragraphs():
    data, ref, _ = grid_fixture(merge=None)
    updated, result = edit(data, ref, merge())
    target = table(updated)
    assert target.cell(1, 0).text == "A101\n007\nA102\n12"
    assert target.cell(1, 0).span_height == target.cell(1, 0).span_width == 2
    assert (
        target.cell(1, 1).text == target.cell(2, 0).text == target.cell(2, 1).text == ""
    )
    assert target.cell(1, 2).text == "-0.50\nmg/L"
    assert target.cell(2, 2).text == "=SUM(A1:A2)"
    assert result.changes[0]["migrated_paragraphs"] == 3


@pytest.mark.parametrize("merge_kind", ["horizontal", "vertical", "rectangle"])
def test_split_and_remerge_empty_coverage_preserves_every_cell_xml(merge_kind):
    data, ref, _ = grid_fixture(merge=merge_kind)
    original = table(data)
    end_row, end_column = (
        original.cell(0, 0).span_height - 1,
        original.cell(0, 0).span_width - 1,
    )
    updated, result = edit(
        data,
        ref,
        {"op": "split", "row": 0, "column": 0},
        merge(
            row=0,
            column=0,
            end_row=end_row,
            end_column=end_column,
            content_policy="require_empty",
        ),
    )
    assert texts(updated) == texts(data)
    target = table(updated)
    for r in range(3):
        for c in range(3):
            assert xml(target.cell(r, c)._tc) == xml(original.cell(r, c)._tc)
    assert (
        result.changes[0]["split_regions"] == result.changes[0]["merged_regions"] == 1
    )


def test_split_keeps_migrated_paragraphs_at_anchor_without_redistribution():
    data, ref, _ = grid_fixture(merge=None)
    updated, _ = edit(data, ref, merge(), {"op": "split", "row": 1, "column": 0})
    assert table(updated).cell(1, 0).text == "A101\n007\nA102\n12"
    assert all(
        not table(updated).cell(r, c).is_spanned for r in range(3) for c in range(3)
    )
    assert table(updated).cell(2, 1).text == ""


def test_merge_can_wholly_contain_an_existing_merge():
    data, ref, _ = grid_fixture(merge="rectangle")
    updated, _ = edit(data, ref, merge(row=0, column=0, end_row=2, end_column=2))
    assert (
        table(updated).cell(0, 0).span_height
        == table(updated).cell(0, 0).span_width
        == 3
    )
    assert (
        table(updated).cell(0, 0).text
        == "樣本 & 結果\nValue\n-0.50\nmg/L\nA102\n12\n=SUM(A1:A2)"
    )


@pytest.mark.parametrize(
    "region,grouped", [("slide", False), ("notes", False), ("slide", True)]
)
def test_merge_moves_fields_links_foreign_xml_and_styles_with_paragraphs(
    region, grouped
):
    data, ref, _ = grid_fixture(region=region, grouped=grouped, merge=None)
    package = NativePptxPackage(data)
    locator = NativePptxShapeLocator(**ref["locator"])
    node = package.locate(locator)
    rows = node.findall(".//a:tbl/a:tr", NS)
    source = rows[1].findall("a:tc", NS)[1]
    paragraph = source.find("a:txBody/a:p", NS)
    paragraph.set("{urn:custom}id", "paragraph007")
    props = paragraph.find("a:r/a:rPr", NS)
    etree.SubElement(
        props, f"{{{NS['a']}}}hlinkClick", {f"{{{NS['r']}}}id": "rIdMergeLink"}
    )
    field = etree.SubElement(
        paragraph, f"{{{NS['a']}}}fld", id="fixed-field", type="datetime"
    )
    etree.SubElement(field, f"{{{NS['a']}}}t").text = "2026"
    etree.SubElement(paragraph, "{urn:custom}annotation").text = "retain"
    rels_path = relationships_path(locator.part)
    rels = package.xml(rels_path)
    etree.SubElement(
        rels,
        f"{{{REL_NS}}}Relationship",
        Id="rIdMergeLink",
        Type=f"{DOC_REL_NS}/hyperlink",
        Target="https://example.com/merge-proof",
        TargetMode="External",
    )
    original_paragraph = deepcopy(paragraph)
    source_props = deepcopy(source.find("a:tcPr", NS))
    data = _replace(data, {locator.part: xml_bytes(package.roots[locator.part])})
    data = _replace(data, {rels_path: xml_bytes(rels)})
    package = NativePptxPackage(data)
    updated, _ = edit(data, reference(data, locator), merge(end_row=1, end_column=1))
    after = NativePptxPackage(updated)
    cells = after.locate(locator).findall(".//a:tbl/a:tr", NS)[1].findall("a:tc", NS)
    moved = cells[0].findall("a:txBody/a:p", NS)[1]
    assert xml(moved) == xml(original_paragraph)
    assert xml(cells[1].find("a:tcPr", NS)) == xml(source_props)
    assert len(cells[1].findall("a:txBody/a:p", NS)) == 1
    assert len(cells[1].find("a:txBody/a:p", NS)) == 0
    for name, raw in package.parts.items():
        if name != locator.part:
            assert after.parts[name] == raw


def test_empty_anchor_and_internal_empty_paragraphs_are_not_silently_discarded():
    data, ref, _ = grid_fixture(merge=None)
    package = NativePptxPackage(data)
    locator = NativePptxShapeLocator(**ref["locator"])
    row = package.locate(locator).findall(".//a:tbl/a:tr", NS)[1]
    row[0].find("a:txBody/a:p/a:r/a:t", NS).text = ""
    source = row[1].find("a:txBody", NS)
    etree.SubElement(source, f"{{{NS['a']}}}p")
    data = _replace(data, {locator.part: xml_bytes(package.roots[locator.part])})
    updated, result = edit(
        data, reference(data, locator), merge(end_row=1, end_column=1)
    )
    assert table(updated).cell(1, 0).text == "\n007\n"
    assert result.changes[0]["migrated_paragraphs"] == 2


def test_new_subdivisions_can_be_composed_with_split_insert_and_merge():
    data, ref, _ = grid_fixture()
    updated, _ = edit(
        data,
        ref,
        {"op": "split", "row": 0, "column": 0},
        {"op": "insert", "axis": "column", "index": 1, "sizes": [250000]},
        merge(row=0, column=0, end_row=0, end_column=2, content_policy="require_empty"),
    )
    assert len(table(updated).columns) == 4
    assert table(updated).cell(0, 0).span_width == 3
    assert table(updated).cell(1, 2).text == "007"


def test_missing_optional_anchor_body_is_created_without_losing_source_paragraph():
    data, ref, _ = grid_fixture(merge=None)
    package = NativePptxPackage(data)
    locator = NativePptxShapeLocator(**ref["locator"])
    cells = package.locate(locator).findall(".//a:tbl/a:tr", NS)[1].findall("a:tc", NS)
    cells[0].remove(cells[0].find("a:txBody", NS))
    expected = xml(cells[1].find("a:txBody/a:p", NS))
    data = _replace(data, {locator.part: xml_bytes(package.roots[locator.part])})
    updated, result = edit(
        data, reference(data, locator), merge(end_row=1, end_column=1)
    )
    after = NativePptxPackage(updated).locate(locator)
    anchor = after.findall(".//a:tbl/a:tr", NS)[1].findall("a:tc", NS)[0]
    assert xml(anchor.find("a:txBody/a:p", NS)) == expected
    assert table(updated).cell(1, 0).text == "007"
    assert result.changes[0]["migrated_paragraphs"] == 1
