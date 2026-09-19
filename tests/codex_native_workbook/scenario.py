"""Extra native workbook lifecycle after the scan/selection workflow."""

WORKSHEET_STEPS = """5b. Extend the SAME workbook through these exact managed revisions.
Discover each operation with contract.for_op first. Before EVERY mutation below,
assemble the complete read_workbook(workbook_view='references') JSON for its current
revision through all next_text_offset pages at one text_sha256. Use returned keys.
- add_worksheets: append two empty worksheets named Review and Temporary.
- update: on Review, set A1 to string 'Current count' and B1 to FORMULA '=Sheet1!B2'.
- rename_worksheet: rename Sheet1 to 資料 O'Brien. Keep its sheetId and part.
- reorder_worksheets: order Review, 資料 O'Brien, Temporary, supplying every key.
- delete_worksheets: delete only Temporary with its exact current key.
After the last mutation, assemble full read_workbook references JSON again. Confirm
Review!B1's explicit formula qualifier now uses the renamed sheet. Read current
資料 O'Brien!B2 and Review!B1 with read_cell. Re-read and verify the OLD B2 selection:
it is historical and still 007. Do not claim formula evaluation or Excel rendering.
Keep all other original literal table cells unchanged. Do not add more revisions.
"""
