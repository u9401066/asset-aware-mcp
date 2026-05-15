# MCP Tool Consolidation Plan

本文件是下一輪 MCP tool surface 整併規格。它描述目標狀態，不代表目前
`origin/master` 已經只註冊 17 個 tools；目前公開 reference 仍以
[MCP Tools](MCP-Tools) 和 `asset-aware-mcp list-tools --json` 為準。

## 目標

把目前約 62 個公開 MCP tools 收斂成約 17 個預設公開 tools，功能基本不砍，只把
legacy direct tools 收進 operation-based entrypoints：

- 讓 agent 優先看到少量、穩定、task-oriented 的入口。
- 保留既有功能、參數語意、輸出格式與 fail-closed citation 行為。
- 在相容期內讓舊 client 可以用 legacy direct tool 名稱。
- 上線前以 direct-vs-op parity tests 和 stdio smoke 驗證沒有功能遺失。

Non-goals：

- 不移除 citation locator、AssetRef、hash、line/page/bbox metadata。
- 不改 resource URI surface；13 個 MCP resources 先維持原樣。
- 不把 KG/LightRAG 變成必要功能；KG 仍是 optional。

## 目標 17 Tools

| Target tool | 狀態 | 收納範圍 |
|---|---|---|
| `document` | 已存在，需擴充 | PDF ingest/list/delete/inspect/parse/OCR/layout/segmentation |
| `document_asset` | 已存在，需縮窄/保留 | asset fetch、asset Foam notes、asset index 更新 |
| `evidence` | 已存在，需維持 | citation span find/verify/bundle/locate/claim promotion/wiki health |
| `convert_document` | 已存在，需維持 | PDF/DOCX/Markdown conversion |
| `docx` | 已存在，需維持 | DOCX/DFM ingest/read/save/list/delete/blocks/validation |
| `docx_table` | 已存在，需維持 | DOCX table/chart extraction、write-back、edit plan |
| `job` | 已存在，需維持 | background job get/list/cancel |
| `knowledge` | 已存在，需維持 | KG consult/export |
| `etl_profile` | 已存在，需維持 | ETL profile list/get/current/set/load/detect |
| `section` | 新增 | section tree/detail/blocks/search/content |
| `plan_table` | 已存在 | A2T schema/template planning |
| `table_manage` | 已存在 | A2T create/delete/list/preview/resume/render/schema ops |
| `table_data` | 已存在 | A2T row/cell read-write ops |
| `table_cite` | 已存在 | A2T cell citation ops |
| `table_history` | 已存在 | A2T audit/history/token ops |
| `table_draft` | 已存在 | A2T draft create/update/resume/commit/list/delete |
| `discover_sources` | 已存在 | A2T source discovery |

Count math：10 consolidated non-table tools + 7 A2T table tools = 17 public tools.

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

新增 `section(op=...)`，並把 direct section tools 從預設公開 surface 收進來。
`document_asset` 可以在相容期保留 section forwarding，但新文件與 agent harness 應改用
`section`。

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
| `ingest_documents(file_paths, ...)` | `document(op="ingest", file_paths=..., ...)` |
| `parse_pdf_structure(pdf_path, ...)` | `document(op="parse", pdf_path=..., ...)` |
| `list_documents()` | `document(op="list")` |
| `delete_document(doc_id)` | `document(op="delete", doc_id=...)` |
| `inspect_document_manifest(doc_id)` | `document(op="inspect", doc_id=...)` |
| `export_document_segmentation(doc_id, ...)` | add `document(op="export_segmentation", doc_id=..., ...)` |
| `visualize_document_layout(doc_id, ...)` | add `document(op="visualize_layout", doc_id=..., ...)` |
| `ocr_pdf_document(pdf_path, ...)` | add `document(op="ocr", pdf_path=..., ...)` |
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

### A2T Table Tools

A2T table tools are already operation-based and should stay public in the 17-tool
surface:

- `plan_table`
- `table_manage`
- `table_data`
- `table_cite`
- `table_history`
- `table_draft`
- `discover_sources`

## Rollout Plan

1. **Document-only phase**
   - Land this plan without changing runtime behavior.
   - Keep `MCP-Tools.md` and endpoint metrics on the actual 62-tool state.

2. **Parity phase**
   - Add `section(op=...)`.
   - Extend `document(op=...)` to cover segmentation, layout visualization, and OCR.
   - Ensure every legacy direct tool has an op-based target.
   - Add direct-vs-op parity tests for every mapping above.

3. **Compatibility phase**
   - Keep legacy direct tools registered by default for one release if needed.
   - Mark direct tools as deprecated in docstrings/descriptions and docs.
   - Update Cline/Codex/Copilot harness examples to prefer op tools.

4. **Default-shrink phase**
   - Default public MCP surface becomes the 17 target tools.
   - Legacy direct tools become opt-in via a compatibility flag, for example
     `ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS=true`.
   - `asset-aware-mcp list-tools --json`, docs metrics, and VSIX smoke tests must
     assert the new default count.

5. **Removal decision**
   - After telemetry/manual release checks confirm no bundled harness uses direct
     names, decide whether to keep the compatibility flag or remove legacy
     registration in a later breaking release.

## Test Requirements

Required before changing the default public tool count:

- Unit parity tests:
  - `job`: get/list/cancel output parity.
  - `etl_profile`: list/get/current/set/load/detect parity.
  - `section`: tree/detail/blocks/search/content parity.
  - `document`: ingest/list/delete/inspect/parse/export_segmentation/visualize_layout/OCR parity.
  - `evidence`: find/verify/bundle/locate parity, including fail-closed locator/hash behavior.
  - `docx`: ingest/read/save/list/delete/list_blocks/validate parity.
  - `docx_table`: to_context/from_context/chart_data/edit_plan parity.
  - `convert_document`: PDF/DOCX/Markdown conversion routing parity.
- MCP registration tests:
  - Default mode lists exactly the 17 target tools.
  - Legacy compatibility flag lists the legacy direct tools too.
  - Required tools in stdio smoke use op-based names, not removed direct names.
- Docs tests:
  - `MCP-Tools.md` matches actual registered default tools after shrink.
  - Endpoint metrics update from 62 tools to 17 tools only after runtime changes land.
- Extension/package tests:
  - VSIX package contents still include assistant harness assets.
  - Cline/Codex/Copilot install flows do not hard-code removed direct tool names.

## Compatibility Rules

- Do not change return formats just because a call moved behind `op=`.
- Keep parameter aliases where current wrappers already accept them, such as
  `ingest/import`, `get/read/content`, `validate/validate_roundtrip`, and
  `consult/query`.
- For citation-related operations, preserve source identity, span IDs, locator
  metadata, hashes, context text, and CRAAP scaffold.
- For DOCX writes, keep stale source checks and strict round-trip validation gates.
- For background jobs, preserve async defaults and cancellation/status semantics.

## Example Before / After

```text
# Before
get_job_status(job_id="job_123")
list_section_tree(doc_id="doc_abc", format="tree")
find_evidence_spans(doc_id="doc_abc", query="primary outcome")
docx_table_edit_plan(doc_id="docx_1", block_id="t001", table_id="tbl_1")

# After
job(op="get", job_id="job_123")
section(op="tree", doc_id="doc_abc", format="tree")
evidence(op="find", doc_id="doc_abc", query="primary outcome")
docx_table(op="edit_plan", doc_id="docx_1", block_id="t001", table_id="tbl_1")
```
