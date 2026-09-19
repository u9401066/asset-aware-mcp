"""Totals transitions need safe space, supported cell structure and exact row roles."""

import pytest
from lxml import etree

from src.domain.native_table_create import NativeTableCreate
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_table_create import NativeWorkbookTableCreate
from tests.native_grid_helpers import table_workbook
from tests.unit.test_native_grid_tables import read, table
from tests.unit.test_native_table_totals import SHEET, TABLE, transition
from tests.unit.test_native_workbook_table_edit import column, mutate


def structure(source, feature):
    def change(root):
        if feature == "merge":
            node = etree.SubElement(root, tag("mergeCells"), count="1")
            etree.SubElement(node, tag("mergeCell"), ref="A6:C6")
        elif feature == "filter":
            etree.SubElement(root, tag("autoFilter"), ref="A6:C10")
        elif feature == "protection":
            etree.SubElement(root, tag("sheetProtection"), sheet="1")
        else:
            anchor = root.find(".//s:c[@r='B5']/s:f", NS)
            anchor.set("t", feature)
            anchor.set("ref", "B5:B6")

    return mutate(source, SHEET, change)


@pytest.mark.parametrize(
    "feature", ["merge", "filter", "protection", "shared", "array", "dataTable"]
)
def test_add_rejects_unsupported_geometry_even_when_target_cell_is_blank(feature):
    with pytest.raises(ValueError):
        transition(structure(table_workbook(), feature), "add")


@pytest.mark.parametrize(
    "feature", ["merge", "protection", "shared", "array", "dataTable"]
)
@pytest.mark.parametrize("cells", ["clear", "keep_cells"])
def test_remove_requires_supported_geometry_even_for_retained_cells(feature, cells):
    with pytest.raises(ValueError):
        transition(
            structure(table_workbook(totals=True), feature), "remove", cells=cells
        )


def test_blank_neighboring_table_is_not_implicitly_absorbed():
    source, _ = NativeWorkbookTableCreate().create(
        table_workbook(),
        NativeTableCreate(
            worksheet={"sheet_id": "1", "part": SHEET},
            name="Neighbor",
            ref="A6:C7",
            header_row=False,
            autofilter=False,
            columns=[{"name": name} for name in ("X", "Y", "Z")],
        ),
    )
    with pytest.raises(ValueError, match="another Table"):
        transition(source, "add")


@pytest.mark.parametrize("kind", ["filter", "sort"])
def test_filter_and_sort_geometry_cannot_include_totals(kind):
    def bad(root):
        path = "s:autoFilter" if kind == "filter" else "s:autoFilter/s:sortState"
        root.find(path, NS).set("ref", "A2:C6")

    source = mutate(table_workbook(totals=True), TABLE, bad)
    with pytest.raises(ValueError, match=r"filter|sort"):
        transition(source, "remove", cells="clear")


def test_hidden_custom_definition_reuse_checks_known_columns_after_rename():
    source, _ = transition(
        table_workbook(totals=True),
        "remove",
        cells="clear",
    )

    def custom(root):
        node = root.findall("s:tableColumns/s:tableColumn", NS)[1]
        node.set("totalsRowFunction", "custom")
        etree.SubElement(node, tag("totalsRowFormula")).text = "SUM([Input])+[@Input]"

    source = mutate(source, TABLE, custom)
    restored, _ = transition(source, "add", column(name="Price [net]"))
    assert "Price '[net']" in read(restored, "B6")["value"]
    invalid = mutate(
        source,
        TABLE,
        lambda root: setattr(
            root.find("s:tableColumns/s:tableColumn/s:totalsRowFormula", NS),
            "text",
            "SUM([Unknown])",
        ),
    )
    with pytest.raises(ValueError, match=r"unknown|Unknown"):
        transition(invalid, "add")
    discarded, _ = transition(invalid, "add", reuse_definitions=False)
    assert read(discarded, "B6")["kind"] == "blank"


def test_headerless_table_keeps_data_membership_and_no_filter():
    def headerless(root):
        root.set("headerRowCount", "0")
        root.remove(root.find("s:autoFilter", NS))

    source = mutate(table_workbook(), TABLE, headerless)
    added, _ = transition(source, "add", cell_styles="last_data_row")
    removed, _ = transition(added, "remove", cells="clear")
    assert table(removed).get("ref") == "A2:C5"
    assert table(removed).find("s:autoFilter", NS) is None
    assert read(removed, "A2")["value"] == "Input"


def test_header_only_table_cannot_invent_a_data_style_template():
    def empty(root):
        root.set("ref", "A2:C2")
        auto = root.find("s:autoFilter", NS)
        auto.set("ref", "A2:C2")
        auto.remove(auto.find("s:sortState", NS))

    source = mutate(table_workbook(), TABLE, empty)
    with pytest.raises(ValueError, match="existing data row"):
        transition(source, "add", cell_styles="last_data_row")


def test_last_worksheet_row_cannot_be_extended():
    def at_bottom(root):
        root.set("ref", "A1048575:C1048576")
        root.remove(root.find("s:autoFilter", NS))

    source = mutate(table_workbook(), TABLE, at_bottom)
    with pytest.raises(ValueError, match="boundary"):
        transition(source, "add")


@pytest.mark.parametrize("table_type", ["xml", "queryTable"])
def test_totals_role_change_retains_mapped_source_guards(table_type):
    source = mutate(
        table_workbook(), TABLE, lambda root: root.set("tableType", table_type)
    )
    with pytest.raises(ValueError, match="source field identities"):
        transition(source, "add")
