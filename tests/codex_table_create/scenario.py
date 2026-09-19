"""Independent native workbook creation; scan truth is not supplied in the prompt."""


def prompt(workspace):
    return f"""Use ONLY document(op="native", native_request=...) on
asset_aware_under_test. No shell/browser/files/other servers/subagents/fixture code.
Discover each needed operation with contract.for_op and assemble every schema page.

1. Register {workspace / "source.pdf"}. Read its page listing, VIEW page zero using
render_pdf_page and assemble all read_pdf_page JSON at its exact revision. Transcribe
the visible first-page five-column data table exactly, preserving every character.
2. Use create to make ONE independent workbook called inventory.xlsx with Sheet1.
In that create request put the five visible header strings into A1:E1, and the ten
visible data strings into A2:E3. They are all STRING cells, even when they look
numeric. Put CountLength in F1; leave other cells blank. This is the BASELINE.
Read COMPLETE baseline read_workbook references and full B2 cell evidence at that
explicit revision. Keep the original full B2 reference.
3. Use ONE add_workbook_table at the baseline expected_revision with exact worksheet
key from read_workbook. Create Inventory at A1:F4, header_row=true, autofilter=true,
totals_row=true, header_policy=require_matching. Ordered column names must match
the six actual headers. Set CountLength calculated formula =LEN([@Count]) with
require_matching and totals sum. Set the first column totals label to Reviewed.
Use TableStyleMedium2 with row stripes. Other columns have no calculated or totals
intent. No worksheet rows are inserted and existing scan values must stay unchanged.
4. Read COMPLETE new workbook references and operation_result, including exact
created_table identity and header_cells. Inspect all current Sheet1 A1:F4 cells
and read_cell when necessary. Check exact scan strings, Table/filter bounds, column
IDs, calculated/totals formula text and styles. Read OLD B2 again at baseline
revision and verify the full original reference as historical.
5. Export baseline and current Wikis under {workspace / "native-wiki"}. Publish the
current XLSX to {workspace / "verified.xlsx"}; inspect history. Never modify the
source PDF. Finish ONLY JSON with source_asset_id, table_asset_id and limitations.
Report checks actually performed: formula text and package readback do not prove
calculated results or Excel rendering. Correct actual errors through MCP.
"""
