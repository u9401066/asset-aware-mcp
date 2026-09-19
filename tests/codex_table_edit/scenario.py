"""A supplied rich native Table; scan truth stays outside the model prompt."""

import io

import xlsxwriter

from tests.codex_pdf.fixtures import COLUMNS


def template():
    output = io.BytesIO()
    with xlsxwriter.Workbook(output, {"in_memory": True}) as book:
        sheet = book.add_worksheet("Sheet1")
        other = book.add_worksheet("Summary")
        text = book.add_format({"num_format": "@", "font_color": "#005599"})
        sheet.set_column("A:F", 18)
        sheet.add_table(
            "A1:F4",
            {
                "name": "Inventory",
                "total_row": True,
                "columns": [
                    *[{"header": name, "format": text} for name in COLUMNS],
                    {
                        "header": "CountLength",
                        "formula": "=LEN([@Count])",
                        "total_function": "sum",
                    },
                ],
            },
        )
        sheet.write_rich_string(
            "B1",
            book.add_format({"bold": True}),
            "Co",
            book.add_format({"italic": True}),
            "unt",
            text,
        )
        other.write_formula("A1", "=COUNTA(Inventory[Count])")
        book.define_name("OriginalCount", "=Inventory[Count]")
    return output.getvalue()


def prompt(workspace):
    return f"""Use ONLY document(op="native", native_request=...) on
asset_aware_under_test. No shell/browser/files/other servers/subagents/fixture code.
Discover each needed operation with contract.for_op, assembling every schema page.

1. Register {workspace / "source.pdf"}. Read its page listing, VIEW page zero using
render_pdf_page and assemble all read_pdf_page JSON at its exact revision. Transcribe
the visible first-page five-column data table exactly, preserving every character.
2. Register {workspace / "template.xlsx"}. Read COMPLETE read_workbook references at
its exact revision, following all offsets. This supplied Inventory Table has five
scan columns, a CountLength calculated column, a rich Count header and a totals row.
Fill only A2:E3 in ONE native update using ten STRING values from the scan. This is
the BASELINE revision. Read COMPLETE baseline references, including header_cells,
and full native B1 and B2 cell references at that revision. Preserve both old refs.
3. Use ONE update_workbook_table at the baseline expected_revision with the exact
worksheet key, active table part, expected_ref and current column IDs/expected names
from read_workbook. Rename Count to Quantity, retaining its existing two run formats
with header_runs=["Quan","tity"]. Configure the CountLength calculated formula as
=LEN([@Quantity])+1 using require_matching. Use sum for its totals function and
Reviewed for the first column's existing totals label. Other scan data is unchanged.
New formulas use the final names. Do not use generic cell edits for this step.
4. Read COMPLETE new workbook references and operation_result, including header_cells.
Read all current Sheet1 A1:F4 cells (inspect then read_cell as needed). Check literal
scan strings, unchanged table/filter bounds and column IDs, rich header runs,
calculated/totals formula text, Summary and OriginalCount reference renaming.
Read OLD B1 and B2 again at baseline revision and verify the original full references
as historical. B1 remains Count and B2 retains its exact original scan string.
5. Export baseline and current Wikis under {workspace / "native-wiki"}; publish
current XLSX to {workspace / "verified.xlsx"}; inspect history. Never write back to
the human source. Finish ONLY JSON with source_asset_id, table_asset_id and a
limitations list. Report only checks actually performed: formula text and package
readback do not prove calculated results or Excel rendering. Correct actual errors
through MCP and complete the workflow.
"""
