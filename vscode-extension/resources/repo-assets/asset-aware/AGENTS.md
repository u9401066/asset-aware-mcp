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
  erasure. Slide structure and arbitrary shape creation remain separate work.

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
