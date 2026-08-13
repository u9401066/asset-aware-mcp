<!-- Generated from Tool-Chooser.md by scripts/build_docs_site.py -->

# Tool Chooser

這頁幫你從任務選 MCP 入口。完整參數仍以 [MCP Tools](#/mcp-tools) 和
[MCP Resources](#/mcp-resources) 為準。

## 常見任務

| 任務 | 建議入口 | 何時看 reference |
|---|---|---|
| 攝入 PDF | `document(op="ingest")` / `ingest_documents` | 需要舊 allow-list 時可用 shortcut `ingest_documents` |
| Configured structured parse | `document(op="parse")` / `parse_pdf_structure` | 需要 backend diagnostic 時查 PDF workflow |
| OCR PDF | `document(op="ocr")` | 長任務 artifact path 查 Background Jobs |
| 看章節樹 | `section(op="tree")` / `document_asset(op="tree")` | 需要 resource URI 時查 MCP Resources |
| 找可引用 span | `evidence(op="find")` / `find_evidence_spans` | source locator 搜尋用 `evidence(op="locate")` |
| 驗證 AssetRef | `evidence(op="verify")` / `verify_citation_ref` | promotion 或 wiki drift 檢查 |
| 寫 Foam evidence pack | `evidence(op="bundle")` / `citation_bundle` | 詳細格式查 LLM Wiki |
| 寫 table/figure note | `document_asset(op="foam_notes")` | asset note drift 用 `evidence(op="health")` |
| 建立 KG index | `ingest_documents(index_knowledge_graph=true)` | 需先 `ENABLE_LIGHTRAG=true` 並重啟 MCP |
| 查 KG | `knowledge(op="consult")` | 先用 `knowledge(op="export", format="summary")` 確認 graph 有內容 |
| 讀寫 DOCX/DFM | `docx(op="ingest|get|save|validate")` | 寫回前注意 stale source / validation |
| DOCX table bridge | `docx_table(op="to_context|from_context|edit_plan")` / `docx_table_edit_plan` | 真正編輯 rows/cells 後進 A2T tools |
| 建立 A2T table | `plan_table` + `table_manage` | rows/cells 用 `table_data` |
| 表格引用 | `table_cite` | draft/commit 用 `table_draft` |
| 背景任務 | `job(op="get|list|cancel")` / `get_job_status` / `list_jobs` | 長任務狀態、取消、artifact path |
| ETL profile | `etl_profile(op=...)` | 匯入 profile 或切 active profile |

## 推薦流程

### PDF 到可引用證據

```text
document(op="ingest")
-> section(op="tree")
-> evidence(op="find")
-> evidence(op="bundle")
-> evidence(op="verify")
```

寫入 wiki：

```text
evidence(op="bundle", output_format="foam", wiki_root="/path/to/wiki")
-> evidence(op="health", wiki_root="/path/to/wiki")
```

### DOCX 到表格編輯

```text
docx(op="ingest")
-> docx_table(op="to_context")
-> table_data(...)
-> docx_table(op="from_context")
-> docx(op="validate")
```

### KG 到 LLM wiki

```text
ingest_documents(index_knowledge_graph=true)
-> knowledge(op="export", format="summary")
-> knowledge(op="consult", verify_references=true)
-> evidence(op="bundle", output_format="foam")
-> topic note with [[wikilinks]]
```

## Resources 搭配

| 類型 | Resource |
|---|---|
| 文件 manifest | `document://{doc_id}/manifest` |
| 章節列表 | `document://{doc_id}/sections` |
| 文件 segmentation／blocks | `document://{doc_id}/segmentation` |
| 表格狀態 | `table://{table_id}/status` |
| 表格內容 | `table://{table_id}/content` |

## 注意

- `section(...)` 是章節導覽；真正要驗證 claim 時回到 `evidence(...)`。
- KG answer 是 discovery layer，不是最終引用來源。
- `parse_pdf_structure` 使用目前設定的 structured extractor；Docling 可用，Marker／MinerU hold 或 backend 不可用時會 fail closed。
- `ingest_documents(use_marker=true)` 是歷史參數名稱，只代表偏好目前設定的 structured extractor；Docling 可用，Marker／MinerU 仍受 security hold，且公開參數沒有 `require_marker`。
- `table_manage` 不直接寫 row/cell；row/cell 讀寫使用 `table_data`。
