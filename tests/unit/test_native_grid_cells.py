"""Original XML relocation with styles, rich content, merge anchors and rules."""

from copy import deepcopy

import pytest
from lxml import etree

from src.domain.native_grid import GridTransform, NativeGridEdit
from src.infrastructure.native_grid_cells import shift_cells, shift_columns
from src.infrastructure.native_grid_formulas import rewrite_grid_formula
from src.infrastructure.native_grid_ranges import (
    apply_merges,
    plan_merges,
    shift_ranges,
    update_dimension,
)
from src.infrastructure.native_grid_shared import (
    expand_shared_formulas,
    shift_formula_blocks,
)
from src.infrastructure.native_grid_xml import Rectangle, cell_map
from src.infrastructure.native_ooxml import SHEET_NS
from src.infrastructure.native_spreadsheet_reader import NS, NativeSpreadsheetReader
from tests.native_workbook_helpers import build_workbook


def edit(axis="row", operation="insert", at=2, count=1, **kwargs):
    return GridTransform(
        NativeGridEdit(axis=axis, operation=operation, at=at, count=count, **kwargs)
    )


def sheet(body):
    return etree.fromstring(f'<worksheet xmlns="{SHEET_NS}">{body}</worksheet>')


def relocate(root, change):
    expand_shared_formulas(root)
    shift_formula_blocks(root, change)
    shift_ranges(root, change)
    for formula in root.xpath(
        ".//s:f | .//s:formula | .//s:formula1 | .//s:formula2", namespaces=NS
    ):
        formula.text = rewrite_grid_formula(
            formula.text or "", change, owner="Data", target="Data", sheets=["Data"]
        )[0]
    plans = plan_merges(root, change)
    shift_columns(root, change)
    result = shift_cells(root, change)
    merges = apply_merges(root, plans)
    update_dimension(root)
    return result, merges


def normalized_cell(cell):
    result = deepcopy(cell)
    result.attrib.pop("r")
    return etree.tostring(result)


def test_rich_original_cells_styles_and_merge_payload_survive_row_relocation():
    root = NativeSpreadsheetReader(build_workbook())._sheet("Data")
    before = {key: normalized_cell(value) for key, value in cell_map(root).items()}
    result, merges = relocate(root, edit())
    cells = cell_map(root)
    assert result["moved_cells"] > 0
    assert normalized_cell(cells["D3"]) == before["D2"]
    assert normalized_cell(cells["A3"]) == before["A2"]
    assert normalized_cell(cells["A6"]) == before["A5"]
    assert cells["B3"].findtext("s:f", namespaces=NS) == "A3*2"
    assert cells["A2"].get("s") == cells["A1"].get("s")
    assert not len(cells["A2"])
    assert merges == [
        {
            "before": "A5:D6",
            "after": "A6:D7",
            "anchor_preserved": False,
            "remains_merged": True,
        }
    ]
    assert root.find("s:dimension", NS).get("ref") == "A1:D11"


@pytest.mark.parametrize(
    "policy,expected", [("before", "12"), ("after", "31"), ("none", None)]
)
def test_inserted_row_inherits_only_requested_format_not_values(policy, expected):
    root = sheet(
        '<sheetData><row r="1" ht="12" customHeight="1" hidden="1" outlineLevel="2"><c r="A1" s="3" t="inlineStr"><is><t>Secret</t></is></c></row><row r="2" ht="31" customHeight="1"><c r="A2" s="4"><v>42</v></c></row></sheetData>'
    )
    relocate(root, edit(inherit_format=policy, count=2))
    rows = {row.get("r"): row for row in root.findall("s:sheetData/s:row", NS)}
    assert rows["1"].get("ht") == "12" and rows["4"].get("ht") == "31"
    if expected is None:
        assert set(rows) == {"1", "4"}
    else:
        for number in ("2", "3"):
            assert rows[number].get("ht") == expected
            assert all(len(cell) == 0 for cell in rows[number])
        assert rows["2"].get("hidden") == ("1" if policy == "before" else None)


def test_column_insert_and_delete_preserves_widths_hidden_outline_and_cell_styles():
    root = sheet(
        '<cols><col min="1" max="2" width="19" hidden="1" outlineLevel="2" style="3" customWidth="1"/><col min="3" max="3" width="33" customWidth="1"/></cols><sheetData><row r="1" spans="1:3"><c r="A1" s="2"><v>7</v></c><c r="B1" s="3"><v>8</v></c><c r="C1"><v>9</v></c></row></sheetData>'
    )
    original = deepcopy(root)
    relocate(root, edit(axis="column", at=2, count=2, inherit_format="none"))
    columns = root.findall("s:cols/s:col", NS)
    assert [(c.get("min"), c.get("max"), c.get("width")) for c in columns] == [
        ("1", "1", "19"),
        ("4", "4", "19"),
        ("5", "5", "33"),
    ]
    assert columns[1].get("hidden") == "1" and columns[1].get("outlineLevel") == "2"
    assert set(cell_map(root)) == {"A1", "D1", "E1"}
    assert root.find("s:sheetData/s:row", NS).get("spans") == "1:5"
    relocate(root, edit(axis="column", operation="delete", at=2, count=2))
    assert etree.tostring(root) == etree.tostring(original)


@pytest.mark.parametrize(
    "axis,ref,at,anchor,new_ref",
    [("row", "A2:C4", 2, "A2", "A2:C3"), ("column", "B1:D2", 2, "B1", "B1:C2")],
)
def test_deleted_merge_anchor_is_preserved_at_surviving_anchor(
    axis, ref, at, anchor, new_ref
):
    number = "".join(c for c in anchor if c.isdigit())
    root = sheet(
        f'<sheetData><row r="{number}"><c r="{anchor}" s="3" t="inlineStr"><is><r><rPr><b/></rPr><t>Keep rich text</t></r></is></c></row></sheetData><mergeCells count="1"><mergeCell ref="{ref}"/></mergeCells>'
    )
    payload = normalized_cell(cell_map(root)[anchor])
    _, merges = relocate(root, edit(axis=axis, operation="delete", at=at))
    assert normalized_cell(cell_map(root)[anchor]) == payload
    assert root.find("s:mergeCells/s:mergeCell", NS).get("ref") == new_ref
    assert merges[0]["anchor_preserved"] is True


def test_merge_anchor_policy_conflicts_and_single_cell_remainders():
    source = '<sheetData><row r="1"><c r="A1"><v>1</v></c></row><row r="2"><c r="A2"><v>2</v></c></row></sheetData><mergeCells count="1"><mergeCell ref="A1:A2"/></mergeCells>'
    root = sheet(source)
    with pytest.raises(ValueError, match="overwrite"):
        relocate(root, edit(operation="delete", at=1))
    root = sheet(source)
    relocate(root, edit(operation="delete", at=1, merged_anchor="delete"))
    assert root.find("s:mergeCells", NS) is None
    assert cell_map(root)["A1"].findtext("s:v", namespaces=NS) == "2"
    root = sheet(source.replace('<c r="A2"><v>2</v></c>', '<c r="A2" s="2"/>'))
    relocate(root, edit(operation="delete", at=1))
    assert cell_map(root)["A1"].findtext("s:v", namespaces=NS) == "1"


def test_deleted_rule_origin_is_rebased_before_structural_reference_rewrite():
    root = sheet(
        '<sheetData/><conditionalFormatting sqref="A2:A4 C8:C9"><cfRule type="expression" priority="1"><formula>B2&gt;0</formula></cfRule></conditionalFormatting><dataValidations count="1"><dataValidation type="custom" sqref="D2:D4"><formula1>E2=1</formula1></dataValidation></dataValidations>'
    )
    relocate(root, edit(operation="delete", at=2, count=2))
    rule = root.find("s:conditionalFormatting", NS)
    assert rule.get("sqref") == "A2 C6:C7"
    assert rule.findtext("s:cfRule/s:formula", namespaces=NS) == "B2>0"
    validation = root.find("s:dataValidations/s:dataValidation", NS)
    assert validation.get("sqref") == "D2"
    assert validation.findtext("s:formula1", namespaces=NS) == "E2=1"


def test_full_column_rules_clip_to_grid_and_deleted_ranges_remove_empty_containers():
    root = sheet(
        '<sheetData/><dataValidations count="1"><dataValidation sqref="A1:A1048576" type="whole"><formula1>1</formula1></dataValidation></dataValidations><hyperlinks><hyperlink ref="B2" location="A1"/></hyperlinks>'
    )
    relocate(root, edit())
    assert (
        root.find("s:dataValidations/s:dataValidation", NS).get("sqref")
        == "A1:A1048576"
    )
    relocate(root, edit(operation="delete", at=3))
    assert root.find("s:hyperlinks", NS) is None


def test_shared_formula_sparse_overrides_and_ignored_follower_text_are_resolved():
    root = sheet(
        '<sheetData><row r="1"><c r="B1"><f t="shared" si="0" ref="B1:B4">$A1+C$1</f><v>0</v></c></row><row r="2"><c r="B2"><f>999</f></c></row><row r="3"><c r="B3"><f t="shared" si="0">WrongTextIgnored</f></c></row><row r="4"><c r="B4"><f t="shared" si="0"/></c></row></sheetData>'
    )
    assert expand_shared_formulas(root) == 3
    formulas = {
        location: cell.find("s:f", NS) for location, cell in cell_map(root).items()
    }
    assert [formulas[f"B{i}"].text for i in range(1, 5)] == [
        "$A1+C$1",
        "999",
        "$A3+C$1",
        "$A4+C$1",
    ]
    assert all(not formula.attrib for formula in formulas.values())
    relocate(root, edit(operation="delete", at=1))
    assert cell_map(root)["B2"].findtext("s:f", namespaces=NS) == "$A2+#REF!"


@pytest.mark.parametrize(
    "body",
    [
        '<c r="A1"><f t="shared" si="0"/></c>',
        '<c r="A1"><f t="shared" si="0" ref="A1:A2">B1</f></c><c r="B1"><f t="shared" si="0"/></c>',
        '<c r="A1"><f t="shared" si="0" ref="A1:C1">B1</f></c><c r="B1"><f t="shared" si="1" ref="B1:D1">C1</f></c>',
    ],
)
def test_invalid_shared_formula_groups_reject_before_materialization(body):
    root = sheet(f'<sheetData><row r="1">{body}</row></sheetData>')
    before = etree.tostring(root)
    with pytest.raises(ValueError):
        expand_shared_formulas(root)
    assert etree.tostring(root) == before


def test_array_blocks_shift_as_whole_partial_edits_fail_and_deleted_inputs_marked():
    root = sheet(
        '<sheetData><row r="3"><c r="B3"><f t="array" ref="B3:C4">A3:A4*2</f></c></row><row r="7"><c r="B7"><f t="dataTable" ref="B7:C8" r1="A1" r2="D9" dt2D="1"/></c></row></sheetData>'
    )
    with pytest.raises(ValueError, match="part of"):
        shift_formula_blocks(deepcopy(root), edit(at=4))
    with pytest.raises(ValueError, match="part of"):
        shift_formula_blocks(deepcopy(root), edit(operation="delete", at=3))
    relocate(root, edit(operation="delete", at=1))
    array = cell_map(root)["B2"].find("s:f", NS)
    assert array.get("ref") == "B2:C3" and array.text == "A2:A3*2"
    table = cell_map(root)["B6"].find("s:f", NS)
    assert table.get("r1") is None and table.get("del1") == "1"
    assert table.get("r2") == "D8" and table.get("ref") == "B6:C7"


def test_stored_range_overflow_and_duplicate_cells_are_not_silently_dropped():
    with pytest.raises(ValueError, match="outside"):
        Rectangle.parse("A1048576:B1048576").shift(edit())
    root = sheet('<sheetData><row r="1"><c r="A1"/><c r="A1"/></row></sheetData>')
    with pytest.raises(ValueError, match="duplicate"):
        cell_map(root)
    for value in ("$$A1:B2", "A$$1:B2", "A1:Name", "A1:B0"):
        with pytest.raises(ValueError):
            Rectangle.parse(value)
