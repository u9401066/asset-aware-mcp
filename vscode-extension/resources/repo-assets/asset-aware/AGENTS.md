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
