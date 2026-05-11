<!-- Generated from MCP-Tools.md by scripts/build_docs_site.py -->

# MCP Tools

![MCP endpoint distribution](wiki/assets/mcp-endpoint-map.jpg)

工具數量由 `./scripts/count_tools.sh` 產生：59 tools in 7 modules。下列為目前公開 MCP tool surface，來源為 `src/presentation/tools/**`。

## `document_tools.py` - 18 tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `parse_pdf_structure` | `pdf_path`, `output_dir`, `async_mode`, OCR/Marker/page options | 建立 background Marker parse job；目前 Marker security hold 時會 fail closed 並給出診斷 |
| `search_source_location` | `doc_id`, `query`, `block_types` | 搜尋文件來源位置，回傳 page/bbox/block context |
| `find_evidence_spans` | `doc_id`, `query`, `span_id`, `span_kinds`, `limit` | 搜尋 citation-ready evidence spans |
| `verify_citation_ref` | `ref` | 驗證 AssetRef 是否仍符合 citation index 與 locator/hash |
| `ingest_documents` | `file_paths`, `async_mode`, `use_marker`, OCR/Marker/page options | 攝入 PDF，建立 manifest、markdown、blocks、assets、citation artifacts |
| `list_documents` | 無 | 列出已處理文件摘要 |
| `delete_document` | `doc_id` | 刪除 PDF 文件 artifacts |
| `convert_pdf_to_docx` | `doc_id`, `output_path`, `mode` | 將已攝入 PDF 轉 DOCX |
| `convert_pdf_to_pptx` | `doc_id`, `output_path`, `mode` | 將已攝入 PDF 轉 PPTX |
| `inspect_document_manifest` | `doc_id` | 檢視 manifest 詳細資訊 |
| `export_document_segmentation` | `doc_id`, `page`, `limit`, `output_path` | 匯出 segmentation schema |
| `visualize_document_layout` | `doc_id`, `page`, label/order/output options | 產生 PDF layout overlay |
| `ocr_pdf_document` | `pdf_path`, `output_path`, OCR options | 建立 background OCR ingest job |
| `fetch_document_asset` | `doc_id`, `asset_type`, `asset_id`, `max_size` | 依 asset identity 擷取 section/table/figure/text |
| `document` | `op`, document ingest/parse/list/delete/convert parameters | Consolidated PDF document entrypoint |
| `document_asset` | `op`, `doc_id`, asset/search/section parameters | Consolidated asset and section entrypoint |
| `evidence` | `op`, `doc_id`, query/span/ref parameters | Consolidated citation evidence entrypoint |
| `convert_document` | `source`, `target_format`, `source_format`, `output_path`, `mode`, `md_text` | Consolidated conversion entrypoint |

## `docx_tools.py` - 16 tools

| Tool | 主要參數 | 功能 |
|---|---|---|
| `ingest_docx` | `file_path` | 攝入 `.docx` / `.doc`，轉為 DocxIR + DFM |
| `get_docx_content` | `doc_id`, `block_id` | 讀取完整 DFM 或單一 block |
| `save_docx` | `doc_id`, `dfm_content`, `output_path`, `from_md`, `force`, `track_changes`, `revision_author` | 將 DFM/Markdown 寫回 DOCX |
| `list_docx_blocks` | `doc_id` | 列出 DOCX block 摘要 |
| `list_docx_documents` | 無 | 列出已攝入 DOCX/DFM 文件 |
| `delete_docx` | `doc_id` | 刪除 DOCX/DFM artifacts |
| `convert_docx_to_doc` | `doc_id`, `output_path`, `mode` | 轉為 legacy DOC |
| `convert_docx_to_pdf` | `doc_id`, `output_path`, `mode` | 轉為 PDF |
| `convert_docx_to_odt` | `doc_id`, `output_path`, `mode` | 轉為 ODT |
| `docx_validate_roundtrip` | `doc_id`, `output_path`, `strict` | 驗證 DOCX -> DFM -> DOCX round trip |
| `docx` | `op`, DOCX/DFM parameters | Consolidated DOCX/DFM entrypoint |
| `docx_table_to_context` | `doc_id`, `block_id`, `register` | 將 DOCX 表格轉為 A2T TableContext |
| `docx_table_from_context` | `doc_id`, `block_id`, `table_id`, `save_dfm` | 將 TableContext 寫回 DFM 表格 |
| `docx_chart_data` | `doc_id`, `block_id`, `register` | 擷取 DOCX 圖表底層資料 |
| `docx_table` | `op`, table bridge parameters | Consolidated DOCX table bridge entrypoint |
| `export_markdown` | `md_text`, `md_path`, `output_path`, `output_format` | Markdown 直接匯出 DOCX/PDF/DOC |

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
| `consult_knowledge_graph` | 查詢 LightRAG knowledge graph |
| `export_knowledge_graph` | 匯出 graph 給視覺化或外部分析 |
| `knowledge` | Consolidated knowledge graph entrypoint |

## `profile_tools.py` - 6 tools

| Tool | 功能 |
|---|---|
| `list_etl_profiles` | 列出內建與已載入 ETL profiles |
| `get_etl_profile` | 取得指定 profile 詳細設定 |
| `get_current_etl_profile` | 查詢目前 active profile |
| `set_etl_profile` | 切換 active profile |
| `load_etl_profile_from_json` | 從 JSON 載入自訂 profile |
| `etl_profile` | Consolidated profile entrypoint |

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
| `table_draft` | draft 建立、更新、加資料、恢復、提交 |
| `discover_sources` | 跨文件搜尋可用於表格的來源 |
