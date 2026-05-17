# MCP Tool Surface Consolidation Plan

> Status: implemented and carried forward for the `v0.7.0` release candidate.

## Goal

Make the default MCP runtime surface easier for agents without removing
capability:

- `balanced`: default, 30 public tools for Cline/Codex/Copilot.
- `compact`: 17 operation-based facade tools for strict allow-lists.
- `legacy`: 63 decorator/direct tools for older clients and migrations.

Resources are not consolidated in this pass. The public endpoint story is
therefore 30 public tools + 13 resources = 43 public MCP endpoints.

## Implemented Shape

The balanced surface is:

- 17 facade tools:
  `document`, `document_asset`, `evidence`, `convert_document`, `docx`,
  `docx_table`, `job`, `knowledge`, `etl_profile`, `section`, `plan_table`,
  `table_manage`, `table_data`, `table_cite`, `table_history`, `table_draft`,
  `discover_sources`
- 13 shortcut tools:
  `ingest_documents`, `list_documents`, `parse_pdf_structure`,
  `fetch_document_asset`, `find_evidence_spans`, `verify_citation_ref`,
  `citation_bundle`, `ingest_docx`, `get_docx_content`, `save_docx`,
  `get_job_status`, `list_jobs`, `docx_table_edit_plan`

## Files Touched

- Runtime policy: `src/presentation/tool_surface.py`
- Server entrypoints: `src/presentation/server.py`, `src/server.py`
- Facade parity: `src/presentation/tools/document_tools.py`,
  `src/presentation/tools/section_tools.py`,
  `src/presentation/tools/__init__.py`
- Count/smoke scripts: `scripts/count_tools.ps1`, `scripts/count_tools.sh`,
  `scripts/smoke_mcp_stdio.py`
- Docs: `README.md`, `README.zh-TW.md`, `vscode-extension/README.md`,
  `docs/wiki/MCP-Tools.md`, `docs/wiki/MCP-Tool-Consolidation.md`,
  `docs/wiki/Tool-Chooser.md`, generated docs site payload
- Tests: `tests/unit/test_mcp_server_startup.py`,
  `tests/unit/test_mcp_section_tools.py`,
  `tests/unit/test_mcp_document_tools.py`,
  `tests/unit/test_count_tools_script.py`,
  `tests/unit/test_docs_site_reference_sync.py`,
  `tests/test_mcp_tools.py`, VSIX install smoke tests

## Verification Checklist

- `uv run python -m src.server list-tools --json`
  returns `surface=balanced`, `count=30`.
- `ASSET_AWARE_MCP_TOOL_SURFACE=compact` returns exactly 17 facade tools.
- `ASSET_AWARE_MCP_TOOL_SURFACE=legacy` and
  `ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS=true` expose the full direct-tool
  compatibility surface.
- `scripts/count_tools.ps1` reports default public tools, decorator inventory,
  resources, public endpoints, and legacy endpoints separately.
- Docs and VSIX copy describe balanced public tools, not legacy decorator count,
  as the default user-facing surface.

## Follow-Up Product Work

A2T design improvements remain valuable after the surface consolidation:

- Stable row IDs.
- Large-table paging/chunking and artifact-only mode.
- Clearer UX when large tables are skipped or previewed.
- More granular table/section citation provenance.
- Row search/filter/coverage tools.
