"""Live scanned-table exercise covering intermediate native grid revisions."""

INSTRUCTIONS = """4a. On the retained FIRST table, discover update_pptx_table_grid. This uses
    asset_id, expected_revision, pptx_table_grid={reference:FULL current shape ref,
    edits:[...]}. Before EACH mutation and after the final one, read the COMPLETE
    current shape JSON, assemble every chunk and verify its UTF-8 SHA256.
    Perform these FIVE calls in order, reading the complete shape after EACH:
    A. [{op:'insert',axis:'column',index:2,sizes:[300000]}]. Omit cells for blanks.
       Check the merged title expands to six columns and data shift correctly.
    B. Insert one row at index 2, size 400000, cells as ONE row containing
       ['TEMP','000','','+0.00','tmp','N/A']; each entry uses
       {paragraphs:[[{text:VALUE,font_size_pt:14}]]}. This is temporary test data,
       not a claim about the scanned source. Grid is now five rows, six columns.
    C. In one edits batch resize row index 2 to [600000], then column index 2 to
       [450000]. Verify sizes and all values, including the original two data rows.
    D. Delete row index 2 with count 1. Read the complete current table.
    E. Delete column index 2 with count 1. Read the complete current table.
       Confirm original four-by-five grid, title merge and exact scanned strings.
    Preserve failures/recoveries honestly; neither cell hashes nor grid read-back
    establishes full slide rendering. Do not claim a slide-render check.
"""
