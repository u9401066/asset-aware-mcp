"""Real package relationships determine formula context and cache invalidation."""

from copy import deepcopy

import pytest
from lxml import etree

from src.domain.native_grid import GridTransform, NativeGridEdit
from src.infrastructure.native_grid_references import (
    CHART_NS,
    GridReferences,
    clear_formula_caches,
)
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_package import NativeWorkbookPackage
from tests.native_workbook_helpers import build_workbook


def package():
    book = NativeWorkbookPackage(build_workbook())
    roots = dict(book.xml_parts(book.active_parts()))
    return book, roots, GridReferences(book, roots)


def edit(operation="insert", at=2, axis="row"):
    return GridTransform(NativeGridEdit(axis=axis, operation=operation, at=at))


def test_formula_names_cross_sheet_chart_and_threshold_follow_actual_owner():
    book, roots, refs = package()
    names = etree.SubElement(book.workbook, tag("definedNames"))
    global_name = etree.SubElement(names, tag("definedName"), name="Evidence")
    global_name.text = "'Data'!$A$2:$A$3"
    scoped = etree.SubElement(
        names, tag("definedName"), name="LocalEvidence", localSheetId="0"
    )
    scoped.text = "$A$2"
    other_scoped = etree.SubElement(
        names, tag("definedName"), name="LocalEvidence", localSheetId="1"
    )
    other_scoped.text = "$A$2"
    root = roots[book.sheets["Data"]["part"]]
    formatting = etree.SubElement(root, tag("conditionalFormatting"), sqref="D1:D3")
    rule = etree.SubElement(formatting, tag("cfRule"), type="colorScale", priority="1")
    scale = etree.SubElement(rule, tag("colorScale"))
    threshold = etree.SubElement(scale, tag("cfvo"), type="formula", val="$A$2")
    result = refs.rewrite("Data", edit())
    assert global_name.text == "'Data'!$A$3:$A$4"
    assert scoped.text == "$A$3" and other_scoped.text == "$A$2"
    assert threshold.get("val") == "$A$3"
    other = roots[book.sheets["Other"]["part"]]
    assert other.findtext("s:sheetData/s:row/s:c/s:f", namespaces=NS) == "Data!A3"
    chart = next(
        root for root in roots.values() if root.tag == f"{{{CHART_NS}}}chartSpace"
    )
    assert chart.findtext(f".//{{{CHART_NS}}}f") == "Data!$A$3:$A$4"
    assert chart.find(f".//{{{CHART_NS}}}numCache") is None
    assert result["new_ref_errors"] == 0 and result["stale_chart_caches_removed"] == 1
    assert refs.owners[book.sheets["Other"]["part"]] == {"Other"}


def test_formula_plan_does_not_apply_earlier_updates_when_later_context_is_ambiguous():
    book, roots, refs = package()
    names = etree.SubElement(book.workbook, tag("definedNames"))
    node = etree.SubElement(names, tag("definedName"), name="Ambiguous")
    node.text = "$A$2"
    before = {part: etree.tostring(root) for part, root in roots.items()}
    with pytest.raises(ValueError, match="context"):
        refs.rewrite("Data", edit())
    assert before == {part: etree.tostring(root) for part, root in roots.items()}


def test_deleted_references_are_reported_and_all_formula_caches_are_invalidated():
    book, roots, refs = package()
    result = refs.rewrite("Data", edit(operation="delete"))
    assert result["new_ref_errors"] == 2  # Data B2 and Other B1; chart range shrinks.
    assert clear_formula_caches(roots) == 2
    for name in ("Data", "Other"):
        root = roots[book.sheets[name]["part"]]
        for cell in root.xpath("./s:sheetData/s:row/s:c[s:f]", namespaces=NS):
            assert cell.find("s:v", NS) is None
    assert (
        roots[book.sheets["Data"]["part"]].findtext(
            's:sheetData/s:row/s:c[@r="A2"]/s:v', namespaces=NS
        )
        == "10"
    )


def test_pivot_ranges_shift_with_refresh_but_do_not_reassign_field_identities():
    _, roots, refs = package()
    root = etree.Element(tag("pivotCacheDefinition"))
    source = etree.SubElement(root, tag("cacheSource"), type="worksheet")
    location = etree.SubElement(
        source, tag("worksheetSource"), sheet="Data", ref="A2:C8"
    )
    roots["xl/pivotCache/pivotCacheDefinition1.xml"] = root
    assert refs.shift_sources("Data", edit()) == {
        "xl/pivotCache/pivotCacheDefinition1.xml": 1
    }
    assert location.get("ref") == "A3:C9"
    assert root.get("invalid") == "1" and root.get("refreshOnLoad") == "1"
    before = deepcopy(root)
    with pytest.raises(ValueError, match="field identities"):
        refs.shift_sources("Data", edit(axis="column"))
    assert etree.tostring(root) == etree.tostring(before)
    with pytest.raises(ValueError, match="header deletion"):
        refs.shift_sources("Data", edit(operation="delete", at=3))


def test_invalid_scoped_name_is_rejected_and_literal_ref_text_is_not_counted():
    book, _, refs = package()
    names = etree.SubElement(book.workbook, tag("definedNames"))
    node = etree.SubElement(names, tag("definedName"), name="Named", localSheetId="99")
    node.text = "A2"
    with pytest.raises(ValueError, match="scope"):
        refs.rewrite("Data", edit())


def test_array_and_data_table_result_cells_are_caches_even_without_formula_nodes():
    _, roots, _ = package()
    root = roots["xl/worksheets/sheet1.xml"]
    rows = root.find("s:sheetData", NS)
    rows[:] = []
    for number in (1, 2):
        row = etree.SubElement(rows, tag("row"), r=str(number))
        for letter in ("A", "B", "C"):
            cell = etree.SubElement(row, tag("c"), r=f"{letter}{number}")
            if (letter, number) == ("A", 1):
                formula = etree.SubElement(cell, tag("f"), t="array", ref="A1:B2")
                formula.text = "D1:E2*2"
            etree.SubElement(cell, tag("v")).text = "10"
    assert clear_formula_caches(roots) == 5  # Four array results plus Other B1.
    values = {
        cell.get("r"): cell.findtext("s:v", namespaces=NS)
        for cell in root.findall("s:sheetData/s:row/s:c", NS)
    }
    assert values == {
        "A1": None,
        "B1": None,
        "C1": "10",
        "A2": None,
        "B2": None,
        "C2": "10",
    }
