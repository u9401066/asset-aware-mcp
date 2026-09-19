"""Native/A2T bridge exercised after the scanned-page selection and derivation."""


def table_steps(workspace):
    return f"""5. Discover read_workbook, project_workbook_table, read_table_workspace,
apply_table_workspace and create_workbook_from_table using contract.for_op. Read
the original workbook's COMPLETE read_workbook structure through all offsets.
Project Sheet1 A1:E3 (headers remain data) using its exact worksheet key and revision.
Read the COMPLETE workspace with read_table_workspace, following every offset and
pinning table_sha256 on continuation. Check all native source references and typed
values. Use table_data(operation='update_cell') to change ONLY B at the second
row's stable row_id to {{"kind":"string","value":"008"}}. Read the COMPLETE
updated workspace again and apply_table_workspace with its exact hash and the
original native revision. Do not use native update for this change.
Read the new workbook's COMPLETE read_workbook structure and its current B2 cell.
Read the COMPLETE frozen A2T snapshot using the returned workspace_reference;
verify this file reference. Create an independent XLSX from THAT frozen snapshot
using create_workbook_from_table, same table_id/hash, sheet='Data', include_headers=false,
name='independent.xlsx'. Read its COMPLETE workbook structure and B2; publish it to
{workspace / "independent.xlsx"}. Creation establishes a new workbook layout.
Re-read the OLD selected reference with read_selection, fully, and verify it again:
it must retain the original scanned value and be historical. Do not migrate the
derivation or auto-advance the A2T source binding. Keep table workspace and snapshots.
"""
