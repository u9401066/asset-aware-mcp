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

## Release Rules

- Treat VSIX install/update as a first-class release path.
- Confirm Copilot, Cline, and Codex MCP config merge behavior remains
  idempotent and non-destructive.
- Do not tag until sync-assets, unit tests, package contents, install smoke,
  artifact audit, Docker smoke, and git diff hygiene are clean.
