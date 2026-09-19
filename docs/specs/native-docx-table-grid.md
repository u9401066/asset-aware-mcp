# Native DOCX table grid operations

Status: Unreleased, accumulated within 1.4.x; public version remains 1.4.0.

## Purpose and responsibility

Agents need to edit native Word table structure while retaining rich paragraphs,
merged cells, nested tables, evidence and historical bytes. MCP checks explicit
mechanical invariants. Agents review semantics, inherited formatting, actual page
images, repeated headers, nested overflow and pagination, then coordinate corrections.
Package integrity is not a Microsoft Word visual fidelity guarantee.

## Public contract

Discover `docx_table_grid_enabled` and each operation through `contract.for_op`.
`read_docx_table` requires `asset_id`, `revision` and a complete
`docx_table_reference` of existing type `native-docx-block-ref-v1`. The runtime validates
the complete canonical reference against a fresh decomposition. It does not create
cell references or interpret DFM character positions as grid coordinates.

Read every `table.text_excerpt` using `next_text_offset`, verifying the same
`text_sha256`, contiguous character ranges and complete length. The assembled JSON
contains physical cells, grid coverage, omissions, dimensions, merge regions, native
XML, evidence and the full stored `operation_result`. A revision's receipt is the
latest history entry matching those file bytes: an identical file SHA can recur
with a different receipt. Restart paging if the full text hash changes.

`update_docx_table_grid` requires `asset_id`, `expected_revision` and
`docx_table_grid: {reference, edits}`. Edits are sequential, 1–32 per batch, using
zero-based coordinates in each intermediate grid:

- `insert`: `axis`, `index`, `sizes_twips`, optional rectangular `cells` using the
  existing `NativeDocxCell` rich text schema. Insert inside a merge expands it;
  covered/omitted inputs must be default empty cells.
- `delete`: `axis`, `index`, `count`. Retain at least one row and column. If a
  vertical merge survives deletion of its anchor, promote complete anchor content
  into the first surviving physical cell. Deleting its whole region deletes content.
- `resize`: `axis`, `index`, `sizes_twips`. Rows receive minimum heights; columns
  receive fixed grid/cell/table widths, including preferred omitted-position widths.
- `merge`: inclusive `row`, `column`, `end_row`, `end_column`, explicit
  `content_policy`. `require_empty` rejects nonempty other cells; `append_blocks`
  moves whole native child blocks in physical row-major order. Existing merge
  regions must be fully contained. Do not cross the repeated-header/body boundary.
- `split`: merge anchor `row`, `column`. Keep content at the anchor; exposed cells
  become blank. Do not infer a former content distribution.

New rows are not repeated headers. Existing properties and untouched native
content remain. Inserted styles do not promise computed/inherited visual parity.
Twips are twentieths of a point. The grid is bounded to 100 rows by 100 columns;
batch input/component and output budgets are validated before commit.

Mutation responses contain a bounded mechanical summary. Follow `review_request`
to read the complete table and receipt, obtain current references and view every
actual rendered Word page. Combined table and receipt JSON is limited to 16 MiB
UTF-8 before committing. A byte-identical no-op creates no history/receipt entry.

## Scope and atomicity

Current support follows complete table references exposed by the extractor:
body, nested and ordinary unlocked body content controls. Headers/footers and other
unextracted stories are not claimed. Locked/bound ancestors reject changes;
explicit `unlocked` controls are accepted. Structural range/field/revision
dependencies reject grid restructuring; pure resizing retains those dependencies.
Unknown topology/wrappers, legacy horizontal merges and ambiguous vertical
continuations fail explicitly. Omitted positions are distinct from blank cells.

Infrastructure edits a private XML tree, checks each intermediate grid, serializes
and compares the result, restores the original target in a comparison tree to
prove XML outside it is unchanged, and checks exact other package part bytes and
inventory. Application re-extracts the unique current reference and checks complete
reviewability before one repository compare-and-swap commit. Failures leave history
and current bytes unchanged. No media/resource garbage collection is performed.
Sources, old references, derivations and Wiki snapshots never advance implicitly.

## Verification

Unit cases cover rich/nested content, omissions, merge-anchor promotion, guards,
rollback, stale/tampered references, no-op and repeated-byte history, complete long
receipts and budget rejection. SDK 2 stdio exercises real paging and mutations.
`tests.codex_docx_grid.run` uses the user's default Codex model without override;
its independent audit checks complete reads, exact scanned strings, native XML,
history, delivered pixels, source bytes/mtime and complete Wiki attachments.
The synthetic one-page Writer example does not test cross-page repeated headers
or Microsoft Word. Retain initial failures and retries in evaluation evidence.

## References

- [python-docx table grid and omissions](https://python-docx.readthedocs.io/en/latest/user/tables.html)
- [python-docx merge analysis](https://python-docx.readthedocs.io/en/latest/dev/analysis/features/table/cell-merge.html)
- [Open XML vertical merge](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.verticalmerge?view=openxml-3.0.1)
