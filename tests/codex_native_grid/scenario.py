"""Native grid workflow after scan transcription and historical selection proof."""

GRID_STEPS = """5b. Discover update_worksheet_grid and read_workbook with contract.for_op;
if schema_delivery is paged, assemble all schema pages at the returned schema hash.
Before EACH grid mutation, assemble COMPLETE read_workbook(workbook_view='references')
JSON for its current revision, following all next_text_offset pages at one text hash.
Use Sheet1's exact worksheet key. Make exactly these two grid mutations:
- First update_worksheet_grid: worksheet_grid.edits is row insert at=2 count=1,
  followed by column insert at=3 count=1. Indices address the intermediate grid.
  Use default format inheritance. Do not fill the new blank row or column.
- Read the COMPLETE workbook references/operation receipt and read current B3.
  It must contain the edited count 008. Original headers are now at A1,B1,D1,E1,F1.
  The original data rows are now rows 3 and 4, with column C blank.
- Second update_worksheet_grid: row delete at=2 count=1, followed by column delete
  at=3 count=1. Remove only the blank row/column just created.
- Read the COMPLETE workbook references/operation receipt and current B2 again.
  Verify the OLD B2 selection once more: it still proves original 007 and is historical.
Final table is again A1:E3, with every original literal unchanged except B2=008.
Do not migrate the derivation, use direct update for these grid edits, or add more revisions.
Report actual mechanical checks; Excel rendering and recalculated values are not tested.
"""
