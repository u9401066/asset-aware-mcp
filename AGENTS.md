# Asset-Aware MCP Codex Harness

These are workspace instructions for Codex when working with Asset-Aware MCP
through the VS Code extension, local CLI, or MCP server.

## Goal

Help the user build and operate citation-ready document workflows that preserve
precise evidence provenance for PDFs, DOCX files, tables, figures, DFM edits,
and LightRAG knowledge graph outputs.

## Working Style

- Use Traditional Chinese unless the user asks otherwise.
- Prefer exact file paths, command output summaries, and verification results.
- Treat messy document inputs as normal: broken numbering, mixed encodings,
  nested tables/lists, OCR artifacts, and repeated format conversions are all
  expected.
- When changing behavior, add a regression test that proves the edge case stays
  fixed.

## Core Workflow

1. Ingest or convert the document with the narrowest suitable MCP tool.
   For PDFs, run
   `document(op="preflight", pdf_path="/absolute/path/source.pdf")` first when
   OCR or layout quality is uncertain.
2. Preserve source identity with stable IDs, locator metadata, and hashes.
3. Keep DFM/DOCX round trips reversible and prompt before destructive writes.
4. Use CRAAP as a conservative evidence-quality scaffold; do not invent scores.
5. Prefer line/char/byte spans plus surrounding context for citation-ready
   claims.
6. Re-run the focused tests for changed code, then the full release harness
   before publishing.
7. Export reusable agent assets with
   `document(op="export_assets", doc_id="doc_...", output_dir="agent-assets")`;
   use the generated Foam index and notes as the portable wiki layer.

## Native Files and Agent Review

- When pdf_annotations_enabled is advertised, read_pdf_annotations pins asset/revision;
  read_pdf_annotation also takes pdf_annotation_locator. Assemble ALL annotation
  text pages at one text_sha256, including catalogs and complete operation receipts.
  update_pdf_annotations pins expected_revision and full page/annotation references;
  1..32 create/update/delete edits address the original revision, each target once.
  Typed appearance positions use displayed rotated CropBox fractions, top-left;
  markup quads use UL/UR/LL/LR. Metadata omitted keys stay; null removes. Visible
  FreeText changes require explicit same-kind replace_appearance. Contents is a
  comment, not underlying highlighted text; FreeText can enter page text extraction.
  Delete scope:annotation_and_owned_popup; include dependent replies explicitly.
  Shared arrays, locks, signatures, widgets, standalone popups and unsupported
  rich/appearance edits retain guards. Read complete review_request/new refs and
  actual affected page PNGs. Agent reviews geometry, meaning and viewer behavior.
  Old refs/selections/derivations/citations/Wikis remain historical; no secure erasure.
  Annotated PDFs use pdf-annotations-v1; no-annotation legacy Wiki stays unchanged.
  Public1.4.0;next consolidated1.4.1;no per-feature version bump.

- When docx_notes_enabled is advertised, read_docx_notes pins revision and pages
  full catalog/catalog_sha256/latest operation_result through note. read_docx_note
  takes docx_note_locator(part,note_kind,note_id); assemble ALL pages at text_sha256.
  Native IDs are not displayed numbering; roles come from w:type, not reserved IDs.
  update_docx_note needs full docx_note_reference, expected_revision and locator plus
  all_native_references scope. update_docx_notes pins catalog hash and explicit
  definitions_and_native_body_references scope; create uses typed blocks and a body
  text_path/Unicode character_offset/expected_text_sha256 from text_nodes[].text_sha256.
  Delete uses locator/exact note hash/literal_body_text:preserve; literal custom marks
  remain for explicit Agent correction. Special definitions and dependency-heavy edits
  have explicit limits. Read full receipts/current notes and EVERY actual page; review
  numbering, placement, bindings, fields and meaning. Explicit remap_ids supplies
  part/note_kind and mappings of note_id to new_note_id; normal definitions and all
  editable main-body references change atomically. Check mapping receipts and read
  new refs. Definition order, special roles, literal content and styles stay intact.
  Reader-specific misbindings need actual before/after pages; old refs stay tied to
  historical revisions. Existing IDs stay unless explicitly remapped; source/history
  and old references stay intact. docx-notes-v1 Wiki retains full evidence/parts; no-note
  documents keep their legacy projection. Public1.4.0, next consolidated1.4.1.

- Native discovery advertises contract_delivery separately from schema_delivery.
  When paged, assemble ALL contract_request / contract_details pages using one
  contract_sha256 and for_op; check UTF-8 text_sha256 before reading complete policies.
  Keep every enabled flag and format/schema continuation from the compact index.
  Rediscover on capability/scope/hash changes; never operate from preview_json.
- When docx_story_structure_enabled is advertised, read_docx_story_structure pins
  revision and pages full catalog/catalog_sha256/latest operation_result. Update
  with expected_revision, docx_story_structure.expected_catalog_sha256, explicit
  scope sections_and_following_inheritors and sequential create/clone/bind/delete/
  first_page/even_pages edits. Clone/delete need exact part hashes. bind part:null
  resumes inheritance, not blank; create/bind an empty paragraph to blank a slot.
  Explicitly rebind following sections when retaining their previous definitions.
  Read every receipt/story and actual page. Supported unique identities are remapped;
  range/control/revision/note/embedded cloning dependencies remain explicit limits.
  Deleted parts retain historical refs/Wikis; orphan media is not securely erased.
  Public1.4.0, next consolidated1.4.1; no per-feature bump.

- When docx_stories_enabled is advertised, read_docx_stories discovers actual
  header/footer definitions, section inheritance and dormant/shared bindings.
  read_docx_story pins docx_story_part; assemble every story page at one text_sha256.
  update_docx_story needs full docx_story_reference and expected_revision; its
  docx_story_update requires part, shared_scope:all_sections_using_part and sequential
  set_text/insert_blocks/delete_blocks edits. Paths/indices address intermediate XML.
  Read complete receipts and all affected actual PNGs. Literal field caches and
  alternate/revision branches are not evaluated results. Preserve historical refs;
  selections/derivations/citations and docx-stories-v1 Wiki retain full evidence.
  Legacy DFM header/footer fields are abbreviated; never infer roles from filenames.
  Definition lifecycle/relinking and note CRUD use their separate operations above.
  Public1.4.0; next consolidated1.4.1, no per-feature version bump.

- When docx_table_layout_enabled is advertised, update_docx_table_grid accepts
  set_header_rows(count) and set_row_layout(index,count,height,split). Header rows
  form a contiguous prefix; do not cut a vertical merge. Height rule auto/inherit
  has no value; at_least/exact requires value_twips. Split allow/prevent/inherit
  changes direct properties; omitted fields stay intact. Read full before/after
  operation_result and all current row_layout/native XML pages, then EVERY actual
  Word page PNG. Exact heights can clip; oversized rows can still span pages.
  Inherited styles and Microsoft Word parity require Agent review. Source bytes,
  historical references and Wikis remain intact. Public1.4.0 / Unreleased1.4.x.

- When docx_table_grid_enabled is advertised, read_docx_table requires a full
  docx_table_reference, asset_id and revision. Read all grid/native XML chunks at
  one text_sha256; omitted positions and merged coverage are not empty cells.
  update_docx_table_grid pins expected_revision and full reference; 1..32 sequential
  zero-based insert/delete/resize/merge/split edits use each intermediate grid.
  sizes_twips means minimum row height or fixed column width. merge requires
  require_empty/append_blocks; split keeps anchor content, other cells blank.
  Mutation summaries are bounded; full operation_result is in paged table reads.
  Repeated file SHAs can have newer receipts: verify complete text_sha256.
  Read complete review_request and current references, then all actual Word page
  PNGs. Sources/history/Wiki remain unchanged; table refs are not new cell refs.
  MCP checks native structure/bytes; Agent reviews meaning, inherited styles,
  repeated headers, nested overflow and page flow. Public1.4.0 / Unreleased1.4.x.

- For legacy PDF ETL evidence, discover inspect_etl_source/capture_etl_source/
  read_etl_source/view_etl_source through evidence csl_contract. Inspect selectors
  return complete current AssetRefs without writing; capture requires the whole
  verified ref. Read all hash-pinned pages, then retain etl-citation-ref-v1 and view
  actual captured original PDF pages. Mixed CSL sources accept captured/native
  refs; Wiki retains all snapshot artifacts. ETL deletion cannot change snapshots.
  Hash/locator checks do not prove extraction, semantics or bibliographic truth;
  Agent reviews those and coordinates corrections. Public1.4.0 / Unreleased1.4.x.

- For document-context academic citations, discover evidence(op="csl_contract")
  completely, then render_citations with structured CSL-JSON items and ordered
  clusters. Read every text page at one text_sha256. sources holds full native
  references; source_keys binds cites without overriding canonical locators.
  Printed CSL locators and bibliographic truth require Agent review. wiki_root
  exports immutable citations, source files and a typography preview; use the
  preview hash as expected_text_sha256. Old refs/snapshots remain historical.
  CSL uses optional local Node.js; existing custom display templates remain.
  Public1.4.0 / Unreleased1.4.x; no per-feature version bump.

- When delimited_enabled is advertised, create_delimited creates independent CSV/TSV
  string tables. Pin revisions for read_delimited/read_delimited_cell; logical row/
  column indices are zero-based. Assemble complete JSON at one text_sha256. Explicit
  delimited_dialect binds delimiter/quote/escape/encoding; custom settings must follow
  all reads, edits and Wiki. No header/type inference. update_delimited uses full refs
  for set_cells or explicit row/column positions. Native byte splices retain untouched
  spelling/EOL/BOM; required empty-field/row-separator repairs are recorded. Read the
  complete review_request receipt; no-op updates create no history entry. Same file
  SHA may recur with a newer receipt. verify/selections/derivations/Wiki bind exact
  fields/dialects; old refs never migrate. Agent reviews meaning and downstream
  rendering/formula interpretation. Public1.4.0 / Unreleased1.4.x; no per-feature bump.

- PDF listings/page records may include parser_checks for independently proven
  equal, direct duplicate stream Length values. Keep those observations with the
  evidence; original bytes are unchanged. Other warnings/conflicting/indirect
  lengths still require a separate repair workflow. Requested page edits/copies
  record canonicalized_equal_duplicate_stream_lengths when serialized. Agent
  reviews actual images and meaning; these checks are not an OCR/fidelity verdict.

- When pdf_regions_enabled is advertised, read_pdf_region takes a full PDF page
  reference plus pdf_region.rect in displayed CropBox fractions (0–1, top-left,
  after rotation), or a full existing region reference without selector override.
  Read the complete record and actual PNG; render_size changes detail, not identity.
  Agent checks glyph coverage/transcription and records explicit region-to-cell
  derivations. verify checks geometry/source only; read_selection selects region JSON.
  Wiki retains region JSON/PNG/render metadata and source PDFs. Missing external
  citation metadata is reported, never borrowed from target authors/year. Historical
  assertions do not migrate; sources/history stay unchanged. Public1.4.0 / 1.4.x.


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


- For native workbooks use `document(op="native", native_request={"op":"contract"})`.
  Register an existing file or create XLSX independently; typed cell edits use the
  returned expected revision. Edits create managed versions before explicit writeback.
- Refresh human source changes under the same asset ID. Divergence requires agent
  reconciliation; never discard either revision to make a stale check pass.
- MCP checks package/source/value integrity and supports deterministic repairs.
  Agents verify semantics, rendered layout and recalculated formulas. Read-back or
  byte preservation alone does not prove full visual fidelity.
- Use `read_cell` with text offsets for long cells. Native cell references differ
  from PDF AssetRefs. Since 1.2.0, `verify` checks native refs and `export_wiki`
  creates immutable snapshots; preserve existing notes and keep synthesis adjacent.

- Query the contract for native DOCX support. read_docx chunks must use one
  revision; update_docx requires complete DFM with its original native binding and
  block markers. Updates create managed revisions before explicit source writeback.
  When advertised, read_docx_block returns revision-pinned native references; verify
  checks the parsed representation. DOCX wiki snapshots retain exact package parts;
  extraction completeness, meaning and rendered layout require agent review.

- Since 1.4.0, native-contract-v2 supports for_op and hash-pinned
  schema pages. Check schema_delivery and preserve schema_sha256 while assembling.
  Query the installed contract before PPTX operations: create/read/read-shape/update
  work on native presentations with revision/run-text preconditions. Shape refs and
  wiki snapshots preserve exact native representations/parts. Agents review semantics,
  inherited formatting, rendered layout and overflow. When advertised, add_pptx_shapes
  inserts typed textboxes; delete_pptx_shapes uses full current-revision shape refs.
  Known dependencies block deletion; retained media means deletion is not secure
  erasure. Slide structure is described below; arbitrary shape creation remains separate.


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


- When advertised, read_selection accepts full native cell/block/shape/page refs.
  Read the complete parent with an empty selector, then select an actual RFC6901
  pointer and optional half-open Unicode character range. Assemble all pages at
  one text_sha256. Spans address parsed strings, never source-file bytes. verify
  and derivations accept selection refs; Wiki retains active selection records.
  Do not override an existing selection or infer native DOCX cell geometry from
  table text. New revisions never migrate assertions; Agent reviews meaning/layout.

## PDF -> Asset Engine Selection

The core goal is turning documents into complete, agent-friendly figure/table/
text assets, fast. `ETL_ENGINE` selects the extraction backend; structured
engines lazy-load and gracefully fall back to PyMuPDF when unavailable:

- `pymupdf` (default) - fast, no models, always available.
- `pymupdf4llm` (`[pdf-plus]`) - drop-in layout-aware upgrade, no GPU.
- `docling` (`[docling]`) - MIT-licensed layout+table+formula+chart engine;
  bridges through an isolated `.venv-docling` interpreter via subprocess when
  the main environment cannot install it directly (see
  `docs/docling-setup.md` for cross-platform install).
- `mineru` - adapter retained for upstream evaluation, but the packaged
  `[mineru]` extra is an empty security hold while MinerU pins
  `transformers<5` and patched releases require `transformers>=5.5`.
- `marker` - disabled; marker-pdf pins `Pillow<11`, incompatible with the
  `Pillow>=12.2.0` security floor.

The active packaged structured engines, PyMuPDF4LLM and Docling, resolve the
current security floors. Structured engines share the `StructuredPDFExtractor`
protocol and emit a common result so they plug into the existing ingestion
pipeline without touching its logic. Adapters live in
`src/infrastructure/{pymupdf4llm,docling,mineru}_adapter.py`; engine selection
is in `src/infrastructure/extractor_factory.py`.

The runtime requires the official MCP Python SDK `>=2,<3` and uses
`MCPServer`. MCP SDK v1 / `mcp.server.fastmcp` is intentionally unsupported.

## Repository Work

- Treat `.codex/skills`, `.cline/skills`, `.clinerules`, `.github/agents`, and
  `.github/copilot-instructions.md` as bundled assistant harness assets.
- Run `npm run sync-assets` in `vscode-extension/` before packaging the VSIX.
- Keep `vscode-extension/resources/repo-assets/**` synchronized with source
  files via `npm run sync-assets:check`.
- Preserve custom user MCP settings, Cline `alwaysAllow`, Codex comments, and
  unrelated server entries during extension install/update flows.

## Guardrails

- Never overwrite a source DOCX without checking stale mtime/session state.
- Never loosen citation locator integrity just to make a test pass.
- Do not commit generated outputs from `dist/`, `vscode-extension/out/`,
  `.venv/`, or document processing data directories.
- Keep the VSIX install path production-grade: native Copilot MCP provider,
  workspace `.vscode/mcp.json`, Cline MCP settings, Codex MCP config, and
  bundled harness assets must remain in sync.

## Related Files

- `.codex/skills/asset-aware-mcp-harness/SKILL.md`
- `.cline/skills/asset-aware-mcp-harness/SKILL.md`
- `.clinerules/workflows/full-check.md`
- `.clinerules/workflows/release-publish.md`
- `.github/copilot-instructions.md`
- `.github/agents/asset-aware-document.agent.md`
