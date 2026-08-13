<!-- Generated from MCP-Tool-Consolidation.md by scripts/build_docs_site.py -->

# MCP Tool Consolidation Plan

本文件記錄目前 MCP tool surface 的整併策略。目標不是砍功能，而是讓 agent
預設看到更少、更穩定、更任務導向的入口，同時保留舊 client 的 direct tool
名稱相容模式。所有模式都使用官方 MCP Python SDK 2 `MCPServer`；SDK v1 不受
支援，`legacy` 也不代表 v1 protocol compatibility。

## Current Policy

| Surface | 啟用方式 | Tool count | 用途 |
|---|---|---:|---|
| `balanced` | 預設，或 `ASSET_AWARE_MCP_TOOL_SURFACE=balanced` | 30 | 一般 Cline/Codex/Copilot 建議模式。 |
| `compact` | `ASSET_AWARE_MCP_TOOL_SURFACE=compact` | 17 | 只保留 operation-based facade tools，適合嚴格 allow-list。 |
| `legacy` | `ASSET_AWARE_MCP_TOOL_SURFACE=legacy` 或 `ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS=true` | 63 | SDK 2 上的舊 client/direct tool-name 相容模式。 |

## Compact 17 Tools

| Target tool | 收納範圍 |
|---|---|
| `document` | PDF preflight、auto ingest/readiness、list/delete/inspect/parse/OCR/layout/segmentation、agent asset export、audit/accessibility/pointer_index/structural_retrieve/compare |
| `document_asset` | asset fetch、asset Foam notes、section forwarding |
| `evidence` | citation span find/verify/bundle/locate/claim promotion/wiki health |
| `convert_document` | PDF/DOCX/Markdown conversion |
| `docx` | DOCX/DFM ingest/read/save/list/delete/blocks/validation |
| `docx_table` | DOCX table/chart extraction、write-back、edit plan |
| `job` | background job get/list/cancel |
| `knowledge` | KG consult/export |
| `etl_profile` | ETL profile list/get/current/set/load/detect |
| `section` | section tree/detail/blocks/search/content |
| `plan_table` | A2T schema/template planning |
| `table_manage` | A2T create/delete/list/preview/resume/render/schema ops |
| `table_data` | A2T row/cell read-write ops |
| `table_cite` | A2T cell citation ops |
| `table_history` | A2T audit/history/token ops |
| `table_draft` | A2T draft create/update/resume/commit/list/delete |
| `discover_sources` | A2T source discovery |

## Balanced Shortcuts

Balanced surface = compact 17 + 下列 13 個高頻 shortcut direct tools：

| Shortcut | 保留原因 |
|---|---|
| `ingest_documents` | PDF 攝入是最常見起點，名稱直覺。 |
| `list_documents` | 輕量、唯讀、常用於 smoke 與探索。 |
| `parse_pdf_structure` | Configured structured parse 需要清楚 exposed diagnostic path。 |
| `fetch_document_asset` | asset 精讀常用且語意清楚。 |
| `find_evidence_spans` | citation workflow 高頻入口。 |
| `verify_citation_ref` | fail-closed citation verification 高頻入口。 |
| `citation_bundle` | evidence bundle/Foam pack 高頻入口。 |
| `ingest_docx` | DOCX workflow 高頻起點。 |
| `get_docx_content` | DOCX/DFM 讀取高頻入口。 |
| `save_docx` | DOCX write-back 高頻入口，但仍保留 stale/validation guard。 |
| `get_job_status` | 長任務狀態查詢高頻入口。 |
| `list_jobs` | 長任務列表與 release smoke 常用。 |
| `docx_table_edit_plan` | 半安全 shortcut：先看 write-back 風險再改表。 |

## Legacy Mapping

### Job Tools

| Legacy direct tool | Target |
|---|---|
| `get_job_status(job_id)` | `job(op="get", job_id=...)` or `job(op="status", job_id=...)` |
| `list_jobs(active_only)` | `job(op="list", active_only=...)` |
| `cancel_job(job_id)` | `job(op="cancel", job_id=...)` |

### ETL Profile Tools

| Legacy direct tool | Target |
|---|---|
| `list_etl_profiles()` | `etl_profile(op="list")` |
| `get_etl_profile(name)` | `etl_profile(op="get", name=...)` |
| `get_current_etl_profile()` | `etl_profile(op="current")` |
| `set_etl_profile(name)` | `etl_profile(op="set", name=...)` |
| `load_etl_profile_from_json(json_path)` | `etl_profile(op="load", json_path=...)` |
| `detect_etl_profile(...)` | `etl_profile(op="detect", ...)` or `etl_profile(op="auto_detect", ...)` |

### Section Tools

| Legacy direct tool | Target |
|---|---|
| `list_section_tree(doc_id, max_depth, format)` | `section(op="tree", doc_id=..., max_depth=..., format=...)` or `section(op="list", ...)` |
| `get_section_detail(doc_id, path)` | `section(op="detail", doc_id=..., path=...)` |
| `get_section_blocks(doc_id, path, include_children, block_types, limit)` | `section(op="blocks", ...)` or `section(op="list_blocks", ...)` |
| `search_sections(doc_id, query, fuzzy)` | `section(op="search", doc_id=..., query=..., fuzzy=...)` |
| `get_section_content(doc_id, section_id)` | `section(op="content", doc_id=..., section_id=...)` |

### PDF Document Tools

| Legacy direct tool | Target |
|---|---|
| Safe route inspection before ingest | `document(op="preflight", pdf_path=...)`; returns stable `pdf-preflight-v1` without mutating the source |
| `ingest_documents(file_paths, ...)` | `document(op="ingest", file_paths=..., ...)` |
| AI-ready handoff for new or existing PDFs | `document(op="auto", file_paths=[...])` or `document(op="auto", doc_id=...)` |
| Combined PDF readiness audit | `document(op="audit", doc_id=...)`; use `refresh=true` only when artifacts must be rebuilt |
| PDF readiness state and next actions | `document(op="prepare_ai", doc_id=..., output_format="json")` for the v2 machine contract |
| `parse_pdf_structure(pdf_path, ...)` | `document(op="parse", pdf_path=..., ...)` |
| `list_documents()` | `document(op="list")` |
| `delete_document(doc_id)` | `document(op="delete", doc_id=...)` |
| `inspect_document_manifest(doc_id)` | `document(op="inspect", doc_id=...)` |
| `export_document_segmentation(doc_id, ...)` | `document(op="export_segmentation", doc_id=..., ...)` |
| Portable agent/Foam asset handoff | `document(op="export_assets", doc_id=..., output_dir=...)` (`agent_assets` alias) |
| `visualize_document_layout(doc_id, ...)` | `document(op="visualize_layout", doc_id=..., ...)` |
| `ocr_pdf_document(pdf_path, ...)` | `document(op="ocr", pdf_path=..., ...)` |
| `fetch_document_asset(doc_id, asset_type, asset_id, ...)` | `document_asset(op="get", doc_id=..., asset_type=..., asset_id=...)` |
| `search_source_location(doc_id, query, ...)` | `evidence(op="locate", doc_id=..., query=...)` |
| `convert_pdf_to_docx(doc_id, ...)` | `convert_document(source=doc_id, source_format="pdf", target_format="docx", ...)` |
| `convert_pdf_to_pptx(doc_id, ...)` | `convert_document(source=doc_id, source_format="pdf", target_format="pptx", ...)` |

### Citation Evidence Tools

| Legacy direct tool | Target |
|---|---|
| `find_evidence_spans(doc_id, ...)` | `evidence(op="find", doc_id=..., ...)` |
| `verify_citation_ref(ref)` | `evidence(op="verify", ref=...)` |
| `citation_bundle(doc_id, ...)` | `evidence(op="bundle", doc_id=..., ...)` |

### DOCX / DFM Tools

| Legacy direct tool | Target |
|---|---|
| `ingest_docx(file_path)` | `docx(op="ingest", file_path=...)` |
| `get_docx_content(doc_id, block_id)` | `docx(op="get", doc_id=..., block_id=...)` or `docx(op="read", ...)` |
| `save_docx(doc_id, dfm_content, ...)` | `docx(op="save", doc_id=..., dfm_content=..., ...)` |
| `list_docx_documents()` | `docx(op="list")` |
| `list_docx_blocks(doc_id)` | `docx(op="list_blocks", doc_id=...)` |
| `delete_docx(doc_id)` | `docx(op="delete", doc_id=...)` |
| `docx_validate_roundtrip(doc_id, ...)` | `docx(op="validate", doc_id=..., ...)` |
| `convert_docx_to_doc(doc_id, ...)` | `convert_document(source=doc_id, source_format="docx", target_format="doc", ...)` |
| `convert_docx_to_pdf(doc_id, ...)` | `convert_document(source=doc_id, source_format="docx", target_format="pdf", ...)` |
| `convert_docx_to_odt(doc_id, ...)` | `convert_document(source=doc_id, source_format="docx", target_format="odt", ...)` |
| `export_markdown(...)` | `convert_document(source=..., source_format="md", target_format=..., ...)` |

### DOCX Table / Chart / Edit Plan Tools

| Legacy direct tool | Target |
|---|---|
| `docx_table_to_context(doc_id, block_id, register)` | `docx_table(op="to_context", doc_id=..., block_id=..., register=...)` |
| `docx_table_from_context(doc_id, block_id, table_id, save_dfm)` | `docx_table(op="from_context", doc_id=..., block_id=..., table_id=..., save_dfm=...)` |
| `docx_chart_data(doc_id, block_id, register)` | `docx_table(op="chart_data", doc_id=..., block_id=..., register=...)` |
| `docx_table_edit_plan(doc_id, block_id, ...)` | `docx_table(op="edit_plan", doc_id=..., block_id=..., ...)` |

### Knowledge Graph Tools

| Legacy direct tool | Target |
|---|---|
| `consult_knowledge_graph(query, ...)` | `knowledge(op="consult", query=..., ...)` or `knowledge(op="query", ...)` |
| `export_knowledge_graph(format, limit)` | `knowledge(op="export", format=..., limit=...)` |

## Runtime Implementation

- Tool decorators register the full compatibility inventory on the official
  SDK 2 `MCPServer`; there is no SDK v1/FastMCP fallback path.
- `src.presentation.server` imports all tools/resources first, then applies
  `src.presentation.tool_surface.apply_tool_surface_policy(mcp)`.
- `AssetAwareMCPServer` tracks registrations through the public `add_tool` API;
  surface filtering uses public `remove_tool`, and diagnostics/tests enumerate
  through public `list_tools`. Private registry internals are not a contract.
- Surface switching is import-time and filters MCPServer's public registry, so
  tests for different surfaces must run in subprocesses.
- MCP SDK 2 `Context` parameters are runtime-injected. They may drive bounded
  progress calls but must never appear in public tool input schemas;
  operational logs use Python logging on stderr instead of protocol logging.
- `asset-aware-mcp list-tools --json` reports `surface`, `count`, and `tools`.

## Compatibility Rules

- Do not change return formats just because a call moved behind `op=`.
- Preserve source identity, span IDs, locator metadata, hashes, context text, and
  CRAAP scaffold for citation-related operations.
- Preserve DOCX stale source checks, round-trip validation gates, and Track
  Changes behavior.
- Preserve background job async defaults, status semantics, cancellation, and
  artifact reporting.
- Keep legacy mode available while bundled VSIX/Cline/Codex/Copilot harnesses
  and user allow-lists migrate; this promise covers tool UX only, not SDK v1.

## Verification Requirements

- `tests/unit/test_mcp_server_startup.py` must prove balanced=30, compact=17,
  and legacy/direct compatibility is still available.
- `tests/test_mcp_tools.py` must exercise the registered MCPServer/client path
  and prove runtime `Context` never leaks into any public input schema.
- Direct-vs-facade parity tests must cover section, document OCR/layout/export,
  DOCX, job, evidence, conversion, and A2T paths before removing any legacy path.
- `scripts/count_tools.sh` and `scripts/count_tools.ps1` must report both public
  runtime count and decorator inventory.
- Docs metrics should use the balanced public count; compatibility notes may
  mention legacy inventory separately.
