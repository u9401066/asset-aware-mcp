"""Live rich-cell merge/split exercise after the original scanned-table workflow."""

INSTRUCTIONS = """4m. On the retained first table (after optional grid exercises), discover
    update_pptx_table_grid. Read the COMPLETE current shape before EACH mutation and
    after the final one, assembling all chunks and checking UTF-8 SHA256. Use the
    full current reference and current expected_revision on each call.
    Perform these SIX calls, reading the complete current shape after EACH:
    A. Insert a temporary row at index 4, sizes=[550000], with ONE row of five
       cells ['TEMP','000','+0.00','µg','尾']. Each cell has one paragraph with one
       14-point run; the '000' run is bold, the '+0.00' run italic. This is temporary
       test data, not a claim about the scan. Existing scanned rows stay unchanged.
    B. Merge that whole row with {op:'merge',row:4,column:0,end_row:4,end_column:4,
       content_policy:'append_paragraphs'}. Verify five original paragraphs and
       formatting at the anchor, with empty covered cells; zero/sign/µ are exact.
    C. Split via {op:'split',row:4,column:0}. Verify the five paragraphs stay in
       cell (4,0), the other cells become visible blanks. Do NOT redistribute text.
    D. Delete only temporary row 4 with axis:'row',index:4,count:1.
    E. Split the original title via {op:'split',row:0,column:0}; check the title and
       original scanned data are unchanged in the restored underlying grid.
    F. Merge the title again via {op:'merge',row:0,column:0,end_row:0,end_column:4,
       content_policy:'require_empty'}. Read full final shape, confirming original
       four-by-five grid and exact scanned data. Do not claim full slide rendering.
"""
