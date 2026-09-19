"""Model instructions without access to expected source transcription answers."""

TABLE_GRID_STEPS = """5. Discover project_workbook_table, read_table_workspace and
apply_table_workspace via contract.for_op; assemble complete paged schemas.
Read COMPLETE read_workbook(workbook_view='references') at the original revision.
Project exact Sheet1 A1:E3 using its worksheet key; headers remain data. Read the
COMPLETE workspace through every offset with table_sha256 pinned on continuations.
Keep all original row_ids and column_ids for comparison. Use table_data and
table_manage only to make these A2T edits:
- Change B in the first data row to the STRING 008 using its stable row_id.
- Save the second data row's four A/B/C/D tagged values from the full read. Delete
  that row by its stable ID. Append those same four values as a NEW row, then append
  another row with strings A=Added, B=000, C=0.0, D=mg/L. New rows must have new IDs.
- Remove column E. Add column Review with column_type='native' and typed default
  {"kind":"string","value":"checked"}. It must have a NEW column_id.
- Set Review in the header row to STRING Review. Leave the three data-row Review
  values as STRING checked. The final table has four rows and five columns.
Read the COMPLETE current workspace again. Verify the first two row IDs and first
four column IDs survived, while the deleted row/column IDs were not reused.
Inspect structural_plan: it moves whole worksheet axes; insertion outside a native
table edge would not implicitly extend table membership. This fixture has no native
Excel table object. Read complete current native workbook references again.
Call apply_table_workspace ONCE with the original expected_revision, current exact
expected_table_sha256 and the explicit worksheet_grid from structural_plan. Do not
use native update/update_worksheet_grid as a substitute. Read COMPLETE native
read_workbook references and stored operation receipt at the returned revision;
read current B2. Read the COMPLETE frozen workspace using workspace_reference and
verify that file reference. Keep the live workspace and frozen input.
Re-read the complete OLD selected reference using read_selection and verify it:
it still proves original 007 and is historical. Do not migrate its derivation or
advance the A2T source binding. Added content is a manual edit, not scan evidence.
"""
