"""Native table package fixtures and private grid-stage integration for regressions."""

import io

import xlsxwriter
from lxml import etree

from src.infrastructure.native_grid_cells import shift_cells, shift_columns
from src.infrastructure.native_grid_filters import shift_filters
from src.infrastructure.native_grid_ranges import (
    apply_merges,
    plan_merges,
    shift_ranges,
    update_dimension,
)
from src.infrastructure.native_grid_references import (
    GridReferences,
    clear_formula_caches,
)
from src.infrastructure.native_grid_shared import (
    expand_shared_formulas,
    shift_formula_blocks,
)
from src.infrastructure.native_grid_tables import GridTables
from src.infrastructure.native_grid_views import shift_breaks, shift_views
from src.infrastructure.native_grid_xml import tag
from src.infrastructure.native_ooxml import xml_bytes
from src.infrastructure.native_spreadsheet_reader import NS
from src.infrastructure.native_workbook_plan import WorkbookPlan
from tests.native_workbook_helpers import _parts, _replace


def table_workbook(
    *, totals=False, formula="=[@Input]*2", first="Input", expand_a1=True
):
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        data = book.add_worksheet("Data")
        other = book.add_worksheet("Other")
        money = book.add_format({"num_format": "0.00", "font_color": "#005599"})
        data.add_table(
            "A2:C6" if totals else "A2:C5",
            {
                "name": "Table1",
                "data": [[10, None, "x"], [20, None, "y"], [30, None, "z"]],
                "total_row": totals,
                "columns": [
                    {"header": first, "format": money},
                    {
                        "header": "Calc",
                        "formula": formula,
                        "format": money,
                        "total_function": "sum",
                    },
                    {"header": "Label", "total_string": "Total"},
                ],
            },
        )
        data.set_row(2, 24)
        if formula == "=A3*2" and expand_a1:
            # Explicit independent source formulas: XlsxWriter otherwise copies
            # the exact configured literal to each table row.
            for number in (3, 4, 5):
                data.write_formula(f"B{number}", f"=A{number}*2", money)
        data.set_column("A:C", 18)
        other.write_formula("A1", "=SUM(Table1[[Input]:[Label]])")
        other.write_formula("A2", "=SUM(Table1[Input])")
        book.define_name("AllData", "=Table1[#All]")
    source = output.getvalue()
    root = etree.fromstring(_parts(source)["xl/tables/table1.xml"])
    auto = root.find("s:autoFilter", NS)
    for index in (0, 2):
        col = etree.SubElement(auto, tag("filterColumn"), colId=str(index))
        filters = etree.SubElement(col, tag("filters"))
        etree.SubElement(filters, tag("filter"), val="x" if index else "10")
    sort = etree.SubElement(auto, tag("sortState"), ref="A3:C5")
    etree.SubElement(sort, tag("sortCondition"), ref="A3:A5")
    return _replace(
        source,
        {
            "xl/tables/table1.xml": xml_bytes(root),
            "customXml/unchanged.xml": b"<keep> untouched </keep>",
        },
    )


def apply_table_grid(source, transform):
    """Exercise table stages on real packages; drawings/comments are separate work."""
    plan = WorkbookPlan(source)
    target = plan.book.sheets["Data"]["part"]
    root = plan.roots[target]
    tables = GridTables(plan)
    for part in plan.book.entries:
        sheet = plan.roots[part["key"]["part"]]
        if sheet.tag == tag("worksheet"):
            expand_shared_formulas(sheet)
    shift_formula_blocks(root, transform)
    shift_ranges(root, transform)
    tables.prepare(target, transform)
    merges = plan_merges(root, transform)
    shift_columns(root, transform)
    shift_cells(root, transform)
    apply_merges(root, merges)
    shift_views(root, transform)
    shift_breaks(root, transform)
    shift_filters(root, transform)
    structured = tables.rewrite_references()
    refs = GridReferences(plan.book, plan.roots).rewrite("Data", transform)
    receipts = tables.finish_cells()
    clear_formula_caches(plan.roots)
    update_dimension(root)
    return plan.finish(
        {
            "operation": "grid_table_integration_test",
            "tables": receipts,
            "structured_references": structured,
            "references": refs,
        }
    )
