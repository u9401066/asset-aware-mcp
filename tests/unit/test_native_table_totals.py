"""Totals roles change without moving data or silently retaining invalid formula scope."""

import io

import openpyxl
import pytest
from lxml import etree

from src.infrastructure.native_grid_source_ranges import table_bounds
from src.infrastructure.native_grid_table_state import table_states
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_spreadsheet import NativeSpreadsheet
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_table_detached_formulas import freeze_totals_formula
from src.infrastructure.native_workbook_plan import WorkbookPlan
from src.infrastructure.native_workbook_table_edit import NativeWorkbookTableEdit
from tests.native_grid_helpers import table_workbook
from tests.native_workbook_helpers import _parts
from tests.unit.test_native_grid_metadata import CACHE, with_pivot_source
from tests.unit.test_native_grid_tables import read, table
from tests.unit.test_native_workbook_table_edit import column, mutate, request

SHEET = "xl/worksheets/sheet1.xml"
TABLE = "xl/tables/table1.xml"


def assert_shared_strings_preserved(source, updated):
    original = etree.fromstring(_parts(source)["xl/sharedStrings.xml"])
    current = etree.fromstring(_parts(updated)["xl/sharedStrings.xml"])
    assert [etree.tostring(n, method="c14n") for n in current] == [
        etree.tostring(n, method="c14n") for n in original
    ]
    references = sum(
        len(etree.fromstring(data).xpath(".//s:c[@t='s']", namespaces=NS))
        for part, data in _parts(updated).items()
        if part.startswith("xl/worksheets/") and part.endswith(".xml")
    )
    assert int(current.get("count")) == references


def transition(source, action, *columns, **intent):
    return NativeWorkbookTableEdit().update(
        source,
        request(
            *columns,
            ref=table(source).get("ref"),
            totals_row={"action": action, **intent},
        ),
    )


def test_clear_remove_and_reuse_preserve_data_styles_filters_and_hidden_metadata():
    source = table_workbook(totals=True)
    removed, receipt = transition(source, "remove", cells="clear")
    assert table(removed).get("ref") == "A2:C5"
    assert table(removed).get("totalsRowCount") == "0"
    assert table(removed).get("totalsRowShown") == "0"
    for col in "ABC":
        assert read(removed, col + "6")["kind"] == "blank"
        assert (
            read(removed, col + "6")["style_index"]
            == read(source, col + "6")["style_index"]
        )
    restored, result = transition(removed, "add")
    assert table(restored).get("ref") == "A2:C6"
    assert table(restored).get("totalsRowShown") == "1"
    assert table(restored).find("s:autoFilter", NS).get("ref") == "A2:C5"
    assert read(restored, "B6")["value"] == "=SUBTOTAL(109,[Calc])"
    assert read(restored, "C6")["value"] == "Total"
    for current in (removed, restored):
        for row in (3, 4, 5):
            for col in "ABC":
                for key in ("kind", "value", "style_index"):
                    assert (
                        read(current, f"{col}{row}")[key]
                        == read(source, f"{col}{row}")[key]
                    )
        for part in ("xl/styles.xml", "customXml/unchanged.xml"):
            assert _parts(current)[part] == _parts(source)[part]
        assert_shared_strings_preserved(source, current)
        assert etree.tostring(
            table(current).find("s:autoFilter", NS)
        ) == etree.tostring(table(source).find("s:autoFilter", NS))
    assert receipt.changes[0]["totals_transition"]["worksheet_rows_moved"] is False
    assert result.changes[0]["cells"]["B6"]["before"]["kind"] == "blank"
    book = openpyxl.load_workbook(io.BytesIO(restored))
    try:
        assert book["Data"].tables["Table1"].totalsRowCount == 1
        assert book["Data"]["C6"].value == "Total"
    finally:
        book.close()


@pytest.mark.parametrize("discard_at", ["remove", "add"])
def test_definitions_can_be_discarded_at_either_transition(discard_at):
    removed, _ = transition(
        table_workbook(totals=True),
        "remove",
        cells="clear",
        retain_definitions=discard_at != "remove",
    )
    added, _ = transition(removed, "add", reuse_definitions=discard_at != "add")
    assert all(read(added, col + "6")["kind"] == "blank" for col in "ABC")
    for node in table(added).findall("s:tableColumns/s:tableColumn", NS):
        assert node.get("totalsRowFunction") is None
        assert node.get("totalsRowLabel") is None
        assert node.find("s:totalsRowFormula", NS) is None


def test_add_with_rename_and_explicit_overrides_uses_final_column_names():
    source = table_workbook()
    updated, result = transition(
        source,
        "add",
        column(name="Amount", totals={"kind": "label", "value": "合計"}),
        column(
            2, "Calc", name="Doubled", totals={"kind": "function", "value": "average"}
        ),
        column(3, "Label", totals={"kind": "formula", "value": "=SUM([Amount])"}),
        cell_styles="last_data_row",
    )
    assert read(updated, "B6")["value"] == "=SUBTOTAL(101,[Doubled])"
    assert read(updated, "C6")["value"] == "=SUM([Amount])"
    assert read(updated, "A6")["value"] == "合計"
    assert read(updated, "B3")["value"] == "=[[#This Row],Amount]*2"
    for col in "ABC":
        assert (
            read(updated, col + "6")["style_index"]
            == read(source, col + "5")["style_index"]
        )
    assert result.changes[0]["cells"]["A6"]["before"]["kind"] == "blank"


def test_remove_keep_freezes_own_formulas_only_and_retains_external_totals_selector():
    source = table_workbook(totals=True)
    source = mutate(
        source,
        "xl/worksheets/sheet2.xml",
        lambda root: setattr(
            root.find(".//s:c[@r='A2']/s:f", NS), "text", "SUM(Table1[#Totals])"
        ),
    )
    updated, receipt = transition(source, "remove", cells="keep_cells")
    assert read(updated, "B6")["value"] == "=SUBTOTAL(109,'Data'!$B$3:$B$5)"
    assert read(updated, "C6")["value"] == "Total"
    assert (
        NativeSpreadsheet(updated).read_cell("Other", "A2")["value"]
        == "=SUM(Table1[#Totals])"
    )
    assert (
        receipt.changes[0]["cells"]["B6"]["before"]["value"] == "=SUBTOTAL(109,[Calc])"
    )
    assert "C6" not in receipt.changes[0]["cells"]
    with pytest.raises(ValueError, match="blank cells"):
        transition(updated, "add")


@pytest.mark.parametrize(
    "formula, expected",
    [
        ("=SUM([Input])", "=SUM('Data'!$A$3:$A$5)"),
        ("=SUM(Table1)", "=SUM('Data'!$A$3:$C$5)"),
        ("=SUM(Table1[[#All],[Input]:[Label]])", "=SUM('Data'!$A$2:$C$6)"),
        ("=SUM(Table1[[#Data],[#Totals],[Calc]])", "=SUM('Data'!$B$3:$B$6)"),
        ("=SUM(Table1[Input]:Table1[Label])", "=SUM('Data'!$A$3:$C$5)"),
        ("=@'data'!Table1[Input]", "=@'Data'!$A$3:$A$5"),
        ('=SUM([Input])+LEN("[Input]")', "=SUM('Data'!$A$3:$A$5)+LEN(\"[Input]\")"),
        (
            "=SUM('[book.xlsx]Data'!Table1[Input])+SUM([Calc])",
            "=SUM('[book.xlsx]Data'!Table1[Input])+SUM('Data'!$B$3:$B$5)",
        ),
        ("=SUM(Table2[Input])+A3", "=SUM(Table2[Input])+A3"),
    ],
)
def test_retained_formula_parser_preserves_exact_scopes(formula, expected):
    plan = WorkbookPlan(table_workbook(totals=True))
    assert freeze_totals_formula(formula, table_states(plan)[0], "Data") == expected


@pytest.mark.parametrize(
    "formula",
    [
        "=Table1[Input]:D8",
        "=[@Input]",
        "=Table1[[#This Row],[Input]:[Calc]]",
        "=Table1[Input]:Table2[Calc]",
        "=Table1[[#Headers],[#Totals]]",
        "=Table1[[Input],[Label]]",
        "='Other'!Table1[Input]",
        "=Table1[Unknown]",
        "=Table1[[#This Row],[#Data],[Input]]",
        "=Table1[Input]:Table1[Calc]:Table1[Label]",
    ],
)
def test_ambiguous_retained_formulas_require_explicit_edit(formula):
    source = mutate(
        table_workbook(totals=True),
        SHEET,
        lambda root: setattr(root.find(".//s:c[@r='B6']/s:f", NS), "text", formula[1:]),
    )
    with pytest.raises(ValueError):
        transition(source, "remove", cells="keep_cells")
    cleared, _ = transition(source, "remove", cells="clear")
    assert read(cleared, "B6")["kind"] == "blank"


def test_escaped_column_name_is_not_a_current_row_selector():
    plan = WorkbookPlan(table_workbook(totals=True, first="@Price [net]"))
    state = table_states(plan)[0]
    assert (
        freeze_totals_formula("=SUM(['@Price '[net']])", state, "Data")
        == "=SUM('Data'!$A$3:$A$5)"
    )


@pytest.mark.parametrize("row", [2, 3, 6])
def test_current_row_requires_actual_data_context(row):
    state = table_states(WorkbookPlan(table_workbook(totals=True)))[0]
    if row == 3:
        assert (
            table_bounds(state, "[@Input]", source_name=False, current_row=row).text
            == "A3"
        )
    else:
        with pytest.raises(ValueError, match="no data-row context"):
            table_bounds(state, "[@Input]", source_name=False, current_row=row)


@pytest.mark.parametrize("cells", ["clear", "keep_cells"])
def test_rich_totals_clear_or_keep_preserves_styles_and_shared_string_bytes(cells):
    def rich(root):
        cell = root.find(".//s:c[@r='C6']", NS)
        cell[:] = []
        cell.set("t", "inlineStr")
        inline = etree.SubElement(cell, tag("is"))
        for value, style in (("總", "b"), ("計", "i")):
            run = etree.SubElement(inline, tag("r"))
            etree.SubElement(etree.SubElement(run, tag("rPr")), tag(style))
            etree.SubElement(run, tag("t")).text = value

    source = mutate(table_workbook(totals=True), SHEET, rich)
    updated, _ = transition(source, "remove", cells=cells)
    assert read(updated, "C6")["value"] == (None if cells == "clear" else "總計")
    assert read(updated, "C6")["style_index"] == read(source, "C6")["style_index"]
    assert_shared_strings_preserved(source, updated)
    if cells == "keep_cells":
        for data in (source, updated):
            root = etree.fromstring(_parts(data)[SHEET])
            assert len(root.findall(".//s:c[@r='C6']/s:is/s:r", NS)) == 2


def test_named_totals_pivot_source_cannot_disappear():
    source = mutate(
        with_pivot_source(table_workbook(totals=True)),
        CACHE,
        lambda root: root.find("s:cacheSource/s:worksheetSource", NS).set(
            "name", "Table1[#Totals]"
        ),
    )
    with pytest.raises(ValueError, match="no surviving rows"):
        transition(source, "remove", cells="clear")


def test_direct_source_on_detached_row_still_checks_header_and_invalidates_cache():
    def detached(root):
        node = root.find("s:cacheSource/s:worksheetSource", NS)
        node.attrib.clear()
        node.set("ref", "B6:C8")
        node.set("sheet", "Data")

    source = mutate(with_pivot_source(table_workbook(totals=True)), CACHE, detached)
    for cells in ("clear", "keep_cells"):
        with pytest.raises(ValueError, match="cache field identities"):
            transition(source, "remove", cells=cells)
    source = mutate(
        source,
        CACHE,
        lambda root: root.find("s:cacheSource/s:worksheetSource", NS).set(
            "ref", "C6:C8"
        ),
    )
    updated, receipt = transition(source, "remove", cells="keep_cells")
    assert etree.fromstring(_parts(updated)[CACHE]).get("invalid") == "1"
    assert receipt.changes[0]["invalidated_pivot_caches"] == [CACHE]


@pytest.mark.parametrize(
    "intent",
    [
        {},
        {"action": "remove"},
        {"action": "remove", "cells": "keep"},
        {"action": "add", "reuse_definitions": "true"},
        {"action": "add", "insert_rows": True},
    ],
)
def test_transition_schema_requires_exact_intent(intent):
    with pytest.raises(ValueError):
        request(totals_row=intent)


def test_empty_update_and_totals_edit_during_removal_are_rejected():
    with pytest.raises(ValueError):
        request()
    with pytest.raises(ValueError):
        request(
            column(totals={"kind": "blank"}),
            totals_row={"action": "remove", "cells": "clear"},
        )


def test_transition_requires_actual_role_state():
    with pytest.raises(ValueError, match="already has"):
        transition(table_workbook(totals=True), "add")
    with pytest.raises(ValueError, match="no totals row"):
        transition(table_workbook(), "remove", cells="clear")
