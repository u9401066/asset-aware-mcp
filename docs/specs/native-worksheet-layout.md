# Native worksheet layout correction

Release scope: **1.4.1**. Use the installed runtime contract and the limits below.

The Agent reads an immutable workbook rendition, identifies clipped text, reads
native dimensions, chooses explicit corrections and renders a new revision. MCP
checks native structure and exact preservation; it does not infer auto-fit sizes
or claim visual/semantic correctness.

`read_worksheet_layout` requires asset_id, revision and worksheet_key. It returns
complete hash-pinned paginated JSON: sheet defaults, explicit row attributes,
column intervals, worksheet protection and the current operation receipt.
`update_worksheet_layout` requires expected_revision and worksheet_layout with
an exact worksheet key and 1..32 sequential edits. Each edit targets row/column,
one-based at/count (up to 1024 positions), explicit height_points or width_ooxml,
reset_size and/or hidden. Width is the raw OOXML width, including digit-font
padding; it is not Excel's displayed character count. Reset removes the manual
size and its flags. It does not calculate text-dependent automatic row heights.
No cells, ranges, formulas or source evidence move to different coordinates.

Preserve all cell payloads/styles except invalidated formula caches, unrelated
row/column attributes, merged ranges, Tables, media, comments and untouched ZIP
members. Split column intervals without losing attributes or foreign extensions.
Reject ambiguous overlapping intervals and malformed dimensions before mutation.
Use existing workbook edit guards and reject unmodeled worksheet object geometry.
Sheet protection must explicitly permit formatting the edited axes; never unlock
or remove protection. Existing workbook-level guards remain conservative.

Object geometry respects authored DrawingML editAs and VML move/size policies.
An identity coordinate transform uses before/after grid dimensions; absolute
objects retain geometry, one-cell objects retain size, two-cell objects follow
the grid. Explicit collapse policy defaults to reject. Metric calibration follows
the existing grid workflow; nondefault Normal fonts need caller measurements.
Store full before/after dimension and geometry receipts. Invalidate formula and
chart caches because CELL width and hidden-row-sensitive formulas can change;
request full recalculation. Agent checks actual renderer output and formula results.

A private package patch is read back before a single revision CAS. Serialized
layout and preserved cell content must match. Bound the complete public review
record before committing. Historical workbooks, PDFs, citations, source bytes and
source mtime stay unchanged. New renditions receive independent PDF identities.

Validation: interval splitting/reset/hidden/defaults; malformed and protected
inputs; rich cells/styles/merges/opaque parts; DrawingML/VML anchor policies and
font metrics; rollback, stale revisions, full read-back hash and historical refs;
real Calc SDK2 and actual default-model Codex correcting observed clipped titles.

Primary references:
- https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.column?view=openxml-3.0.1
- https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.row?view=openxml-3.0.1
- https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.sheetprotection?view=openxml-3.0.1
- https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.spreadsheet.twocellanchor?view=openxml-3.0.1
