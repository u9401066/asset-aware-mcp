"""Exact named-source scope, table selectors and indirect pivot schema dependencies."""

import pytest
from lxml import etree

from src.infrastructure.native_grid_source_ranges import GridSourceResolver
from src.infrastructure.native_grid_table_state import table_states
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_grid import NativeWorkbookGrid
from src.infrastructure.native_workbook_plan import WorkbookPlan
from tests.native_grid_helpers import table_workbook
from tests.native_workbook_helpers import _parts, _replace
from tests.unit.test_native_grid_metadata import CACHE, with_pivot_source
from tests.unit.test_native_workbook_grid import request, root


def named_source(*definitions, name="Proxy", owner=None):
    source = with_pivot_source(table_workbook())
    book = root(source, "xl/workbook.xml")
    container = book.find("s:definedNames", NS)
    for key, text, scope in definitions:
        node = etree.SubElement(container, tag("definedName"), name=key)
        if scope is not None:
            node.set("localSheetId", str(scope))
        node.text = text
    cache = root(source, CACHE)
    selector = cache.find("s:cacheSource/s:worksheetSource", NS)
    selector.set("name", name)
    if owner is not None:
        selector.set("sheet", owner)
    return _replace(
        source, {"xl/workbook.xml": etree.tostring(book), CACHE: etree.tostring(cache)}
    )


@pytest.mark.parametrize(
    "expression,expected",
    [
        ("Table1", "A2:C6"),
        ("Table1[#All]", "A2:C6"),
        ("AllData", "A2:C6"),
        ("Table1[#Data]", "A3:C5"),
        ("Table1[#Headers]", "A2:C2"),
        ("Table1[#Totals]", "A6:C6"),
        ("Table1[[#Headers],[#Data]]", "A2:C5"),
        ("Table1[[#All],[Input]:[Calc]]", "A2:B6"),
        ("Table1[Calc]", "B3:B5"),
        ("'Data'!$A$2:$C$5", "A2:C5"),
    ],
)
def test_static_table_items_and_a1_ranges_resolve_exactly(expression, expected):
    plan = WorkbookPlan(table_workbook(totals=True))
    resolved = GridSourceResolver(plan, table_states(plan)).resolve(expression)
    assert resolved.sheet == "Data" and resolved.bounds.text == expected


@pytest.mark.parametrize(
    "expression",
    [
        "Table1[@Input]",
        "Table1[[#This Row],[Input]]",
        "Table1[[#Headers],[#Totals]]",
        "Table1[[Input],[Label]]",
        "OFFSET(Data!$A$2,0,0,4,3)",
        'INDIRECT("Data!A2:C5")',
    ],
)
def test_dynamic_or_disjoint_sources_require_explicit_evaluation(expression):
    plan = WorkbookPlan(table_workbook(totals=True))
    with pytest.raises(ValueError):
        GridSourceResolver(plan, table_states(plan)).resolve(expression)


def test_name_chains_keep_pivot_cache_in_sync_and_block_indirect_schema_changes():
    source = named_source(("Alias", "AllData", None), ("Proxy", "(Alias)", None))
    updated, result = NativeWorkbookGrid().update(
        source, request({"axis": "row", "operation": "insert", "at": 4})
    )
    assert root(updated, CACHE).get("refreshOnLoad") == "1"
    assert result.changes[0]["edits"][0]["invalidated_named_source_caches"] == [CACHE]
    with pytest.raises(ValueError, match="cache field identities"):
        NativeWorkbookGrid().update(
            source, request({"axis": "column", "operation": "delete", "at": 2})
        )


def test_named_a1_source_moves_and_rejects_deleted_header():
    source = named_source(("Proxy", "Data!$D$8:$F$12", None))
    updated, _ = NativeWorkbookGrid().update(source, request())
    name = root(updated, "xl/workbook.xml").find(
        's:definedNames/s:definedName[@name="Proxy"]', NS
    )
    assert name.text == "Data!$D$9:$F$13"
    assert root(updated, CACHE).get("invalid") == "1"
    with pytest.raises(ValueError, match="header deletion"):
        NativeWorkbookGrid().update(
            source, request({"axis": "row", "operation": "delete", "at": 8})
        )


def test_local_name_shadows_global_and_global_definition_keeps_global_context():
    source = named_source(
        ("Proxy", "Data!$A$2:$C$5", None),
        ("Proxy", "Data!$D$2:$F$5", 0),
        owner="Data",
    )
    # B deletion affects the global definition's width, not the selected local one.
    updated, _ = NativeWorkbookGrid().update(
        source, request({"axis": "column", "operation": "delete", "at": 2})
    )
    plan = WorkbookPlan(updated)
    resolver = GridSourceResolver(plan, table_states(plan))
    assert resolver.resolve("Proxy", "Data").bounds.text == "C2:E5"
    assert resolver.resolve("Proxy").bounds.text == "A2:B5"


def test_unrelated_named_source_and_external_name_are_not_invalidated():
    source = named_source(("Proxy", "Other!$A$1:$C$5", None))
    updated, _ = NativeWorkbookGrid().update(source, request())
    assert _parts(updated)[CACHE] == _parts(source)[CACHE]
    source = named_source(("Proxy", "'[Other.xlsx]Data'!$A$1:$C$5", None))
    updated, _ = NativeWorkbookGrid().update(source, request())
    assert _parts(updated)[CACHE] == _parts(source)[CACHE]


def test_name_cycles_and_ambiguous_global_relative_coordinates_fail_before_publication():
    source = named_source(("Proxy", "Alias", None), ("Alias", "Proxy", None))
    with pytest.raises(ValueError, match="Cyclic"):
        NativeWorkbookGrid().update(source, request())
    source = named_source(("Proxy", "$A$2:$C$5", None), owner="Data")
    with pytest.raises(ValueError, match="exact worksheet"):
        NativeWorkbookGrid().update(source, request())


def test_scoped_relative_name_uses_its_definition_sheet():
    source = named_source(("Proxy", "$D$2:$F$5", 0), owner="Data")
    updated, _ = NativeWorkbookGrid().update(source, request())
    plan = WorkbookPlan(updated)
    assert (
        GridSourceResolver(plan, table_states(plan))
        .resolve("Proxy", "Data")
        .bounds.text
        == "D3:F6"
    )
