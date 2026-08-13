# MCP Tools

預設 runtime surface 是 **balanced**：30 個公開 tools。這是 Cline、Codex、
Copilot 的一般建議模式，保留完整 facade 入口，也保留少數高頻、直覺且安全的
shortcut direct tools。若只想讓 agent 面對最小入口，可設定
`ASSET_AWARE_MCP_TOOL_SURFACE=compact` 使用 17 個 facade tools；若舊 client 仍依賴
direct tool 名稱，可設定 `ASSET_AWARE_MCP_TOOL_SURFACE=legacy` 或
`ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS=true` 暫時公開完整 legacy inventory。

所有 surface 都執行在官方 MCP Python SDK 2 `MCPServer`（`mcp>=2,<3`）上。
SDK v1 不受支援且沒有 FastMCP/v1 fallback；此處的 `legacy` 僅指 direct tool
名稱與既有 allow-list 的 UX 相容。Tool 的 `Context` 由 server 在 runtime 注入，
不屬於 client input schema；測試會 fail closed 防止 `ctx` 欄位洩漏。

工具數量請以 runtime 為準：

```bash
uv run asset-aware-mcp list-tools --json
./scripts/count_tools.sh
```

`list-tools` 會顯示預設 public surface；count script 會同時列出預設 public tools
與 decorator inventory，避免把 legacy 庫存誤認為 agent 實際可見的工具數。

## `document_tools.py` - 11 public tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `parse_pdf_structure` | `pdf_path`, `output_dir`, `async_mode`, OCR/structured/page options | Configured structured PDF parse shortcut；Docling 可用，held／缺少 backend 時 fail closed 並給診斷。 |
| `find_evidence_spans` | `doc_id`, `query`, `span_id`, `span_kinds`, `limit` | 搜尋 evidence spans；短 quote 可 inline canonical AssetRef，超過 1,000 字元時只回不可驗證的 bounded preview，完整 ref 請匯出 persisted bundle。 |
| `verify_citation_ref` | `ref` | 驗證 AssetRef 是否仍符合 citation index 與 locator/hash。 |
| `citation_bundle` | `doc_id`, query/span filters, `output_format`, Foam write options | 匯出 verified evidence bundle，可產生 Markdown/JSON/Foam evidence pack。 |
| `ingest_documents` | `file_paths`, `async_mode`, `use_marker`, OCR/Marker/page options | 攝入 PDF，建立 manifest、markdown、blocks、assets、citation artifacts。 |
| `list_documents` | 無 | 列出已處理 PDF 文件摘要。 |
| `fetch_document_asset` | `doc_id`, `asset_type`, `asset_id`, `max_size`, `max_chars` | 依 asset identity 讀取 table/figure/section/full text。 |
| `document` | `op`, PDF path/document/output/ingest/OCR/layout/audit/retrieval parameters | PDF document facade；除 ingest/readiness/audit/retrieval 外，也支援 read-only `preflight` 與 citation-ready `export_assets` agent/Foam bundle。完整 ops 見下方。 |
| `document_asset` | `op`, `doc_id`, asset/section/Foam note parameters | Asset facade；支援 asset fetch、section forwarding、asset Foam notes。 |
| `evidence` | `op`, `doc_id`, query/span/ref parameters, Foam options | Evidence facade；支援 `find`, `verify`, `bundle`, `locate`, `claim_promotion`, `health`。 |
| `convert_document` | `source`, `target_format`, `source_format`, `output_path`, `mode`, `async_mode` | PDF/DOCX/Markdown conversion facade；大型 conversion 預設 job-backed。 |

## `docx_tools.py` - 6 public tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `ingest_docx` | `file_path` | 攝入 `.docx` / `.docm`，也可經 LibreOffice 轉入 `.doc` / `.odt` / `.ods`。 |
| `get_docx_content` | `doc_id`, `block_id` | 讀取 DFM/DOCX 內容或單一 block，保留 locator metadata。 |
| `save_docx` | `doc_id`, `dfm_content`, `output_path`, `force`, Track Changes options | 將 DFM/Markdown 寫回 DOCX，保留 stale source 與 validation guard。 |
| `docx` | `op`, DOCX/DFM parameters | DOCX facade；支援 ingest/read/save/list/delete/list_blocks/validate。 |
| `docx_table_edit_plan` | `doc_id`, `block_id`, `table_id`, target shape options | 先產生 table write-back 風險計畫，再進行 A2T/DOCX table 操作。 |
| `docx_table` | `op`, DOCX table/chart bridge parameters | DOCX table facade；支援 `to_context`, `from_context`, `chart_data`, `edit_plan`。 |

## `job_tools.py` - 3 public tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `get_job_status` | `job_id` | 查詢 background job 狀態、progress、warnings、artifacts。 |
| `list_jobs` | `active_only` | 列出 active 或全部 jobs。 |
| `job` | `op`, `job_id`, `active_only` | Job facade；支援 `get/status`, `list`, `cancel`。 |

## `knowledge_tools.py` - 1 public tool

| Tool | 主要參數 | 功能 |
|---|---|---|
| `knowledge` | `op`, query/export parameters | Knowledge graph facade；支援 `consult/query` 與 `export`。KG 是 opt-in discovery layer，citation-ready 結論仍回到 evidence bundle。 |

## `profile_tools.py` - 1 public tool

| Tool | 主要參數 | 功能 |
|---|---|---|
| `etl_profile` | `op`, profile parameters | ETL profile facade；支援 list/get/current/set/load/detect。 |

## `section_tools.py` - 1 public tool

| Tool | 主要參數 | 功能 |
|---|---|---|
| `section` | `op`, `doc_id`, `path`, `section_id`, `query`, filters | Section facade；支援 `tree/list`, `detail`, `blocks/list_blocks`, `search`, `content`。 |

## `table_tools.py` - 7 public tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `plan_table` | schema/template/source planning parameters | A2T schema 與 table template planning。 |
| `table_manage` | `op`, table/schema/render parameters | 建立、刪除、列出、preview、resume、render、schema 操作。 |
| `table_data` | `op`, row/cell/filter parameters | A2T row/cell read-write operations。 |
| `table_cite` | table/cell citation parameters | 維護 cell-level citation refs。 |
| `table_history` | table/history/token parameters | 讀取 audit trail、history 與 token usage。 |
| `table_draft` | `op`, draft/table parameters | Draft create/update/resume/commit/list/delete。 |
| `discover_sources` | document/source discovery parameters | 探索可轉成 A2T 表格的文件來源。 |

## Compatibility Notes

- `compact` surface 只公開 17 個 operation-based facade tools。
- `balanced` surface 在 `compact` 之外多保留 13 個高頻 shortcuts，總數 30。
- `legacy` surface 會公開完整 decorator inventory，目前為 63 tools；這是 SDK 2
  內的 tool-name 相容模式，不是 SDK v1 protocol compatibility，也不是建議給
  agent 的預設工具面。
- Facade 轉接不得改變 citation locator、AssetRef、hash、line/page/bbox metadata、DOCX stale source guard 或 background job semantics。

### Document Inspection, Audit, And Asset Ops

The OpenDataloader-inspired PDF audit features stay inside the existing `document` facade, so the balanced public tool count remains 30:

- `document(op="preflight", pdf_path="...")` performs a read-only,
  process-isolated PDF inspection before ingest. Its stable `pdf-preflight-v1`
  response preserves source SHA-256 and page/bbox provenance, classifies every
  page, and reports OCR pages plus the recommended extraction route. Invalid,
  encrypted, oversized, over-page-limit, changed, or timed-out inputs return a
  stable error payload rather than partially ingesting the source.
- `document(op="auto", file_paths=[...])` starts the normal ingest/background job flow. `document(op="auto", doc_id="...")` returns the AI readiness state for an existing document.
- `document(op="prepare_ai", doc_id="...", output_format="json")` returns the v2 readiness contract with `status`, `blockers`, `warnings`, `capabilities`, `artifacts`, `missing_audits`, `invalid_audits`, `audit_artifacts`, and `next_actions`. The default Markdown response embeds the same JSON for humans.
- `document(op="audit", doc_id="...")` reuses current safety/native/coverage/accessibility artifacts by default and reports them as cached only when they are present and valid. Pass `refresh=true` to rebuild all four diagnostics.
- `document(op="safety_audit", doc_id="...", output_path=...)` writes `ai_safety_report.json`.
- `document(op="native_structure", doc_id="...", output_path=...)` writes `native_structure.json`.
- `document(op="coverage", doc_id="...", output_path=...)` writes `segmentation_coverage.json`.
- `document(op="accessibility", doc_id="...", output_path=...)` writes `accessibility_report.json`, focused on captions, sectioning, line spans, asset links, and reading-order readiness rather than PDF/UA certification.
- `document(op="pointer_index", doc_id="...")` writes `section_pointer_index.jsonl`, a deterministic section proxy index with breadcrumbs, page/line/char/byte locators, source hashes, asset ids, and evidence-span ids.
- `document(op="structural_retrieve", doc_id="...", query="...")` searches an existing valid pointer index and materializes bounded section previews. Use `document(op="pointer_index")` or `refresh=true` when the index is missing or stale.
- `document(op="compare", doc_id="...", doc_b_id="...", criteria="...")` writes a deterministic structural comparison bundle for review before claims are promoted.
- `document(op="export_assets", doc_id="...", output_dir="agent-assets")`
  (alias `agent_assets`) writes `agent-asset-bundle-v1`: `manifest.json`,
  agent-readable `assets.jsonl`, a Foam `index.md`, per-asset `notes/**`, and
  copied figure `media/**`. Each text/table/figure record carries stable source
  identity, content/record hashes, locators, AssetRef/evidence refs, and a Foam
  wikilink; replacement is restricted to a matching managed bundle.

Preflight is read-only; audit/retrieval ops are artifact-only diagnostics; asset
export writes only a managed child bundle and never mutates the source document,
citation spans, AssetRefs, or table/document write-back state. Readiness and
job-status artifact discovery are read-only and do not create document
directories. `list_documents`, `inspect_document_manifest`, and `get_job_status`
surface `document(op="prepare_ai", ...)` / `document(op="audit", ...)` next
actions so agents do not have to memorize the individual audit ops.
