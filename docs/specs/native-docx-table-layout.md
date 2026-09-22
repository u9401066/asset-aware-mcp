# Native Word table pagination

Release scope: **1.4.1**. Use the installed runtime contract and the limits below.

An Agent must be able to correct clipped table text and missing repeated headers
after viewing actual pages. Extend the existing `update_docx_table_grid` batch,
full table reference, source CAS and complete paged receipt workflow. These edits
set explicit native properties; they neither evaluate inherited styles nor certify
rendering. No source or historical evidence changes implicitly.

## Operations

- `set_header_rows`, `count`: set a contiguous prefix of zero to all table rows
  as repeating headers. Clear active header flags outside that prefix. Reject a
  boundary through an existing vertical merge. Noncontiguous declarations read
  from existing files are reported separately from the effective direct prefix.
- `set_row_layout`, `index`, `count`: target an explicit sequential row range.
  At least one of `height` or `split` is required. `height.rule` is `auto`,
  `at_least`, `exact` or `inherit`; only the two sized rules require
  `height.value_twips`. `split` is `allow`, `prevent` or `inherit`. Omitted fields
  retain their current direct properties; `inherit` removes that property so the
  style/default applies. `auto` explicitly requests content-driven height.

New edits share the intermediate coordinates and limits of grid batches. They
can be combined with insert/delete/resize/merge/split. They preserve cell bodies,
merges, table/grid widths, unrelated row properties and other package parts.
Repeated edits that make no XML change retain exact bytes and history.
Receipt before/after state includes the directly changed row properties. Read
complete `review_request` pages at one hash before the next mutation or judgment.

## Mechanical checks and review

Bounds, merge/header boundaries, editable package/source state, relevant tracked
row properties and locked/bound controls are checked before one atomic commit.
Pure layout edits retain field/range content rather than treating them as block
deletions. Structural edits retain their existing dependency checks.

Readback exposes direct height/split properties and header prefix length; it does
not infer computed layout from a style hierarchy. Native inheritance can change
the effect of removing a direct setting. `prevent` requests a row stay on one page
when it fits; oversized rows can still span pages. `exact` can clip content. Agents
must review every page after correction, including repeated headers and all row
contents. LibreOffice previews do not establish Microsoft Word parity.

## Evidence

Regressions must cover explicit/inherited height and splitting, malformed or
multiple declarations, preserved rich/nested content, fields, tracked properties,
locked controls, merged boundaries, rollback and no-op receipts. An actual Writer
multi-page case must expose clipped text before correction, complete content and
repeated headers afterward, compare real SDK2 PNGs with independent rendering,
and retain old evidence/source bytes/Wiki snapshots. Actual default Codex must
inspect initial/final pages and full records without model override. Record first
errors/retries instead of replacing their evidence with a clean run.

References: [TableHeader](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.tableheader?view=openxml-3.0.1),
[CantSplit](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.cantsplit?view=openxml-3.0.1),
[TableRowHeight](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.tablerowheight?view=openxml-3.0.1),
[python-docx table XML](https://github.com/python-openxml/python-docx/blob/master/src/docx/oxml/table.py).
