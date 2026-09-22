# Asset-Aware MCP: Agent Document Collaboration Specification

Native Table creation: see [the operation contract](specs/native-table-creation.md).

<a id="retained-raster-evidence-unreleased-14x"></a>

### Retained raster evidence (1.4.1)

Persist complete source-bound frame records and catalogs when read, and exact
bounded PNG previews when generated. Full historical references resolve these
immutable representations after a decoder change; never remove decoder identity
from hashes or silently replace old records. Verify source bytes and retained
representation integrity separately from current-decoder reproduction and Agent
semantic/visual review. A retained preview is available only for its exact full
reference, render size and color policy. An uncaptured preview requires the current
decoder to reproduce the referenced frame; otherwise report it unavailable.
Allow read_image/export_wiki to pin image_catalog_sha256 and read_image_frame to
pin its complete reference in addition to asset/revision/locator. New unpinned
reads use the current decoder. Mutation preconditions remain current-decoder
checks. Historical catalogs/previews and direct input references must also work in
native and cross-format Wikis after restart. Partial/corrupt archives fail closed.

## Agent document collaboration contract (2026-09-18)

The goal is native cross-format document CRUD: create, read, decompose, update,
write back and delete documents/components, preserving features outside the edit.
Standalone table creation is first-class. Markdown and wikilinks are projections,
not universal storage or substitutes for the editable source.

An asset is an addressable, versioned unit an agent can inspect, reuse or operate
on. Source files are root assets; paragraphs, cells, worksheets, slides, pictures,
charts and embedded objects are children. Each carries identity, source revision,
a native locator, typed representations, relationships, operation capabilities,
preservation constraints and validation state. New agent-created assets record a
creation origin without requiring a PDF. Inferred meaning is separate from source.

Human handoff: register original identity → inspect native format/features →
expose structure/previews/capabilities → stage scoped edits → necessary checks →
agent review/correction → revision-checked atomic commit → optionally project selected assets
into a wikilink evidence library. Source files and curated notes retain ownership.
Deleting a projection does not mean deleting the original document.

### Necessary MCP checks and agent verification

MCP owns source/version preconditions, staged writes, format-preservation guards,
structural checks and inspectable before/after operation results. Supported writes
must fail on stale sources or failed integrity checks and publish atomically.
It exposes locators, diffs, warnings and available previews for agent inspection.
The agent owns complete semantic and visual verification, decides corrections and
coordinates subsequent tool calls. MCP rechecks each resulting operation.
Deterministic repair is appropriate only for explicitly supported mechanical rules;
it is not a promise of complete automatic correction or layout verification.
Verification coverage and unperformed checks must remain explicit. Structural
validity alone must never be reported as semantic correctness or full fidelity.

<a id="native-worksheet-grid-transformations-in-progress-unreleased-14x"></a>

### Native worksheet grid transformations (1.4.1)

Extend native workbook collaboration with sequential row/column insertion and
deletion at an exact worksheet key and expected revision. Operate on the original
OOXML package, retaining surviving cell XML, rich text, number formats, row heights,
column widths, hidden/outline metadata and unrelated parts. New blank rows/columns
use an explicit before/after/none format inheritance policy. Coordinates are
one-based and each operation uses the grid resulting from prior operations.

The operation must transform explicit A1 references across local/cross-sheet
formulas, scoped names, chart series, validation, conditional formatting and
hyperlinks, including absolute/mixed references, whole rows/columns and range
shrinkage. Preserve formula whitespace, strings, external-workbook references and
unaffected names. Deleted direct references become explicit #REF! and are reported;
this is not formula evaluation. Expand shared formulas before relocation; reject
partial array/data-table edits and ambiguous 3D/reference contexts instead of
inventing semantics. Historical cell/selection references remain revision-local.

Move/resize merged ranges and retain surviving cell formatting. If deleting only
the merged anchor, use an explicit preserve/delete content policy; preserving must
retain the complete cell payload without overwriting conflicting surviving data.
Update table/filter/sort ranges and column identities, comments and drawing/VML
anchors, view/selection/freeze locations, breaks, print areas and worksheet bounds.
Respect move/resize behavior; geometric reconstruction must use known or explicitly
supplied column digit metrics instead of guessing non-default font widths. Keep
unmodeled or protected structures unchanged by rejecting unsupported transformations.

Return a complete operation receipt with coordinate transforms, removed content
counts, moved anchors, reference repairs and required Agent review. Reparse the
serialized workbook, verify cell/mapping/format invariants and unchanged part bytes,
repair stale derived counts/caches and request recalculation. Source publication
remains explicit. Extend A2T correspondence using these operations without silently
reinterpreting stable row IDs or moving old semantic assertions. Verify rich real
packages, boundary/overflow/merge/reference cases, SDK2 and actual Codex scanned
PDF→native→A2T→structurally edited native workflows. This section records the intended
implementation; it does not mark native grid/A2T structural fidelity complete.

Primary references: [openpyxl dependency boundary](https://openpyxl.readthedocs.io/en/stable/editing_worksheets.html),
[OOXML column metrics](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.column),
and [XlsxWriter object placement](https://xlsxwriter.readthedocs.io/working_with_object_positioning.html).
Formula materialization follows the [Open XML shared/array/data-table rules](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.cellformula):
nonshared overrides inside a shared rectangle remain independent, while a shared
follower's own text does not override its master. Rebase validation/conditional
formulas when their first application cell is deleted, before rewriting coordinates.
Array/data-table result cells are stale caches even when only the master stores a
formula node. Preserve [escaped structured column names](https://support.microsoft.com/en-us/excel/using-structured-references-with-excel-tables)
as literal headers; both endpoints of structured ranges must participate in known
dependency checks. Frozen pane counts differ from split positions in points, and
page break coordinates are zero-based. These internal helpers do not advertise a
public operation until package orchestration and the complete workflow are tested.

Table columns retain their native numeric IDs across grid edits. Structured column
references resolve names against those IDs, including local row selectors, escaped
headers, column intervals and explicit worksheet/external qualifiers. A deleted
single-column reference becomes #REF!; a column interval shrinks to its surviving
endpoints. References to a removed table become #REF!. Do not silently bind a lost
column to a newly inserted column with the same name. Keep unaffected formula
spelling. New table columns receive unique IDs and deterministic unique headers;
table/header/formula changes must participate in the same private package plan.
Deleting a table's header row hides that header while retaining column names and
all surviving data; it does not overwrite the next data row with generated labels.
Deleting its totals row disables the totals row and removes the corresponding
totals definitions. Inserted data rows receive the table's calculated-column
formulas at their new coordinates; inserted columns receive empty data and unique
headers. Implicit selectors require an unambiguous table context.

Drawing geometry uses 96-DPI pixel/EMU metrics with recorded font/default-width
assumptions or explicit caller-supplied calibration. Preserve fixed-position
objects' absolute placement, moving-only objects' extent, and moving/resizing
objects' transformed endpoints. A deleted interval that collapses an object uses
an explicit preserve-size/reject policy, rather than silently making its content
invisible. VML offsets are pixel values; comments retain their text/author payload
while cell locators and display anchors move together. Whole deleted comment cells
remove their corresponding note shapes. Dynamic auto-height, renderer font metrics
and final appearance still require Agent review.

The private package adapter now combines these stages for sequential edits and
checks surviving cell payloads/styles before any merge promotion or generated
table cells. After serialization it reparses every planned XML part, table column
identity/range/relationship and unchanged package member. Cell comparison uses
exclusive canonical XML so inherited unused namespace declarations do not cause
false payload differences. Whole-package XML readback remains exact.

DrawingML supports two-cell, one-cell and fixed anchors, keeping corresponding
top-level transforms consistent and retaining intentionally zero chart transforms.
Legacy note text/authors, cell locators, pixel anchors and point-valued display
styles participate in the same private plan. Empty note parts remain valid after
deleting all note cells; original source/history bytes are retained. See the
[Microsoft VML anchor definition](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.vml.spreadsheet.anchor).
Worksheet outline summaries and cell watches are repaired. Whole pivot result
rectangles may move; partial edits require coordinated pivot-field handling.
Direct named-table pivot sources invalidate caches on row changes and reject
unmapped column changes. External same-name sources retain their own grid.
Chart reference caches are invalidated even when table expansion leaves their
formula text unchanged. This does not calculate new chart or formula results.

The development operation is `update_worksheet_grid`, taking `asset_id`,
`expected_revision` and `worksheet_grid` (exact worksheet key, sequential edits and
optional dimension calibration). It requires configured grid and workbook-readback
adapters, stages an immutable managed revision with compare-and-swap, and returns
a revision-pinned `read_workbook` review request for the complete operation receipt.
Source writeback stays explicit. The contract advertises `workbook_grid_enabled`
only when configured. SDK2 and actual Codex cover direct grid editing and the A2T
insertion/deletion bridge below. Broader table/move fidelity remains open;
this operation is included in 1.4.1.

Named pivot/consolidation sources must resolve worksheet-scoped and workbook-scoped
name chains, exact A1 rectangles and explicit table selectors against each current
grid. Keep scope precedence and external workbook identity. Compare source ranges
before/after each edit; pivot fields require the same column schema and surviving
header. Cyclic names, ambiguous scopes and formulas requiring evaluation must fail
with an explicit dependency error rather than retain stale field identities.

<a id="native-workbooka2t-correspondence-unreleased-14x"></a>

### Native workbook/A2T correspondence (1.4.1)

Expose project_workbook_table, read_table_workspace, apply_table_workspace and
create_workbook_from_table through native_request. Projection requires an exact
asset/revision, worksheet sheetId/part and bounded rectangular A1 range. Every row
including any header remains data; column labels use native column letters. Never
infer numeric strings, formulas, headers or dates. Tagged scalar cells distinguish
literal strings, booleans, numbers, formulas and blanks; preserve read-only source
representations when no supported editor exists. Existing ordinary A2T tables remain
compatible and can create independent native XLSX workbooks with explicit options.

A durable native binding pins source revision/range and stable A2T row/column
correspondence. Complete workspace JSON includes current values and complete native
source-cell references/representations; page at one table_sha256. Imported style/raw
numeric/formula metadata remains in the original immutable file and read-back, not
flattened into Markdown. The binding describes extraction origin, not semantic
support for later edited values. Existing PDF-style CellCitation remains separate.

Applying uses a copied table snapshot with expected_table_sha256 plus the exact bound
workbook expected_revision. Reconstruct source records and compare tagged values;
unchanged native cells are never rewritten. Apply only typed changed cells through
the checked original-package adapter, preserving styles and all untouched parts.
Changed correspondence requires an explicit worksheet_grid plan as described below.
Reject unsupported edits, stale bindings, archives and malformed type payloads
before native commit. The operation result records the
applied snapshot hash and table/source identity. Before committing a native update
or independent creation, retain canonical A2T JSON as a managed immutable file with
format `a2t`, media type `application/vnd.asset-aware.a2t+json`, and a full
`workspace_reference`. Read this reference after the mutable table changes or is
deleted; `verify` checks exact file bytes. A late workbook CAS failure may retain an
unreferenced input snapshot while leaving the target revision unchanged. No-op
application creates neither snapshot nor revision. It does not mutate the A2T binding or
advance assertions: re-project the new native revision for subsequent synchronized
work. Source publication/writeback remains an explicit existing operation.

Independent creation from A2T handles the current rows/columns, including structural
A2T edits, using explicit destination filename/sheet/header choices. It creates a new
native asset and returns the mapping; it is not a format-preserving source writeback.
Applying insertion/deletion to existing workbooks uses the native grid/reference/
merge/style adapter through the explicit identity plan below. Agent
reviews meaning, dynamic references, formula results and rendered layout. Regressions,
SDK2 and actual Codex must verify literal scan data, typed edits, original bytes,
source and table preconditions, complete readback and persistent historical evidence.

<a id="structural-a2t-application-unreleased-14x"></a>

### Structural A2T application (1.4.1)

New TableContext instances carry stable column_ids as well as row_ids. Rename keeps
column identity; new appended rows and columns receive fresh IDs, including after
deletion of an identical value/name. Persistence retains these IDs. Historical A2T
snapshots without column IDs keep their canonical representation; compatible mutable
legacy schemas can acquire an explicit binding before a schema edit. Ambiguous
previous schema history cannot be silently mapped. Missing legacy creation dates
remain unknown instead of changing the workspace hash with each fresh read.

When table_grid_apply_enabled, complete read_table_workspace exposes structural_plan.
Its deterministic insert/delete proposal follows stable identity order and records
the destination. Caller explicitly supplies worksheet_grid to apply_table_workspace;
MCP checks the exact worksheet, surviving IDs and new slots, bounding every edit to
the changing projection. Whole worksheet axes move, so content outside the projection
also relocates. Plans discard deleted merged anchors. Reordering surviving identities
requires a native move operation, not reconstruction with fabricated old identities.

Read exact original records, apply the checked native grid to memory, then apply only
new or changed typed values. Unchanged formulas/rich text follow the native relocation;
new/edited formulas address the destination. Missing new values are blank. Read every
destination value back and compare unedited representations/styles, retain the frozen
A2T input and commit once under the original file CAS. Old evidence remains historical.
Native Table edge insertion requires explicit expand_tables to extend membership; table headers,
calculated columns and partial array structures retain their dedicated edit boundaries.
No structural preview claims semantic, recalculation or visual completeness.

<a id="native-table-column-edits-unreleased-14x"></a>

### Native Table column edits (1.4.1)

`update_workbook_table` selects one exact worksheet key, active Table part and
`expected_ref`, with the normal file `expected_revision`. Each column edit uses
its current numeric `column_id` and `expected_name`. A request changes metadata
and worksheet cells in one private package plan and one repository CAS.

- `name` renames the column and header together. Existing formulas, defined names
  and modeled structured references follow the original column identity. Supplied
  new formulas use the final names. Rich headers require explicit `header_runs`
  matching the existing runs and concatenating to the new name. Complete
  `read_workbook.tables[].header_cells` exposes original cell/resolved shared-string
  XML for this inspection without changing historical read_cell representations. Retain run formats
  and clone shared strings so other cells are unaffected.
- `calculated` sets a scalar formula anchored at the first data row. Its policy
  `require_matching` accepts blank cells or formulas matching the previous column
  formula; exceptions reject. `replace_all` explicitly replaces ordinary data
  values/formulas. Formula removal uses null plus `keep_cells`, retaining cell
  contents while removing future automatic-fill metadata.
- `totals` edits an existing totals row: blank, literal label, scalar formula or
  an explicit supported SUBTOTAL function. It never inserts or consumes a data
  row implicitly. Bounds/filters/column IDs and existing styles remain intact.
- Preserve generic cell guards. Protected, merged, metadata-bearing, array/shared
  formula and unsupported rich/phonetic edits require their own workflows. Mapped
  or query schemas are not silently renamed; pivot source header changes need
  coordinated field identities and therefore reject. Invalidate affected caches,
  request recalculation, and expose the complete receipt and reference readback.

MCP checks exact package/cell readback and untouched parts. Before commit it also
checks the complete public reference inventory plus receipt fits the 16 MiB read
budget; separate component budgets do not prove a readable combined result.
Receipt cell `before` values come from the original revision, even when existing
formulas were renamed during a private intermediate stage before formula edits.
Agent checks meaning,
rendered headers, filter visibility, formula results and totals semantics. Old
evidence and A2T bindings stay revision-scoped.
Primary references: [SpreadsheetML tableColumn](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.spreadsheet.tablecolumn)
and [XlsxWriter tables](https://xlsxwriter.readthedocs.io/working_with_tables.html).

<a id="explicit-native-table-expansion-unreleased-14x"></a>

### Explicit native Table expansion (1.4.1)

read_workbook.tables exposes worksheet/part identity, attributes, column IDs, raw
part SHA-256 and complete parsed XML even for non-UTF-8 source definitions.
Each insert edit may supply expand_tables with exact table part and expected_ref
in that intermediate worksheet grid. Row insertion at the first/last data boundary
or column insertion at the left/right boundary can explicitly include new cells.
Insert before totals to extend data; insertion after totals cannot move the totals
meaning implicitly. No expansion is inferred for adjacent tables. Existing IDs,
column metadata, styles and structured references survive; new columns get fresh
IDs and unique headers. Extend table-owned filters/sort ranges consistently, retain
criteria and record generated headers/calculated formulas. Query/XML-mapped and
pivot source schema changes still require coordinated mapping.

A2T native_generated with null value explicitly preserves only a header/calculated
cell generated during this structural operation. Replay all grid steps to track its
final position. Reject placeholders on ordinary/surviving cells and nonstructural
exports; missing/blank remain blank. Freeze the input intent, record resolved values,
verify the native result and commit once. This does not certify recalculated results,
filter visibility, sorting or rendered layout; Agent completes those reviews.

Reference designs: [Microsoft SpreadsheetML tables](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-tables)
and [XlsxWriter tables](https://xlsxwriter.readthedocs.io/working_with_tables.html).
Table definitions and sheet cells are distinct package parts; both must agree.

<a id="native-workbook-sheet-structure-unreleased-14x"></a>

### Native workbook sheet structure (1.4.1)

Provide revision-pinned read_workbook structure/reference inventories and managed
add_worksheets, rename_worksheet, reorder_worksheets and delete_worksheets. Keys use
exact sheetId/part identity; rename retains both. Reorder supplies every current key
exactly once; deletion cannot remove the last visible worksheet. Add empty native
worksheets, then reuse typed cell edits. Preserve all existing worksheet/media/style/
comment/custom-part bytes outside explicit reference or view repairs; retain detached
deleted-sheet parts and state that deletion is not secure erasure.

Patch the original OOXML package rather than resaving through an object model.
Update workbook relationships/content types, scoped defined-name indices, active
view indices and known reference fields. Use lossless formula token spans to rewrite
explicit local sheet qualifiers across formulas, names, charts, validation and
conditional formatting. Preserve external-workbook references and string literals;
INDIRECT/HYPERLINK string semantics and calculated values require Agent review.
Use openpyxl's tokenizer only, retaining original whitespace and syntax outside edits.
Detect unsupported syntax and ambiguous identities instead of silently guessing.

Reject deletion with surviving explicit sheet/table/pivot/consolidation references. For insertion
and reordering, preserve the membership of 3D references by default; allow an explicit
allow_3d_membership_change policy with reported counts and Agent formula review.
Remap localSheetId and workbook view indices to retained sheet identity. Request
recalculation, detach stale calc-chain relationships while retaining their original
parts, and clear optional stale extended-property sheet-title caches. Reject signed/protected or opaque
macro/revision structures that need a dedicated workflow. Read operations remain
available independently of mutation eligibility. Bound member/formula/output budgets.

Test rich workbooks with formulas, chart series, tables, merges, comments, protected
unmodified sheets and custom XML; verify exact unaffected bytes and independent
openpyxl readback. Include quoted/Unicode names, external refs, dynamic/spill syntax,
3D membership, defined names, hidden views, relocated parts, stale/archived/history
references and delete dependencies. Exercise real SDK2 and actual Codex scan-to-XLSX
sheet lifecycle, selection/history/Wiki and source preservation. Full publication
gates and docs/harness sync remain required; no automatic version bump/tag.

<a id="native-selection-evidence-unreleased-14x"></a>

### Native selection evidence (1.4.1)

Add read_selection over full verified native cell/block/shape/page references.
Use RFC6901 JSON-string pointers (no URI-fragment decoding), zero-based array
indices without leading zeros and exact Unicode keys without normalization. Empty
pointer reads the complete parent record without added evidence metadata. Optional character ranges are nonempty,
zero-based and half-open over a selected string; report its UTF-8 byte range,
source text hash and nearby context. These offsets address parsed values, not
original package bytes or PDF geometry. Opaque file references have no parsed
selection; nested selection parents are unsupported.

Bind parent identity, selector, context and selected JSON value in canonical UTF-8
SHA256. Return immutable native-selection-ref-v1 plus complete hash-pinned paged
JSON. Re-reading an existing selection ref must verify its full identity; false,
zero, null and empty strings are valid selected values. Limit pointer length/depth
and selection bytes; reject missing keys, wrong types and out-of-range spans.

Existing verify, derivation recording/supersession/retraction and wiki workflows
accept selection endpoints. Preserve old reference/ledger serialization and history.
Selection evidence is revision-local; edits never migrate it automatically. Export
complete deduplicated selected-record artifacts and exact source attachments for
active assertions at the exported revision. Immutable checks do not infer semantic
support, OCR, native-cell equivalence or visual fidelity. Native rendering and Agent
review remain necessary. Test every supported parent format, locator/hash tampering,
equal-value wrong paths, Unicode codepoints, merged/changed tables, complete paging,
portable wiki evidence and actual Codex use against scanned source plus native table.

<a id="cjk-preview-environment-correction-unreleased-14x"></a>

### CJK preview environment correction (1.4.1)

Provide an opt-in, private Linux Fontconfig evaluation fixture with exact upstream
Noto font hashes, original font licenses and hashes of copied local Latin fonts.
Do not modify global font configuration, source DOCX bytes or requested run fonts.
Forward the explicit environment to both actual Codex MCP and independent replay;
record configuration/font identities and reject changed fixtures before reuse.
Compare before/after rendering of identical DOCX bytes and require expected CJK
text/font evidence as a mechanical check, alongside actual Agent image review.
Nonzero glyph IDs or extracted Unicode alone do not certify correct appearance.
Ordinary tests never download fonts or start a model. Document this bounded Linux
fixture without claiming Microsoft Word fidelity or universal script coverage.

<a id="native-docx-page-previews-unreleased-14x"></a>

### Native DOCX page previews (1.4.1)

`render_docx_page` requires an asset ID, explicit immutable revision and zero-based
`docx_page_index`. A separate renderer port returns an actual MCP PNG, image hash,
rendered PDF hash, page dimensions/count, renderer/version and review limitations.
Page identity belongs to this rendered revision/environment, not to native block
locators or a promise of Microsoft Word pagination. Agents can start at index0,
then inspect every page through the returned count/next_page_index.

The optional LibreOffice Writer adapter receives an untouched temporary copy of
the stored DOCX bytes, never a DFM reconstruction. Export the entire document with
blank pages retained and form fields as their static print representation. Verify
actual bounded PDF output and unchanged temporary source; use isolated native PDF
workers for page inspection and PNG rendering. Preserve time/output/process-group
limits and private profiles with macros disabled; this is not an OS sandbox.
Reject known external resource relationships, include/DDE/database fields,
alternative chunks, linked VML resources, SVG and embedded OLE packages before
starting Writer. Ordinary hyperlinks, internal images, tables, headers/footers,
sections and common display fields remain within the preview workflow.

Require a valid rendered page index; up to 2,000 pages, 64 MiB PDF and 64..2048 px previews.
No managed/source revision changes occur. Report installed-font/viewer differences,
recalculated fields, annotations/revisions and dynamic-content limitations. A PNG
is review evidence, never an automated semantic or visual-fidelity verdict.
Test real SDK2 images across multiple pages and historical revisions, page bounds,
resource guards, unavailable Writer/missing output, source integrity and actual
Codex scan-to-DOCX visual review with independent pixel comparison.

<a id="native-docx-creation-and-body-structure-unreleased-14x"></a>

### Native DOCX creation and body structure (1.4.1)

Provide create_docx from typed rich paragraphs and rectangular/merged tables, with
explicit page dimensions/margins and literal display strings. No precursor PDF or
DFM source is required. Save into managed identity/history; publication/writeback
remain separate. New content must retain its requested text, direct formatting,
grid widths and merge structure after independent native readback.

add_docx_blocks inserts typed blocks at body start/end or before/after a full current
DOCX block reference. delete_docx_blocks deletes exact referenced top-level body
paragraphs/tables. Check source/revision/CAS, complete reference hashes and native
locator metadata before mutation. Resolve original body-child positions, not offsets
in a flattened text view. Reject partial multi-block paragraphs, protected/signed
sources, ambiguous body/section structure and deletions affecting range/section/
field dependencies. Historical references remain valid; new block IDs are revision
scoped. Retain orphan media/relations; deletion does not promise secure erasure.

Generate only new XML in a scratch document. Patch the original main part without
resaving its other parts through python-docx; independently verify exact untouched
body subtrees, source package inventory and unrelated part bytes. Enforce aggregate
block/cell/run/text budgets and reject invalid XML characters or overlapping merges.
Existing nested structures remain intact outside an explicit selected deletion.
MCP checks source/package/representation integrity; Agent checks semantics, page
flow, inherited styles, rendered layout and updated Word fields/viewer caches.

<a id="native-whole-slide-previews-unreleased-14x"></a>

### Native whole-slide previews (1.4.1)

`render_pptx_slide` requires an asset ID, explicit immutable revision and exact
`pptx_slide_key={slide_id,part}`. A separately injected rendering port returns a
static PNG plus source identity, image hash, renderer/version, source slide index
and limitations. MCP never converts a preview into a visual-verification verdict.

The optional LibreOffice Impress adapter exports a temporary full-deck copy with
hidden slides included and notes pages excluded, then checks PDF page count and
uses isolated native PDF workers to render the requested slide. Full-deck export
preserves slide-number context. It checks both the conversion exit and actual PDF;
an installed `soffice` without Impress is insufficient. Private profiles disable
macros; process timeout cleanup includes descendants. This is not an OS sandbox.
Package, slide-count (100), PDF-byte and image-size limits apply. External linked
content, SVG media and alternative show selections require additional workflows.
Ordinary hyperlinks remain supported. Fonts, static media, animation and viewer
differences remain Agent review concerns. Managed/source files are never modified.

The contract distinguishes adapter configuration from per-request availability;
the default package/container does not gain a mandatory office installation.
Regression coverage must include missing output despite exit zero, hidden slides,
reordered raw part identity, historical revisions, subprocess timeout cleanup,
actual SDK2 image delivery and optional real Impress conversion.

### Citation presentation contract

Canonical identity, revision, locator and exact quote/hash are independent from
human citation style. A versioned declarative contract defines inline/reference
templates and required metadata, supporting source labels, author/year,
caller-assigned numeric references and custom organizational formats. Templates
are not full APA/Chicago/CSL implementations; standards-aware rendering remains
in scope. Missing metadata must be reported, never invented.

Allow only named scalar placeholders, no code/attribute/format expressions.
Metadata cannot replace canonical IDs, hashes or locators. Export the contract
and its hash alongside notes/bundles. Style changes preserve evidence identities
and wikilink targets. Locator validity, extraction accuracy and semantic support
are distinct concepts.

<a id="canonical-a2t-citation-readback-14x-development"></a>

### Canonical A2T citation readback (1.4.1)

Keep table_cite get as the compatible cell/row/table summary. Add read for one
cell selected by table_id, column_name and row_id (preferred) or row_index.
Return the full persisted CellCitation, including every AssetRef locator, exact
quote/hash, CRAAP metadata, notes and confidence, alongside the current cell value
and stable table/row/column binding. A missing citation is explicit null. Unknown
rows/columns are errors. Do not invent missing source locators or quality scores.

Serialize the a2t-cell-citation-v1 record as sorted compact UTF-8 JSON, preserving
Unicode exactly. The SHA-256 binds the value, citation and cell identity, excluding
the mutable row index. The a2t-citation-page-v1 envelope carries citation_sha256,
text_excerpt, total character length, half-open character range and next offset.
text_limit is 1..4000 (default 4000); the encoded envelope must fit the configured
MCP response cap. Reject a cap too small for any progress. Bound each complete
representation to 16 MiB UTF-8 and reject unsupported non-JSON/non-finite values.
For text_offset > 0, require citation_sha256 from the first page; reject mismatched
hashes, out-of-range offsets or a different cell. Agents concatenate all excerpts
at one hash, verify UTF-8 SHA-256, then parse the complete JSON. Partial excerpts
are transport fragments, never shortened canonical AssetRefs.

Reads do not change table/source artifacts. Hash equality proves consistent stored
content, not source validity, authenticity, extraction accuracy or semantic support.
Source verification and rendered/semantic review remain separate. Tests must cover
long/multiple refs, Unicode/control characters, small response caps, stale paging,
row deletion/reindexing, nonexistent addresses, absent citations and unchanged
artifacts. Real SDK2 and opt-in Codex PDF workflows must read every final Reading
cell's references through MCP, with independent audit of returned locators/content.

### Starting coverage and completion evidence

A2T operation results identify the resolved stable row and index, including the
pre-deletion index for deleted rows. A row_id takes precedence over an input index;
never display the unused -1/default or a conflicting input index as the operated
target. Cell-history labels use the validated stable row ID when supplied. This
changes result metadata/presentation only; row identity, data, citation invalidation
and history semantics remain unchanged. Regress after deleting an earlier row.

<a id="native-pptx-shape-structure-14x-development"></a>

### Native PPTX shape structure (1.4.1)

Add add_pptx_shapes and delete_pptx_shapes under document/native, preserving the
existing native-contract-v2 discovery flow. Both require asset_id and expected_revision,
stage managed revisions through CAS, and never implicitly write the human source.

add_pptx_shapes accepts up to 100 typed textbox additions. Each supplies a container
(slide_id, part, region, optional group_shape_id) and the existing textbox model
(local EMU geometry, explicit paragraphs/runs/styles). Resolve the container through
the presentation relationships, allocate unused unsigned 32-bit shape IDs in its
part, and append shapes at the top of z-order before extLst. Generate only the new
textbox XML using python-pptx's public API; do not round-trip the existing package
through that library. Preserve group transforms without automatically resizing or
repositioning existing children. Bound aggregate additions to 20,000 runs / 4 MiB
UTF-8 text. Return generated locators for reading and subsequent edits.

delete_pptx_shapes accepts up to 100 existing NativePptxReference objects. Require
matching asset/revision and exact full representation hashes. Reject duplicates
and overlapping ancestor/descendant requests. A group deletion includes its subtree.
Reject removal when remaining known connector, timing or build references target
removed shape IDs; deleting a dependent connector in the same batch is allowed.
Shape deletion retains package relationships and related media/embedding parts;
it is not secure content erasure. Slide creation/removal, non-text shape creation,
animation editing and interpretation of arbitrary extension dependencies remain
separate capabilities, not implied by these operations.

For either operation, validate package inventory and untouched member bytes,
read back the intended structural change, and reverse only the planned shape
changes in an independent parsed result to compare all other XML canonically.
Preserve existing immutable references/wiki snapshots and their exact old hashes.
Reject stale, signed/protected, strict/macro/legacy, ambiguous or invalid packages.
Report known mechanical check coverage separately from agent review of meaning,
rendering, z-order, overflow, inherited styles and unmodeled dependencies.
Tests cover groups/notes, text formatting, connector/timing dependencies, retained
charts/media/foreign parts, ID exhaustion/collisions, stale refs/CAS, tampered output,
reopened presentations, historical evidence/wiki and real SDK2 writeback/backups.

Published 1.0.1 covers PDF read/decompose/export, scoped DOCX/DFM writeback and
independent A2T table creation/edit/export. Native spreadsheet/presentation CRUD,
general asset registration, cross-format wiki export, per-format operation checks
and agent review workflows, and standards-aware APA/Chicago/CSL rendering remain
unfinished in that baseline. Version 1.1.0 adds custom citation display contracts to existing PDF
evidence/Foam and portable exports, plus a native file registry and scoped
spreadsheet operations described below. Remaining native-format adapters,
spreadsheet structural CRUD and academic style rendering are still unfinished. Conversion to
DOCX/PPTX does not prove native round-trip fidelity. ROADMAP.md tracks full scope.
Each milestone updates README, Pages, repository metadata/labels and Memory Bank;
reviewed commits are pushed in stages and releases require the full harness.

### Codex-driven PDF collaboration verification

Exercise the current checkout through a real Codex CLI MCP connection, in an
isolated synthetic-data workspace, without changing user MCP configuration.
Keep the expected transcription outside the agent workspace. Capture JSONL tool
events and independently compare persisted outputs with fixture truth; an agent's
success statement or a passing SDK transport test is insufficient evidence.

Cover digital, image-only and mixed/rotated PDF pages. Require source preflight,
ingestion, actual MCP image delivery, agent transcription, structured table CRUD,
source references and reusable asset export. Image-only pages must not acquire
fabricated text-span citations. Distinguish editing derived structured data from
rewriting the original PDF; preserve original hashes throughout the workflow.

Use deterministic SDK regressions for mechanical invariants and opt-in Codex
runs for perception/tool-use evaluation. The latter requires an authenticated
Codex CLI and may incur model usage; it must not silently run during pytest or
claim universal OCR accuracy from a small synthetic corpus. Record skipped,
failed, unperformed and successful checks separately.

Figure crop coordinates use unrotated cropbox-relative page space, consistently
with PDF preflight and native image locators. Intersect/pad in that space, then
transform the clip into the rotated rendering space. Rotated/cropped full-page
scans must retain the complete visible page; pixel comparisons against a full
page render and partial-region crops cover all right-angle rotations.
An image-only ingestion may legitimately have figures without section blocks.
Section-navigation errors must point agents to the document asset inventory and
image fetch path, rather than requiring a particular held extraction backend.

### Scalable native operation discovery (v1.4.0)

The SDK tool input retains the full typed NativeDocumentRequest schema. Native
contract discovery must not duplicate an ever-growing schema until the response
cap silently truncates it. Introduce native-contract-v2 with capabilities,
operation names, a canonical schema digest and an explicit schema delivery mode.
Small schemas may remain inline; large schemas are obtained via native op=schema
using bounded text_offset/text_limit chunks. Each page identifies the full schema
hash; subsequent pages require that hash and reject a changed installed contract.
Agents assemble the complete JSON and verify its hash before interpreting it.

contract(for_op=...) returns the declared schema for one operation, including only
its supported fields and transitive definitions, required/non-null inputs and the
unchanged field constraints. The operation field registry is shared with runtime
validation, so discovery cannot drift from required/unused field checks. Complete
request schemas remain available via schema without for_op. Runtime semantic
validators are still authoritative; JSON Schema is not a claim of exhaustive
validation of XML text, file states or preservation constraints.

Existing native operation inputs and aliases remain accepted. Discovery clients
must inspect schema_delivery instead of assuming schema is always inline; use the
returned schema_request or select for_op. This explicit migration replaces the old
oversized response failure, without raising global output limits or weakening any
validation keyword. The normal MCP tools/list schema remains complete.

### Native PPTX collaboration (v1.4.0)

Treat the original presentation as an immutable native root with revision-scoped
slides, shape trees, text runs, table cells, notes and exact package-part relations.
Resolve slide IDs through presentation relationships rather than assuming that
slide order determines package filenames. Preserve nested group hierarchy and
local coordinates; do not claim computed visual bounds or inherited formatting.
Native read/decompose returns bounded views and complete evidence representations;
unknown objects retain source XML and package attachments for agent interpretation.

Create independent PPTX documents using the existing python-pptx dependency.
Updates to existing presentations must operate on precise native targets, preserving
run/paragraph properties, layouts, masters, themes, media, charts and unrelated
package parts. Broad .text assignment can clear runs and is unsuitable for checked
preservation. Reopen and compare results before a managed revision CAS; source
publish/writeback remains explicit. Signed/protected, ambiguous or unsupported
operations must be explained without silently dropping features.

Component evidence binds original revision and locators; wiki projection retains
full records, exact source/package attachments and existing snapshots. Structural
CRUD and complete rendered/semantic review remain part of the broad objective;
each operation advertises its actual scope. MCP performs necessary deterministic
checks; agents review text meaning, overflow, layout, animations and object behavior.

Reference decisions: [python-pptx shape hierarchy](https://python-pptx.readthedocs.io/en/latest/user/understanding-shapes.html),
[text frames, paragraphs and runs](https://python-pptx.readthedocs.io/en/latest/user/text.html),
and [PresentationML package structure](https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document).

Implemented operations: create_pptx (presentation), read_pptx (asset_id with
revision/offset/limit), read_pptx_shape (asset_id/pptx_locator with JSON text pages),
update_pptx (asset_id/expected_revision/pptx_edits), native verify and export_wiki.
Locators carry slide_id, native part, slide/notes region and shape_id. Text edit
locators additionally carry paragraph/run indices and paired optional table row/
column. Regular runs are indexed independently of fields and line-break nodes;
text hashes are required preconditions. Tabs/newlines, field editing, merged-cell
continuations and structural edits are rejected. Creation supports explicit
text boxes, paragraphs, styled runs, dimensions in EMU and notes.

PPTX wiki projection pptx-shapes-v1 retains complete shape JSON/XML and every
original package part; previous opaque snapshots remain separate. Existing v1.2
XLSX and v1.3 DOCX artifact digests are regression guarded. Source/revision/CAS
checks are mechanical; visual bounds, inherited formatting, text overflow and
semantic accuracy require agent review. Legacy .ppt, macro .pptm and strict
PresentationML are outside the native editor's current scope.

### Native DOCX / DFM bridge (v1.3.0)

`read_docx` reads a registered DOCX immutable revision through the existing DFM
parser/renderer in a private temporary workspace. Its deterministic DFM projection
omits the session creation timestamp and binds the full native asset ID and SHA-256
revision in frontmatter. Return bounded character excerpts, the full projection
hash and paginated block summaries; clients must assemble every excerpt before
editing. Block IDs and locators are revision-scoped, not cross-version identities.

`update_docx` requires expected_revision and a complete docx_edit payload. Re-ingest
that immutable revision, check the native frontmatter binding, then reuse
DocxService.save_docx with force disabled. Existing DFM session/checksum,
pre/post-save, table-shape and unedited-block guards remain mandatory. Only after
these pass may a checked package become a managed native revision under the
repository's compare-and-swap lock. No update writes to the human source file;
publish/writeback remain explicit native operations with their existing checks.

Before parsing, enforce the native ZIP/member/XML limits, reject DTDs and require
the supported transitional DOCX main part. Signed/protected documents require a
separate editing workflow. After editing, verify identical member inventory and
unchanged bytes outside document.xml (plus settings.xml for explicit tracked
changes). Report changed parts/block IDs, preservation checks and agent review
requirements. This adds scoped existing-body edits, not arbitrary insertion,
deletion, style design, DOC/DOCM conversion or complete visual fidelity. Native
DOCX evidence/wiki integration is described below. Legacy operations remain available.

### DOCX component evidence and wiki projection (v1.3.0)

Native DOCX blocks expose the complete existing IR representation, native part and
revision-scoped block ID, plus a canonical representation hash. read_docx_block
returns bounded text excerpts with full-reference and full-text hashes. read_docx
summaries carry the same references; previews are never used to compute evidence.
verify resolves the immutable blob and exact block/part, recomputes the complete
representation and reports integrity separately from freshness and agent review.
Old references remain verifiable after edits/archive. The serializer's extraction
coverage is explicit: integrity does not prove that every OOXML feature was parsed.

DOCX export_wiki uses the distinct docx-blocks-v1 projection in snapshot identity,
so previously exported opaque DOCX snapshots and all XLSX/XLSM snapshots remain
untouched. Export full JSONL block representations/references, revision-pinned
block/index notes, the original DOCX and exact package-part attachments with
original-part-to-filename mapping and hashes. Each attachment's provenance points
to the original package member; do not infer chart values or fabricate media links
from temporary DFM filenames. Block/part locators drive custom citation display.

Retain existing no-overwrite publication rules. Reject whole exports exceeding
20,000 block records, 10,000 package parts, 30,004 artifacts or 128 MiB; never export
a silently incomplete evidence collection. Unknown/unsupported parsed semantics
remain available in the original and package parts for agent review. No claim of
full visual fidelity, automatic quality scoring or semantic claim verification.

### Native file assets and spreadsheet operations (v1.1.0)

A registered file receives a persistent asset ID independent of its filename and
content hash. Immutable revisions use SHA-256. Source identity, native structure,
capabilities and review coverage travel together; inferred meaning remains an
agent annotation, not a fabricated extraction result. Registration supports opaque
formats without pretending to provide a native editor for every format.

The first native adapter reads XLSX/XLSM worksheet/cell locators, creates independent
XLSX workbooks and updates/clears typed cells. It edits only the necessary OOXML
parts, retains styles and all unrelated ZIP member bytes, and checks the resulting
package before publishing an immutable managed revision. Shared/array formula
regions, rich-text replacements, protected sheets and digitally signed packages
require an explicit supported operation; unsupported edits fail without writing.
Formula caches are not evaluated by MCP. Edits set recalculation flags and report
cached formula values as unverified. Plain strings never become formulas implicitly.

The registry provides optimistic revision checks, serialized writes and retained
history. Updates first create managed revisions; explicit source writeback requires
the expected source hash plus the saved source stat to prevent stale replacement.
A source backup is retained. Removing an asset archives its registry entry; it does
not silently erase the human's source file. `refresh` adopts human source edits
without changing asset identity and rejects divergent unpublished edits.
Native cell reads include `native-cell-ref-v1`; chunked text keeps its full-cell
reference and a separate full-text hash. Version 1.2.0 adds the native wiki and
citation integration described below. See [operation details and limits](wiki/Native-File-Assets.md).

Read/modify limits apply before decompression and XML parsing. XML entity expansion,
external-resource resolution, path traversal and ambiguous package members are
rejected. A successful structural check proves its stated preservation scope, not
rendered fidelity or formula correctness; agent semantic/visual review stays open.

Reference decisions: [openpyxl preservation limits](https://openpyxl.readthedocs.io/en/stable/tutorial.html),
[XlsxWriter formula semantics](https://xlsxwriter.readthedocs.io/working_with_formulas.html),
and [Microsoft worksheet structure](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-sheets).

## 2. Core Architecture

### Native evidence verification and wiki publication (v1.2.0)

Native cell references must be independently checkable against the immutable
registered revision: verify blob hash, worksheet identity/part/kind, cell address
and the full canonical cell representation hash. Report whether that revision is
the current managed head separately from reference validity. This verifies native
representation integrity, not formula evaluation, rendered layout or claim support.
Old valid references remain verifiable after updates or archival.

Portable native wiki exports retain these references independently of custom
citation display. `native/export_wiki` creates an immutable revision snapshot under
the caller's wiki directory, with a source attachment, canonical JSONL cell records,
one index and revision-pinned cell notes. Note names derive from asset/revision/native
locator, never display metadata. Native worksheet/cell locators feed citation display;
caller metadata cannot override them. XLSX/XLSM expose stored cells, while other
formats export an explicitly opaque source without fabricated semantic notes.

New revisions create separate snapshots, preserving old links and adjacent curated
notes. Repeating an export verifies its complete inventory and exact bytes. Modified,
unexpected or symlink entries fail closed without overwriting them. A different
citation presentation for the same revision requires a separate output directory;
this first version does not rewrite existing notes. Output has explicit cell/byte
limits and never silently truncates. Publication reserves a new directory exclusively
and writes the manifest last as its completion marker. Interrupted exports retain
their files and report reconciliation rather than claiming atomic directory visibility.
Source/store overlap is rejected. Formula, semantic and rendered review remain agent
responsibilities. Standards-aware academic formatting remains separate work.

### Existing PDF bundle publication integrity

Refreshing an existing generated PDF bundle requires its complete declared artifact
inventory, manifest self-hash and file hashes to verify. Modified, missing, extra or
symlink entries reject replacement; the matching doc_id/version marker alone is not
ownership evidence. Recheck the observed manifest token under an OS advisory lock
immediately before publication. Identical exports reuse existing files. Changed
exports retain the previous directory as a named backup and return its path, so
late writes through external editors' open handles are not deleted. An external
writer is not serialized by the MCP lock; conflicts retain recoverable files and
must not claim successful publication. Source-overlap protections remain enforced.

### 2.1 DDD (Domain-Driven Design) 分層架構

```text
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                         │
│                   (MCP Server Interface)                     │
│  server.py - MCPServer tools & resources exposed to AI Agent│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Application Layer                          │
│                   (Use Cases / Services)                     │
│  DocumentService, AssetService, JobService, KnowledgeService │
│  TableService (A2T - Anything to Table)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Domain Layer                             │
│                   (Core Business Logic)                      │
│  Entities: Document, Manifest, Table, Figure, Section, Job   │
│  A2T Entities: TableContext, TableDraft, TableSchema         │
│  Value Objects: AssetType, DocId, JobStatus                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Infrastructure Layer                         │
│                 (External Dependencies)                      │
│  PyMuPDFExtractor (Core ETL), LightRAGAdapter,               │
│  FileStorage, FileJobStore, ExcelRenderer                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 ETL Pipeline: "The Mechanic"

- **PyMuPDF Integration**: Uses PyMuPDF (fitz) for lightweight and fast PDF-to-Markdown conversion, including heuristic-based table extraction and image extraction.
- **Asynchronous Processing**: Ingestion is handled as background jobs, allowing the Agent to track progress for large batches of documents.
- **Asset Decomposition**: Separates text, tables, and figures with page-level metadata.
- **Knowledge Graph**: Uses LightRAG to build a dual-index (Vector + Graph) for cross-document reasoning.
- **Document Manifest**: Generates a `manifest.json` for each document, acting as a "map" for the AI Agent.

### 2.3 A2T (Anything to Table) Workflow: "The Orchestrator"

- **Schema Planning**: `plan_table_schema` allows Agents to design table structures before creation.
- **Drafting System**: `TableDraft` provides persistent storage for work-in-progress tables, enabling resumption across sessions.
- **Batch Streaming**: `add_rows_to_draft` supports incremental data accumulation for long tables.
- **Token Efficiency**: `resume_draft` and `get_section_content` minimize context window usage.
- **Excel Rendering**: Professional output with auto-beautification based on table intent.

### 2.4 MCP Server: "The Interface"

- **Tools**: Exposes tools for ingestion, job tracking, manifest inspection, precise asset fetching, and A2T orchestration.
- **Resources**: Provides dynamic URI-based access to document outlines, tables, figures, and A2T table/draft states.
- **Vision Support**: Figures are transmitted as **Base64 images** within `ImageContent` for direct analysis by Vision-capable LLMs.

## 3. Tech Stack

| Category | Technology | Purpose |
| -------- | ---------- | ------- |
| Language | Python 3.10+ | Core runtime |
| MCP | official `mcp>=2,<3` Python SDK | MCPServer; SDK v1 unsupported |
| ETL | **PyMuPDF** | Primary PDF decomposition & Table recognition |
| RAG | LightRAG (`lightrag-hku`) | Knowledge Graph & Vector Index |
| Validation | Pydantic | Data models & validation |
| Storage | Local filesystem | JSON/Markdown/Image storage |

## 4. Project Structure (DDD)

```text
asset-aware-mcp/
├── src/
│   ├── domain/                      # 🔵 Domain Layer (Pure Logic)
│   │   ├── entities.py              # Document, Manifest, Assets
│   │   ├── job.py                   # ETL Job entities
│   │   ├── value_objects.py         # AssetType, DocId, JobStatus
│   │   ├── services.py              # ManifestGenerator
│   │   └── repositories.py          # Abstract interfaces
│   │
│   ├── application/                 # 🟢 Application Layer (Use Cases)
│   │   ├── document_service.py      # Ingestion orchestration
│   │   ├── job_service.py           # Async job management
│   │   ├── asset_service.py         # Precise asset retrieval
│   │   └── knowledge_service.py     # RAG & Graph queries
│   │
│   ├── infrastructure/              # 🟠 Infrastructure Layer (Impl)
│   │   ├── pdf_extractor.py         # PyMuPDF implementation (Core ETL)
│   │   ├── lightrag_adapter.py      # LightRAG integration
│   │   ├── file_storage.py          # Local file repository
│   │   ├── job_store.py             # Persistent job tracking
│   │   └── config.py                # Settings & environment
│   │
│   └── presentation/                # 🔴 Presentation Layer (Interface)
│       └── server.py                # MCP SDK 2 server entrypoint
│
├── data/                            # Local storage root
│   ├── {doc_id}/                    # PDF document artifacts
│   │   ├── {doc_id}_full.md         # Full text markdown
│   │   ├── {doc_id}_manifest.json   # Asset map
│   │   └── images/                  # Extracted figures
│   └── lightrag_db/                 # Knowledge graph database
```

## 5. MCP Interface Definition

### 5.1 Tools

| Tool | Input | Description |
|------|-------|-------------|
| `ingest_documents` | `file_paths`, `async_mode` | Start ETL pipeline (returns `job_id` if async) |
| `get_job_status` | `job_id` | Check progress of an ETL job |
| `list_jobs` | `active_only` | List recent or active ETL tasks |
| `list_documents` | None | List all ingested documents |
| `inspect_document_manifest` | `doc_id` | View the "Map" (Tables, Figures, Sections) |
| `fetch_document_asset` | `doc_id`, `type`, `id` | Get specific Table (MD), Figure (B64), or Section |
| `consult_knowledge_graph` | `query`, `mode` | Cross-document RAG query |

### 5.2 Resources

| URI | Description |
|-----|-------------|
| `documents://list` | List of all documents |
| `document://{id}/outline` | Bird's-eye view of document structure |
| `document://{id}/manifest` | Full JSON manifest |
| `document://{id}/tables` | List of tables in the document |
| `document://{id}/figures` | List of figures in the document |
| `knowledge-graph://summary` | Statistics and sample entities from the graph |

## 6. Image Handling (Base64)

- **Extraction**: PyMuPDF extracts figures with page numbers.
- **Transmission**: `fetch_document_asset` returns `ImageContent` containing the Base64 data.
- **Vision AI**: Agents can "see" the figure directly to interpret charts, diagrams, or medical imaging.

## 7. Constraints & Directives

1. **DDD Integrity**: Domain layer must remain pure and not depend on infrastructure.
2. **Job-Based ETL**: Long-running tasks must use the `JobService` to avoid timeouts.
3. **Manifest-First**: Agents are encouraged to use `inspect_document_manifest` or `outline` resource before fetching full content.
4. **Local-First**: All processing and storage must happen locally by default.

## Upstream adoption (2026-09-18)

- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk):
  current stable v2 API, MCPServer and Client; baseline runtime uses mcp>=2,<3.
- [Docling Core](https://github.com/docling-project/docling-core): native document
  hierarchy and provenance; retain original structure alongside agent projections.
- [MinerU](https://github.com/opendatalab/MinerU): compare current structured output
  contracts and rendering; the existing held adapter is not evidence of 4.x compatibility.
- [pikepdf](https://github.com/pikepdf/pikepdf): evaluate native PDF manipulation,
  object preservation and validation for future PDF CRUD.
- [GROBID](https://github.com/grobidOrg/grobid),
  [gmft](https://github.com/conjuncts/gmft) and
  [OmniDocBench](https://github.com/opendatalab/OmniDocBench): scholarly structures,
  table extraction and parsing evaluation. Selection requires local real-file
  evaluation; repository claims alone do not establish fidelity.

<a id="native-pdf-page-assets-and-structural-crud-14x-development"></a>

## Native PDF page assets and structural CRUD (1.4.1)

Goal: extend the immutable native asset registry to PDF pages, including native
read/decompose/render, independent creation, page insertion/copy/deletion/reorder,
geometry updates, explicit source writeback and immutable wiki evidence. This is
page-level editing, not arbitrary semantic text replacement or secure redaction.
MCP performs source/version, object-graph, known dependency and readback checks;
agents verify meaning, layout, accessibility, forms and viewer-specific behavior.

Use pikepdf/QPDF for object-aware edits and PyMuPDF for independent text/render
inspection. Preserve page identities during reorder by detach/reinsert, never
page assignment. Typed references bind asset ID, immutable revision, page index,
object/generation locator and canonical representation digest. Reject mismatched
or duplicate mutation targets and CAS conflicts. Source files change only through
existing guarded writeback with backups; historical refs remain valid.

Verification must account for source pages with text, images, vectors, crop/rotate,
annotations, forms, hyperlinks, bookmarks, metadata, attachments and inherited
page attributes. Object graph hashing must be bounded and stable across output
object renumbering, preserving stream data and shared references. Compare all
existing page content and document-level objects except planned changes, then
reopen with an independent parser. Document metadata is not silently imported by
page copying. Any unsupported dependency must be reported or rejected before
commit, not flattened or dropped. Encrypted/signed/repaired inputs require explicit
unsupported diagnostics rather than implicit protection removal or repair.

All operations use bounded schemas/pages and explicit preservation/review scopes.
Pikepdf compatibility, universal lock security, Python 3.10 and SDK2 transport must
be tested before enabling the adapter. Required tests include positive mixed
content CRUD, rendering/text preservation, internal links/forms/page labels,
negative corruption/dependency/stale writes, prior evidence/wiki stability, and
actual Codex MCP use. Included in the consolidated 1.4.1 release scope.

PDF copying must also check annotation graph backreferences. The initial pinned
pikepdf form-aware copy experiment duplicated note/popup graph objects and broke
the original reciprocal identity even though rendered pixels matched. A supported
deterministic repair may relink copied Popup/Parent/IRT pointers using the exact
source-to-destination annotation correspondence, followed by full graph equality.
Do not weaken the graph check merely to accept the upstream copy. Form fields must
remain registered in AcroForm and retain their source values/resources.

Native PDF worker results must use the existing private, atomic, size-bounded
MessagePack handoff used by PDF extraction. A pipe readability check does not
bound a subsequent full-frame receive; partial writes must not bypass the overall
worker deadline. Serialize NativeEditResult as plain data, then validate it in the
parent. Reject missing/partial/corrupt/oversized results and reap children before
removing their private temporary directory.

<a id="native-pptx-image-assets-and-picture-crud-14x-development"></a>

## Native PPTX image assets and picture CRUD (1.4.1)

Native picture operations move immutable image assets into and out of presentations.
MCP provides necessary checks; the Agent completes semantic/visual review.

- A native-file-ref-v1 identifies complete immutable file bytes by asset ID and
  revision SHA-256. It does not assert image meaning. Register remains the entry
  point for human PNG/JPEG files; canonical file verification uses managed bytes.
- add_pptx_pictures accepts revision-bound image references and existing slide,
  notes or nonzero-extent group containers. Use local EMU rectangles and explicit
  contain/cover/stretch fitting. Embed exact original image bytes, not a re-encoded
  copy. Persist source refs in operation history and expose new shape locators.
- replace_pptx_pictures targets complete current-revision shape references and
  new image references. Preserve the existing picture mapping (geometry, rotation,
  flips, crop, effects and z-order) by changing only the image relationship ID.
  This policy is explicit; new image aspect ratios may alter the displayed content
  and require agent review. Shared original image parts/relationships stay intact;
  never overwrite a shared part when replacing one picture. Reject external-linked,
  ambiguous and alternate-representation image targets rather than retaining a
  competing image rendition silently.
- read_pptx_picture resolves the pinned picture's internal image relationship,
  returns exact media hash/metadata and a real bounded MCP image preview. The
  preview is the embedded image, not a rendering of the slide/crop/effects.
  extract_pptx_picture creates an independent image asset from the exact embedded
  bytes with originating PPTX revision/shape/media lineage in its first history.
- Existing delete_pptx_shapes handles picture deletion and retains media; it is
  not secure erasure. Old presentation evidence and wiki attachments remain valid.
  Do not change the released shape-v1 representation/hash schema to add metadata.
- Preserve original package members byte-for-byte except planned owner XML,
  owner relationships and content types; retain ZIP member metadata. Add only
  explicitly planned media/relationship members. Compare exact new bytes,
  validate relationships/content types and reverse XML changes to prove the rest
  of each touched part is unchanged. Reopen independently with python-pptx in tests.
- Validate PNG/JPEG signatures/content, decompressed dimensions and resource budgets;
  reject multi-frame and EXIF-oriented inputs that cannot be faithfully displayed
  without an explicit transform. Keep immutable originals. Add corruption, shared-
  media, group/notes, stale/CAS/source backup, evidence/wiki and real SDK2 tests.
- Upstream public references: python-pptx Shapes.add_picture accepts width/height
  and preserves aspect when only one dimension is supplied; Image exposes exact
  blob, content type, dimensions and digest. Pillow provides verification and
  decompression-bomb limits. Use these libraries behind native ports, not a
  load-and-save of the user's whole presentation.

<a id="native-pptx-table-creation-unreleased-14x"></a>

### Native PPTX table creation (1.4.1)

`add_pptx_tables` accepts asset_id, expected_revision and 1–100 `pptx_tables`.
Each item identifies an existing slide/notes/nonzero-group container and a table
with local EMU left/top, explicit column_widths/row_heights, a rectangular cells
matrix, nonoverlapping inclusive merge rectangles, name and description. Width
and height equal the sums of column/row dimensions. Cells contain structured
paragraphs/runs, horizontal/vertical alignment, margins, optional RGB fill/text
colors. Numbers and formulas are literal display text, never recalculated.

The destination tableStyles relationship and default style GUID are resolved and
explicitly applied to the new table. Without that relationship no style ID is
invented. No foreign style/media relationships or parts are imported. Explicit first/last
row/column and banding switches control theme roles. Merges are established before
writing cell content. Covered cells must use the empty/default cell request so
content/formatting cannot silently disappear. Every new table is read back against
its requested grid, text, direct formatting and merge map. Scoped shape-tree
insertion retains exact existing package parts and reverses new nodes to verify
unmodified XML. MCP stages immutable versions with CAS; source writeback is explicit.

Read full tables through read_pptx_shape, edit native cell runs with update_pptx,
delete whole tables with full current shape refs via delete_pptx_shapes, and retain
historical evidence/wiki snapshots. Individual grid row/column insertion/deletion
and edits to existing merge maps remain follow-up work. Agent reviews actual slide
rendering, inherited table style, overflow, data interpretation and accessibility.
Budget: at most 100 rows/columns per table; 10,000 cells, 20,000 runs and 4 MiB UTF-8
text per batch. Per dimension and summed table extent stay within 100,000,000 EMU.

Implementation references: [python-pptx table concepts](https://python-pptx.readthedocs.io/en/latest/user/table.html)
and [public table API](https://python-pptx.readthedocs.io/en/latest/api/table.html).

#### Native citation display schema discovery

Actual Codex scanned-table run 01 correctly transcribed the image but tried to put
source proof objects into citation_contract. The runtime rejected those fields and
the agent recovered. NativeDocumentRequest now must expose a typed union of a
preset selector (`source`, `author-year`, `numeric`) and CitationFormatContract,
including required inline_template/reference_template and bounded allowed template
fields. Valid existing JSON inputs remain accepted; native wiki passes the typed
model's JSON representation to the existing resolver. Canonical source references
are separate from display contracts and cannot be overridden by formatting input.

<a id="native-derivation-ledger-unreleased-14x"></a>

### Native derivation ledger (1.4.1)

An agent may record that a revision-pinned native component/file was derived from
one or more other native references. `record_derivation` verifies the target and
every source before storing a bounded, content-addressed assertion. Supported
references are existing file/cell/DOCX-block/PPTX-shape/PDF-page references; no
invented locator or document text is accepted as proof. Activity, agent identity
and semantic/layout/formula review fields are caller assertions, never authenticated
identity or machine proof of meaning. Historical targets/sources remain explicit;
links never migrate automatically when a document changes.

`read_derivations` returns the complete append-only ledger as canonical JSON pages
pinned by `derivations_sha256`; continuations require that hash. Recording and
`retract_derivation` require `expected_derivations_sha256` from a prior read. A new
record can atomically supersede an active record on the same target asset. Retraction
and supersession preserve prior assertions. `verify_derivation` separately reports
active status, immutable-reference validity, current managed revisions and the
agent's review claims. It does not assert external-file freshness or semantic support.

Store the ledger separately from native file bytes, under the existing per-asset
operation lock with atomic writes and digest compare-and-swap. Bound each assertion
to 64 unique sources, each ledger to 1,000 events and 16 MiB. Validate event replay,
record hashes and target identity on load. Reject archived-target mutations,
self-references, stale writes, unknown/inactive replacements and malformed records.
No cross-asset transaction is required: references address immutable revisions.

Wiki export pins the ledger digest into a distinct snapshot identity, preserves
the full ledger for audit, and adds human-readable wikilink notes plus exact source
attachments for active assertions targeting the exported file revision. Verify
those references again before publishing; preserve existing snapshots/curated notes.
Retractions create new snapshots without rewriting old exports. Citation display
templates stay separate from canonical provenance. Existing no-ledger snapshots
retain their identities and byte format. Output byte/artifact budgets still apply.

References: [W3C PROV-O derivation](https://www.w3.org/TR/prov-o/#Derivation) and
[Docling Graph provenance ledger](https://github.com/docling-project/docling-graph/blob/main/docs/fundamentals/graph-management/provenance.md).
This API uses those concepts; it does not claim complete PROV-O/RDF conformance.

<a id="native-pptx-table-grid-editing-unreleased-14x"></a>

### Native PPTX table grid editing (1.4.1)

`update_pptx_table_grid` accepts `asset_id`, `expected_revision` and
`pptx_table_grid`: one full current shape `reference` plus 1..32 sequential
`edits`. Each edit is `insert`, `delete` or `resize`, with `axis` (`row` or
`column`) and zero-based `index`. Insert/resize specify EMU `sizes`; delete
specifies `count`. Insert may specify a row-major `cells` matrix (same typed
cell creation contract); omitted cells are blank. Indices apply to the result
of the preceding edit. No dimension may become empty or exceed 100 entries,
10,000 grid cells, 100,000,000 EMU total or the existing text/run budgets.

Insertions inside an existing merged rectangle extend it; insertions at its
start move it. New covered cells must be default/empty. Deletion shrinks a
partially surviving merge; if its anchor is deleted, retain the original
anchor content/format at the new top-left cell. Hidden content in a promoted
covered cell is rejected instead of discarded. Fully deleted merges disappear.
Resize preserves content and merge topology. Existing cell XML, row/column
metadata, table style, relationships and unrelated package bytes are retained
except requested deletion, merge flags and explicit anchor promotion. Shape
position remains fixed; its local extent follows the new grid totals, preserving
any existing grid-to-frame scale. Full shape hash, source revision/CAS and
archive/signature/protection checks precede mutation. Independently check final
grid dimensions/merges and serialized shape, restore the old shape to verify
unchanged surrounding XML, and compare every untouched package member.

References remain revision scoped; old evidence still verifies, but cell
coordinates and derivation assertions do not automatically migrate. Return
compact edit/promotion counts and a current-revision read request. Rendering,
banding/inherited styles, text overflow, semantics and unmodeled dependencies
remain Agent review. Package retention/deletion is not secure erasure.

Reference design: [python-pptx merge grid semantics](https://python-pptx.readthedocs.io/en/latest/user/table.html)
and [DrawingML row structure](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.tablerow).

<a id="native-pptx-mergesplit-edits-unreleased-14x"></a>

### Native PPTX merge/split edits (1.4.1)

Extend `update_pptx_table_grid.pptx_table_grid.edits` with two discriminated edits:

- `merge`: inclusive zero-based `row`, `column`, `end_row`, `end_column`, and
  required `content_policy` (`require_empty` or `append_paragraphs`). The rectangle
  must contain at least two cells and may wholly contain existing merges. Partial
  intersections are rejected; explicitly split those merges first.
- `split`: `row` and `column` identify an existing merge origin. Restore underlying
  cells without changing row/column dimensions or redistributing anchor paragraphs.

`require_empty` refuses meaningful content in any non-anchor cell, including fields,
breaks, links, extension/foreign content and paragraph identities. Original XML is
retained except merge flags. `append_paragraphs` retains the anchor's paragraphs and
appends the complete paragraph sequences of nonempty cells in row-major order,
including their internal empty paragraphs and any stored hidden text. Original
paragraph XML (run formats, fields, IDs, hyperlinks and unknown descendants) moves
within the same package part. Each moved-from body receives one empty paragraph;
its cell properties, body properties and list styles remain in place. Empty-only
cells remain unchanged. Empty anchor paragraphs are retained, without guessing
which formatting or blank lines are disposable. Unsupported text-body structure
blocks migration rather than concealing content. Existing relationships/parts stay
unchanged. Splitting does not reverse paragraph migration; historical references
and source versions retain the old positions.

Sequential insert/delete/resize/merge/split can be composed in one atomic request.
Existing shape hash, CAS, resource, package and readback checks remain mandatory.
Report counts for merged/split regions and migrated paragraphs. MCP verifies native
structure and literal XML; Agent checks meaning, inherited formats, overflow and
rendered output. No arbitrary finer grid is invented by split; insert rows/columns
explicitly when additional subdivisions are needed. Reference:
https://python-pptx.readthedocs.io/en/latest/user/table.html#un-merging-a-cell .

<a id="native-pptx-slide-structure-unreleased-14x"></a>

### Native PPTX slide structure (1.4.1)

`read_pptx_layouts` returns revision-pinned, paged layout identities discovered via
all presentation masters, including names, type and placeholder counts. New slides
use an explicit existing layout part, never a hard-coded layout index. The layout's
ordinary shape placeholders are instantiated empty using public python-pptx layout
semantics (date/footer/slide-number placeholders remain inherited). Layout styles
stay in their original parts; master prompt text is not copied into slide content.
Optional textboxes use existing typed run/EMU models. The loaded source presentation
is never resaved by python-pptx; only new slide nodes are extracted.

`add_pptx_slides` takes `pptx_slide_insert={index,slides:[{layout_part,textboxes}]}`
with a zero-based insertion boundary and 1..100 slides. `delete_pptx_slides` takes
`pptx_slide_keys=[{slide_id,part},...]` (1..100); `reorder_pptx_slides` takes a complete
`pptx_slide_order` permutation using the same keys. All require `asset_id` and
`expected_revision`; keys must resolve in that exact file revision. IDs and part
names of surviving slides stay intact. The slide limit for these operations is
2,000; input textbox budgets remain 20,000 runs / 4 MiB UTF-8. Empty decks are valid.

Deletion removes slide-list entries and their presentation relationships while
retaining original slide/notes/media bytes as detached parts (not secure erasure).
Incoming references from retained slides, custom shows, view settings or other parts
block deletion. Notes backreferences belonging exclusively to removed slides are
allowed. Reorder preserves independent custom-show ordering. Section lists and
index-based show ranges require a structure-aware workflow and block these edits.
Known extended-property slide/notes counts are updated; other cached document
properties stay intact and may need viewer refresh. Agents review unmodeled behavior.

Validate source protection/signatures, exact identities/permutation, slide/layout
relationships, unique new IDs/part names, resource limits, serialized slide ordering,
new placeholders/textboxes, and package bytes/XML outside the explicit plan. Failed
operations never commit partial revisions; old shape/file evidence and wiki package
attachments remain available. Existing source writeback requires CAS/source checks
and backups. MCP verifies mechanical preservation; Agent reviews inherited styles,
actual rendering, slide order meaning and interactions. Copy/import across decks,
new speaker-note structures and full visual validation remain additional work.

References: [python-pptx slides](https://python-pptx.readthedocs.io/en/latest/user/slides.html),
[Microsoft slide deletion](https://learn.microsoft.com/en-us/office/open-xml/presentation/how-to-delete-a-slide-from-a-presentation).
