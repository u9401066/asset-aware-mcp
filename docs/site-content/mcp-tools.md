<!-- Generated from MCP-Tools.md by scripts/build_docs_site.py -->

# MCP Tools

![MCP endpoint distribution](wiki/assets/mcp-endpoint-map.jpg)

Tool consolidation is planned but not yet applied to the default public surface.
See [MCP Tool Consolidation Plan](#/mcp-tool-consolidation) for the 17-tool
target and legacy direct-tool mapping.

如果你不是在查完整參數，先從 [Tool Chooser](#/tool-chooser) 依任務選入口，再回到本頁查
精確 tool contract。

工具數量由 `./scripts/count_tools.sh` 產生：62 tools in 7 modules。下列為目前公開 MCP tool surface，來源為 `src/presentation/tools/**`。

## `document_tools.py` - 19 tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `parse_pdf_structure` | `pdf_path`, `output_dir`, `async_mode`, OCR/Marker/page options | 建立 background Marker parse job；目前 Marker security hold 時會 fail closed 並給出診斷 |
| `search_source_location` | `doc_id`, `query`, `block_types` | 搜尋文件來源位置，回傳 page/bbox/block context |
| `find_evidence_spans` | `doc_id`, `query`, `span_id`, `span_kinds`, `limit` | 搜尋 citation-ready evidence spans |
| `verify_citation_ref` | `ref` | 驗證 AssetRef 是否仍符合 citation index 與 locator/hash |
| `citation_bundle` | `doc_id`, query/span filters, `include_verification`, `output_format`, `citation_key`, Foam write options | 匯出 verified evidence bundle，包含 AssetRef、quote/hash、locator、context、CRAAP 與 verification；`output_format="foam"` 產生 Foam evidence pack，可用 `wiki_root` 寫檔並更新 index |
| `ingest_documents` | `file_paths`, `async_mode`, `use_marker`, OCR/Marker/page options | 攝入 PDF，建立 manifest、markdown、blocks、assets、citation artifacts |
| `list_documents` | 無 | 列出已處理文件摘要 |
| `delete_document` | `doc_id` | 刪除 PDF 文件 artifacts |
| `convert_pdf_to_docx` | `doc_id`, `output_path`, `mode`, `async_mode` | 建立 background conversion job，將已攝入 PDF 轉 DOCX；`async_mode=false` 可同步執行 |
| `convert_pdf_to_pptx` | `doc_id`, `output_path`, `mode`, `async_mode` | 建立 background conversion job，將已攝入 PDF 轉 PPTX；`async_mode=false` 可同步執行 |
| `inspect_document_manifest` | `doc_id` | 檢視 manifest 詳細資訊 |
| `export_document_segmentation` | `doc_id`, `page`, `limit`, `output_path` | 匯出 segmentation schema |
| `visualize_document_layout` | `doc_id`, `page`, label/order/output options | 產生 PDF layout overlay |
| `ocr_pdf_document` | `pdf_path`, `output_path`, OCR options | 建立 background OCR ingest job |
| `fetch_document_asset` | `doc_id`, `asset_type`, `asset_id`, `max_size` | 依 asset identity 擷取 table/figure/section/full_text |
| `document` | `op`, PDF ingest/parse/list/delete/inspect parameters | Consolidated PDF document entrypoint；conversion 請用 `convert_document` |
| `document_asset` | `op`, `doc_id`, asset/section parameters, Foam note options | Consolidated asset and section entrypoint；section search 是章節導覽，source locator 請用 `search_source_location` 或 `evidence(op="locate")`；`op="foam_notes"` 可將 table/figure 寫成 Foam notes |
| `evidence` | `op`, `doc_id`, query/span/ref parameters, `output_format`, `citation_key`, `wiki_root` | Consolidated citation evidence entrypoint，支援 `find` / `verify` / `bundle` / `claim_promotion` / `health` / `locate`；bundle 可輸出/寫入 Foam evidence pack，claim promotion 會強制 verify 後才允許寫 Foam，health 可掃 wiki citation drift |
| `convert_document` | `source`, `target_format`, `source_format`, `output_path`, `mode`, `md_text`, `async_mode` | Consolidated conversion entrypoint；預設建立 background conversion job |

Operation notes:

- `document` accepts `ingest` / `import`, `parse`, `list`, `delete`, and `inspect`; PDF/DOCX/Markdown conversions live behind `convert_document`.
- `document_asset` accepts asset fetch plus section tree/detail/blocks/search operations; `foam_notes` writes table/figure asset notes and updates the managed asset index block. Source locator search stays in `search_source_location` / `evidence(op="locate")`.
- `evidence` accepts `find`, `verify`, `bundle`, `health`, and `locate` / `search_location`; the old `search` wording is avoided because the code routes citation lookup through `find`.
- PDF ingest、Marker parse、OCR 與 conversion requests 都可 job-backed；conversion tools 預設 `async_mode=true`，大型 LibreOffice/PDF conversion 不會卡住 MCP request path。`parse_pdf_structure(output_dir=...)` and `ocr_pdf_document(output_path=...)` still accept compatibility parameters, but background job mode owns the final artifact paths.

## `docx_tools.py` - 17 tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `ingest_docx` | `file_path` | 攝入 `.docx` / `.docm`，或透過 LibreOffice 轉換 `.doc` / `.odt` / `.ods` 後轉為 DocxIR + DFM |
| `get_docx_content` | `doc_id`, `block_id` | 讀取完整 DFM 或單一 block；單一 block payload 會包含 DOCX locator metadata |
| `save_docx` | `doc_id`, `dfm_content`, `output_path`, `from_md`, `force`, `track_changes`, `revision_author` | 將 DFM/Markdown 寫回 DOCX |
| `list_docx_blocks` | `doc_id` | 列出 DOCX block 摘要與 compact DOCX locator |
| `list_docx_documents` | 無 | 列出已攝入 DOCX/DFM 文件 |
| `delete_docx` | `doc_id` | 刪除 DOCX/DFM artifacts |
| `convert_docx_to_doc` | `doc_id`, `output_path`, `mode`, `async_mode` | 建立 background conversion job，轉為 legacy DOC |
| `convert_docx_to_pdf` | `doc_id`, `output_path`, `mode`, `async_mode` | 建立 background conversion job，轉為 PDF |
| `convert_docx_to_odt` | `doc_id`, `output_path`, `mode`, `async_mode` | 建立 background conversion job，轉為 ODT |
| `docx_validate_roundtrip` | `doc_id`, `output_path`, `strict` | 驗證 DOCX -> DFM -> DOCX round trip |
| `docx` | `op`, DOCX/DFM parameters | Consolidated DOCX/DFM entrypoint |
| `docx_table_to_context` | `doc_id`, `block_id`, `register` | 將 DOCX 表格轉為 A2T TableContext |
| `docx_table_from_context` | `doc_id`, `block_id`, `table_id`, `save_dfm` | 將 TableContext 寫回 DFM 表格 |
| `docx_chart_data` | `doc_id`, `block_id`, `register` | 擷取 DOCX 圖表底層資料 |
| `docx_table_edit_plan` | `doc_id`, `block_id`, `table_id`, `target_columns`, `target_rows` | 預覽 table write-back 的 cell/row/column/header 變更與結構風險 |
| `docx_table` | `op`, table bridge parameters | Consolidated DOCX table bridge entrypoint，支援 `edit_plan` |
| `export_markdown` | `md_text`, `md_path`, `output_path`, `output_format`, `async_mode` | Markdown 直接匯出 DOCX/PDF/DOC/ODT；預設建立 conversion job |

## `job_tools.py` - 4 tools

| Tool | 功能 |
|---|---|
| `get_job_status` | 查詢 ETL/background job 狀態、進度、warnings、artifacts |
| `list_jobs` | 列出 active/all jobs |
| `cancel_job` | 取消 running job |
| `job` | Consolidated get/list/cancel entrypoint |

## `knowledge_tools.py` - 3 tools

| Tool | 功能 |
|---|---|
| `consult_knowledge_graph` | 查詢 LightRAG knowledge graph；可用 `verify_references=true` 附上 verified citation bundle |
| `export_knowledge_graph` | 匯出 graph 給視覺化或外部分析 |
| `knowledge` | Consolidated knowledge graph entrypoint |

## `profile_tools.py` - 7 tools

| Tool | 功能 |
|---|---|
| `list_etl_profiles` | 列出內建與已載入 ETL profiles |
| `get_etl_profile` | 取得指定 profile 詳細設定 |
| `get_current_etl_profile` | 查詢目前 active profile |
| `set_etl_profile` | 切換 active profile |
| `load_etl_profile_from_json` | 從 JSON 載入自訂 profile |
| `detect_etl_profile` | 從 PDF / doc_id / sample_text 偵測建議 profile，可選 `activate=true` |
| `etl_profile` | Consolidated profile entrypoint，支援 `detect` / `auto_detect` |

## `section_tools.py` - 5 tools

| Tool | 功能 |
|---|---|
| `list_section_tree` | 列出動態 section tree |
| `get_section_detail` | 取得 section metadata |
| `get_section_blocks` | 取得 section 內 blocks，支援 children/filter/limit |
| `search_sections` | 搜尋 section name |
| `get_section_content` | 讀取 section-level 快取內容 |

## `table_tools.py` - 7 tools

| Tool | 功能 |
|---|---|
| `plan_table` | Schema 設計、模板查詢、模板建表 |
| `table_manage` | 建立、刪除、列表、預覽、渲染、schema 演進 |
| `table_data` | 新增/讀取/更新/刪除 rows 和 cells |
| `table_cite` | cell-level citation refs 管理 |
| `table_history` | 變更紀錄、token 估算 |
| `table_draft` | draft 建立、更新、加資料、恢復、提交；operation 名稱為 `resume` |
| `discover_sources` | 跨文件搜尋可用於表格的來源 |
