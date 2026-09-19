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
