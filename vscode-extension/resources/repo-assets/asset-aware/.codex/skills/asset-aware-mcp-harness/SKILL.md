---
name: asset-aware-mcp-harness
description: "Codex harness for Asset-Aware MCP. Triggers: asset-aware, MCP, PDF, DOCX, DFM, citation-ready, CRAAP, release checklist, VSIX."
---

# Asset-Aware MCP: Codex Harness Skill

Use this skill when working with Codex on this repository, the VS Code
extension, MCP configuration, citation-ready document pipelines, or release
verification.

## What To Read First

- `AGENTS.md` for Codex workspace instructions.
- `.github/copilot-instructions.md` for cross-agent project guardrails.
- `.clinerules/` for implementation and release rules that also apply here.
- `memory-bank/activeContext.md` for the current working focus.

## Canonical Commands

- Python checks: `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src --ignore-missing-imports`, `uv run pytest`
- Extension checks: `cd vscode-extension && npm run test:ci`
- Assistant asset sync: `cd vscode-extension && npm run sync-assets:check`
- VSIX smoke: `cd vscode-extension && npm run test:install-smoke`
- Docker smoke: `docker build -t asset-aware-mcp:smoke .` then `docker run --rm --entrypoint python asset-aware-mcp:smoke -c "import src.presentation.server"`

## Citation-Ready Rules

- Prefer verifiable spans: source revision, span IDs, byte/char/line offsets,
  context text, and hashes.
- Keep CRAAP values conservative unless the implementation can justify them.
- Preserve aliases/backward compatibility when evolving MCP tool payloads.
- When table_cite advertises read, use it for complete cell/value/citation JSON;
  get remains a summary. Follow next_text_offset with one citation_sha256, assemble
  all text_excerpt chunks and verify UTF-8 SHA-256. Inspect exact source locators;
  stored-content integrity alone does not verify source validity or semantic support.

## Native Document Operations

- When pdf_regions_enabled is advertised, read_pdf_region takes a full PDF page
  reference plus pdf_region.rect in displayed CropBox fractions (0–1, top-left,
  after rotation), or a full existing region reference without selector override.
  Read the complete record and actual PNG; render_size changes detail, not identity.
  Agent checks glyph coverage/transcription and records explicit region-to-cell
  derivations. verify checks geometry/source only; read_selection selects region JSON.
  Wiki retains region JSON/PNG/render metadata and source PDFs. Missing external
  citation metadata is reported, never borrowed from target authors/year. Historical
  assertions do not migrate; sources/history stay unchanged. Public1.4.0 / 1.4.x.


- When table_workspaces_enabled is advertised, project_workbook_table pins an exact
  revision, worksheet key and range. Headers remain data; native columns hold
  tagged {kind,value} cells. Read the complete read_table_workspace JSON with one
  table_sha256, verifying assembled text_sha256. Use table_data with stable row_id
  and tagged values, then read again before apply_table_workspace at the exact
  table hash and bound native revision. Changed correspondence uses the explicit
  structural plan below; source styles/untouched parts survive supported edits.
  Read the new native revision and full stored operation result. Applied/exported
  inputs persist as workspace_reference snapshots; verify and re-read them even
  after mutable A2T changes. Bindings do not auto-advance. Structural A2T edits can
  create_workbook_from_table independently; it retains values/formula text but
  does not copy source layout or relocate formulas. Source refs describe origin,
  not semantic support for changed data. Agent reviews meaning/results/layout.
  Public stays 1.4.0; new work is Unreleased within 1.4.x.

- When worksheet_layout_enabled is advertised, read_worksheet_layout requires
  asset_id/revision/worksheet_key; read every chunk at one text_sha256. Update with
  expected_revision and worksheet_layout. Use explicit height_points/width_ooxml,
  reset_size or hidden; widths are raw OOXML, not Excel UI character counts.
  Native cells/styles stay intact; object anchors follow authored policies and
  recorded metrics. Formula/chart caches invalidate. Read complete review_request,
  render a new recalculated PDF, and inspect actual images/results. No AutoFit or
  visual verdict is inferred; history/source/evidence stay fixed. Public1.4.0 / 1.4.x.

- When workbook_rendering.configured is true, create_workbook_rendition pins XLSX
  asset_id/revision and requires workbook_rendition.mode (print/whole_sheet) plus
  calculation (recalculate/prefer_cache). Optional Calc creates a separate PDF.
  Read complete read_rendition at its creation revision and text_sha256, then all
  PDF page records/PNGs. Print may omit hidden/blank/out-of-range cells; whole-sheet
  includes hidden sheets but may clip overflow. Compare source formulas and actual
  images; no Excel fidelity verdict. Wiki retains the receipt and exact XLSX.
  Source caches stay unchanged; later PDF edits do not inherit sheet mappings.
  Agent owns semantic/visual/result review. Public1.4.0 / Unreleased1.4.x.

- When table_totals_lifecycle_enabled is advertised, update_workbook_table accepts
  table_update.totals_row with the exact revision, worksheet key, Table part/ref.
  Add requires blank cells below the Table; reuse_definitions restores hidden
  labels/functions/formulas, and cell_styles:last_data_row copies direct styles.
  Remove requires cells:clear or keep_cells; retain_definitions defaults true.
  Kept formulas freeze own Table references to pre-removal absolute ranges; other
  workbook references stay structured. No worksheet rows move. Compose explicit
  grid operations for space, read full receipts/references and review future
  formula membership/results/layout. Historical evidence stays unchanged.
  Public stays 1.4.0 / Unreleased within 1.4.x.

- When workbook_table_creation_enabled is advertised, add_workbook_table creates
  native Tables over explicit worksheet ranges in existing or independent workbooks.
  Pin file revision and worksheet key; supply ref, unique name and ordered columns.
  Matching headers preserve rich/shared strings; fill_blank only adds blank headers.
  Headerless Tables disable autofilter. Explicit totals rows must start blank; no
  worksheet rows are inserted. New calculated columns need blanks or replace_all.
  Choose built-in/existing Table styles; preserve ordinary data and cell formats.
  Read complete created_table, header_cells and operation_result after one commit.
  Active protection/overlap/source-schema checks remain. Agent checks meaning,
  rendered layout and recalculated results; old references/A2T bindings stay historical.
  Public stays 1.4.0 / Unreleased within 1.4.x.

- When workbook_table_edit_enabled is advertised, update_workbook_table pins the
  worksheet key, active Table part/ref, file revision and column IDs/expected names.
  Read complete references and header_cells XML first. Rich header_runs must match
  existing runs and concatenate to name; formatting/shared strings are preserved.
  Existing structured references follow renamed identities; new formulas use final
  names. Calculated require_matching rejects exceptions; replace_all explicitly
  replaces ordinary values. Null/keep_cells removes formula metadata only. Totals
  editing needs an existing totals row. Read full operation_result and new contents;
  Agent reviews meaning, filters, recalculated results and actual rendering. Source
  schema dependencies retain checks; old evidence/A2T bindings never migrate.
  Public stays 1.4.0 / Unreleased within 1.4.x.

- When table_expansion_enabled is advertised, complete read_workbook.tables exposes
  exact part/worksheet identity, attributes, column IDs, raw-part SHA and parsed XML.
  Each insert edit can expand_tables with part/expected_ref from that intermediate
  grid. Use first/last data or left/right column boundaries; insert before totals.
  Adjacent Tables are not selected implicitly. Native-generated headers/formulas
  are recorded at their final coordinates. A2T {kind:"native_generated",value:null}
  explicitly keeps ONLY a newly generated Table cell; missing/blank remain blank.
  Read generated_table_cells, resolved values, full native references and frozen
  intent. Review filter visibility, sorting, formula results and layout separately.
  Existing headers/formulas/totals, mapped sources and identity moves retain checks.
  Source bindings/evidence never auto-advance. Public remains 1.4.0 / Unreleased 1.4.x.

- When table_grid_apply_enabled is advertised, read the COMPLETE A2T structural_plan
  after edits and inspect current native references. Pass worksheet_grid explicitly
  to apply_table_workspace with the exact table hash and bound file revision. Stable
  row_ids/column_ids distinguish surviving, renamed and newly created identities.
  The plan moves whole worksheet axes, including outside the projection; deleted
  merged anchors are discarded. Unchanged formulas follow native relocation; new/
  edited formulas use destination coordinates. Read full new workbook references,
  operation_result and frozen workspace_reference, then verify the snapshot.
  Explicit Table edge expansion follows the policy above; specialized table edits
  and reordering retain their checks. Agent checks table membership, semantics, recalculated results and layout.
  Old bindings/evidence never auto-advance. native contract.for_op accepts native
  operation names only; table_data/table_manage use their exposed MCP tool schemas.
  Public stays 1.4.0 / Unreleased within 1.4.x.

- When workbook_grid_enabled is advertised, update_worksheet_grid takes an exact
  worksheet_grid.worksheet key and 1..32 sequential row/column insert/delete edits.
  Indices are one-based in each intermediate grid. Pin expected_revision, read the
  complete current workbook references before edits, and complete review_request
  afterward. Record geometry calibration; do not guess non-default font metrics.
  Inspect deleted-reference errors, table identities, moved objects and cache repairs.
  Agent review covers layout, automatic row heights and recalculated results. Old
  references and A2T bindings do not migrate. Source writeback remains explicit.
  Identical bytes can recur at a later history entry; compare the complete current
  operation receipt as well as file revision. Public stays 1.4.0 / Unreleased 1.4.x.


- When advertised, read_workbook returns complete hash-pinned structure/reference JSON.
  Pin revision and workbook_view, assemble text_excerpt pages and verify UTF-8 SHA-256.
  add_worksheets uses worksheet_insert; rename_worksheet uses worksheet_rename;
  reorder_worksheets supplies every current sheet_id/part key in worksheet_order;
  delete_worksheets takes selected worksheet_keys. Pin expected_revision, follow
  review_request and read full operation_result. Preserve 3D membership unless
  allow_3d_membership_change is explicitly intended. Known dependencies block
  deletion; detached parts remain, not secure erasure. Formula strings/external
  workbooks stay unchanged; Agent reviews dynamic references, results and rendering.
  Original sources and historical evidence remain intact; publication is explicit.
  Public stays 1.4.0, with new work Unreleased for 1.4.x.


- When advertised, read_selection accepts full native cell/block/shape/page refs.
  Read the complete parent with an empty selector, then select an actual RFC6901
  pointer and optional half-open Unicode character range. Assemble all pages at
  one text_sha256. Spans address parsed strings, never source-file bytes. verify
  and derivations accept selection refs; Wiki retains active selection records.
  Do not override an existing selection or infer native DOCX cell geometry from
  table text. New revisions never migrate assertions; Agent reviews meaning/layout.


- Discover the typed contract with `document(op="native", native_request={"op":"contract"})`.
  For native-contract-v2 (1.4.0+), check schema_delivery. Use for_op
  for one operation or follow schema_request, retaining schema_sha256/for_op across
  pages; assemble all text_excerpt chunks and verify UTF-8 SHA-256 before parsing.
- Use native register/create/inspect/read_cell/update operations for workbooks;
  keep expected revisions and source hashes through publish/writeback/refresh.
- Keep source backups and report divergent edits for agent reconciliation.
  MCP performs mechanical checks and supported deterministic repairs; the agent
  verifies semantics, rendered layout and formula results.
- When advertised, native PPTX supports create_pptx/read_pptx/read_pptx_shape/
  update_pptx. Assemble shape JSON at one revision and verify its UTF-8 hash; edit
  only the returned paragraph/run (and paired table row/column) locators with text
  hash preconditions. verify checks shape references; export_wiki retains shapes
  and exact package attachments. Agents review layout, overflow and inherited styles.
- When advertised, add_pptx_shapes inserts typed textboxes into existing slide,
  notes or nonzero-extent group containers; coordinates are local EMU. Delete with
  delete_pptx_shapes and full shape refs from the expected revision. Known surviving
  connector/timing/build references block deletion. Media and relationships remain;
  deletion is not secure erasure. Follow review_request and read complete shapes.
  Agents review rendering and unmodeled dependencies; source writeback is explicit.
- Native cell refs are not PDF AssetRefs. Version 1.2.0 adds native `verify` and
  `export_wiki`: immutable revision snapshots and full references with citation
  display. Existing notes are verified, never replaced; curate synthesis adjacent.
  Broader native CRUD remains separate; do not invent unsupported operations.

- Query the installed contract before native DOCX operations. When read_docx and
  update_docx are advertised, assemble DFM chunks at one revision, retain native
  frontmatter/block markers, and keep managed updates separate from source writeback.
  The agent reviews rendered Word layout and meaning; MCP performs DFM/package checks.
- When the installed contract advertises read_docx_block, use its revision-pinned
  evidence with native verify. DOCX export_wiki retains full parsed blocks and exact
  package parts in a distinct projection. Preserve old snapshots; extraction coverage
  and semantic support still require agent review. Never treat DFM temporary paths
  as persistent media attachments; use manifest.part_attachments.


- When advertised, create_docx creates independent native Word paragraphs and tables.
  add_docx_blocks inserts at start/end or before/after a full current block reference;
  delete_docx_blocks deletes complete body paragraphs/tables with docx_block_refs.
  Pin expected_revision, follow review_request, read all DFM chunks and block pages.
  Use update_docx for existing content; never alter block markers to insert/delete.
  Covered merged cells must be default empty. Known section/range/field/revision/
  embedded dependencies block unsupported deletion. Original parts/history remain.
  MCP checks serialized structure and untouched XML/bytes; Agent reviews page flow,
  inherited formatting, fields and rendering. When configured, render_docx_page
  returns actual whole-page MCP PNGs at an explicit revision/docx_page_index. Follow
  next_page_index and compare current/historical pages with full native content.
  Optional LibreOffice Writer uses exact source bytes; record renderer, page count
  and limitations. Fresh conversions can repaginate fields; indices belong to that
  rendition. Static previews do not certify Microsoft Word fidelity.
  Source publication/writeback is explicit; public stays 1.4.0 / Unreleased for 1.4.x.

- When configured, render_pptx_slide returns a whole-slide MCP PNG using optional
  LibreOffice Impress. Supply an explicit revision and exact pptx_slide_key from
  read_pptx; compare current/historical images with complete native content. Check
  overlap, clipping and inherited layout. Report the renderer and actual review
  scope; static LibreOffice output is not a PowerPoint fidelity verdict. Missing
  Impress or unsupported linked/show resources fail explicitly. Sources stay intact.

- When advertised, read_pptx_layouts discovers all destination masters' layouts at
  a pinned revision. add_pptx_slides uses explicit layout_part plus optional typed
  textboxes; ordinary placeholders start empty and inherit layout formatting.
  Read complete current slide listings via next_slide_offset. reorder_pptx_slides
  needs all slide_id/part keys once; delete_pptx_slides takes selected exact keys.
  Pin expected_revision, follow review_request and read complete shapes. Incoming
  retained dependencies, sections and index-based show ranges may block edits.
  Detached parts remain after deletion; not secure erasure. Agent reviews rendering,
  inherited styles, viewer caches and unmodeled interactions. Source writeback stays
  explicit; cross-deck copy/import and new notes structures remain additional work.

- When advertised, add_pptx_pictures embeds registered PNG/JPEG file_reference
  bytes in existing containers. replace_pptx_pictures uses full current shape refs
  and preserve_existing mapping; shared media is never overwritten. read_pptx_picture
  returns an actual embedded-image PNG, not a slide render. extract_pptx_picture
  creates an independent native image asset with source shape/media lineage.
  native-file-ref-v1 verifies immutable whole-file bytes, not meaning or live source
  freshness. Use read_pptx_shape for complete geometry/evidence; Agent reviews slide
  rendering, crop, effects and semantics. Delete via delete_pptx_shapes; retained
  media is not secure erasure. These operations remain Unreleased on the 1.4.x line.

- When advertised, add_pptx_tables inserts native editable tables into existing
  containers with explicit EMU grids, structured cell runs, formatting and merges.
  Covered cells must remain default/empty. Read complete shape JSON, edit anchor
  runs with update_pptx, and delete tables with current full shape references.
  Preserve exact display strings; formulas are literal text. Default table style
  comes from the destination; Agent reviews rendered layout and overflow.
  citation_contract is a typed display preset/custom-template union, not a place
  for source references or proof reports. Preserve canonical evidence separately.


- When advertised, update_pptx_table_grid applies 1..32 sequential row/column
  insert/delete/resize edits using a full current table reference. Indices address
  each intermediate grid. Merges expand/shrink; deleted anchors promote content
  only when covered-cell data will not be lost. Read complete updated shapes and
  review rendering, style banding and overflow. Old evidence remains historical;
  coordinates and derivation assertions do not automatically migrate.
  Merge edits require content_policy=require_empty or append_paragraphs. The latter
  moves exact rich paragraphs in row-major order to the anchor; partial intersections
  with existing merges fail. Split names an existing merge origin and leaves migrated
  content there. It never redistributes text. Read back and review the new layout.

- When derivations_enabled is advertised, read complete read_derivations JSON
  with derivations_sha256 before record_derivation/retract_derivation. Pin full
  target/source references; supersedes atomically replaces an active assertion,
  retaining history. verify_derivation separates activity, endpoint validity and
  caller-supplied agent review; follow next_offset at the same ledger hash.
  Record only reviews actually performed; hashes do not certify meaning. Native
  file revisions never inherit old assertions automatically. Wiki snapshots pin
  ledger hashes and attach sources for active assertions on the exported revision.

- When advertised, native PDF supports create_pdf/read_pdf/read_pdf_page/
  render_pdf_page/add_pdf_pages/update_pdf/delete_pdf_pages/reorder_pdf_pages.
  Pin revisions, assemble complete page JSON and verify its UTF-8 hash; retrieve
  current page refs before every mutation. PNGs are actual MCP images; native text
  is not OCR. Page copying retains explicit source lineage. Rotation is absolute;
  crop uses native PDF bottom-left user space, distinct from text-block coordinates.
  verify/export_wiki retain old evidence, exact PDFs and previews. Check supported
  dependencies before copying/deleting; cropping/deletion is not secure erasure.
  MCP checks graphs/versions and bounded unchanged-page rendering; agents review
  semantics, full-resolution layout, forms, scripts, reading order and accessibility.
  Stage managed revisions before explicit writeback with source checks and backups.

## Release Rules

- Treat VSIX install/update as a first-class release path.
- Confirm Copilot, Cline, and Codex MCP config merge behavior remains
  idempotent and non-destructive.
- Do not tag until sync-assets, unit tests, package contents, install smoke,
  artifact audit, Docker smoke, and git diff hygiene are clean.
