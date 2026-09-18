---
name: asset-aware-mcp-harness
description: "Cline harness for this repo (rules + workflows + checks). Triggers: cline harness, full check, release checklist, workflow, 文檔工作流, DFM, citation-ready."
---

# asset-aware-mcp: Cline Harness Skill

Use this skill when working in this repo with Cline and you want a reliable, production-grade loop: change -> verify -> ship.

## What To Use First
- Rules: `.clinerules/` (always-on, with conditional scopes)
- Workflows: `.clinerules/workflows/`
  - Run `/full-check.md` for the full local gates
  - Run `/release-publish.md` for a guided tagged release
- VSIX assistant assets: `vscode-extension/resources/repo-assets/asset-aware/`
  - Keep them synchronized with `cd vscode-extension && npm run sync-assets:check`
- Skills: this repo already has multiple skills under `.claude/skills/` (Cline can load them too)
  - If any `.claude/skills` instruction conflicts with current repo behavior, treat `.clinerules/` as the source of truth.

## Canonical Commands
- Python: `uv run ruff check .`, `uv run mypy src --ignore-missing-imports`, `uv run pytest`
- Extension (in `vscode-extension/`): `npm run test:ci`
- Docker smoke: `docker build -t asset-aware-mcp:smoke .` then `docker run --rm --entrypoint python asset-aware-mcp:smoke -c "import src.presentation.server"`

## Citation-Ready Mindset
- Prefer stable, verifiable spans (line/char/byte offsets + hashes) over loose “source: page 3” citations.
- Treat CRAAP fields as a conservative scaffold: avoid claiming more confidence than you can actually verify.

## Native Document Operations

- Discover the typed contract with `document(op="native", native_request={"op":"contract"})`.
  For native-contract-v2 (main, pending release), check schema_delivery. Use for_op
  for one operation or follow schema_request, retaining schema_sha256/for_op across
  pages; assemble all text_excerpt chunks and verify UTF-8 SHA-256 before parsing.
- Use native register/create/inspect/read_cell/update operations for workbooks;
  keep expected revisions and source hashes through publish/writeback/refresh.
- Keep source backups and report divergent edits for agent reconciliation.
  MCP performs mechanical checks and supported deterministic repairs; the agent
  verifies semantics, rendered layout and formula results.
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

## MCP Auto-Config Mindset
- VSIX install/update must keep Copilot `.vscode/mcp.json`, Cline `cline_mcp_settings.json`, and Codex `config.toml` idempotent.
- Preserve unrelated MCP servers and user-local Cline/Codex metadata.
- Do not create duplicate Asset-Aware server entries under alternative names.
