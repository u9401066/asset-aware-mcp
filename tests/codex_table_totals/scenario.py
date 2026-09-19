"""Extend the independent scan-to-Table workflow with explicit totals transitions."""

from tests.codex_table_create.scenario import prompt as creation_prompt


def prompt(workspace):
    text = creation_prompt(workspace)
    start = text.index("5. Export baseline")
    return (
        text[:start]
        + f"""5. Now use update_workbook_table THREE TIMES, always with
the current expected_revision, exact worksheet key, Table part and expected_ref.
Read COMPLETE workbook references and operation_result after EACH call before
proceeding. Do not supply column edits: this tests hidden totals definition reuse.
First table_update.totals_row={{action:"remove",cells:"clear",retain_definitions:true}}.
Confirm Table A1:F3, filter A1:F3 and blank A4:F4; preserve all data/formula cells.
Second totals_row={{action:"add",reuse_definitions:true,cell_styles:"last_data_row"}}.
Confirm Table A1:F4, restored Reviewed label and CountLength sum formula, unchanged
data, preserved Table style and direct cell styles inherited from row 3.
Third totals_row={{action:"remove",cells:"keep_cells",retain_definitions:true}}.
Confirm Table A1:F3, data unchanged, A4 label retained and F4 formula referencing
the pre-removal data range as absolute Sheet1 coordinates. Inspect full A1:F4 cells.
No worksheet row insertion/deletion: only the explicit Table totals role changes.
6. Read OLD B2 again at the original independent-workbook baseline revision and
verify the exact original reference as historical. Export only baseline and FINAL
Wikis under {workspace / "native-wiki"}. Publish the FINAL XLSX to
{workspace / "verified.xlsx"}; inspect history, expecting five entries in total.
Never modify the source PDF. Finish ONLY JSON with source_asset_id, table_asset_id
and limitations. Report actual checks only: formula text and package readback do
not prove calculated results or Excel rendering. Correct actual errors through MCP.
"""
    )
