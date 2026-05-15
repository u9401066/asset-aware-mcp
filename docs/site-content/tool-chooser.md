<!-- Generated from Tool-Chooser.md by scripts/build_docs_site.py -->

# Tool Chooser

這頁是「我現在該用哪個 MCP tool？」的快速查表。完整參數仍以
[MCP Tools](#/mcp-tools) 和 [MCP Resources](#/mcp-resources) 為準；這裡只幫你從任務進入。

## 先選任務

| 任務 | 首選入口 | 什麼時候改用 reference |
|---|---|---|
| 攝入 PDF | `document(op="ingest")` / `ingest_documents` | 需要 legacy client allow-list 時查 `ingest_documents` |
| Marker-required parse | `document(op="parse")` / `parse_pdf_structure` | 需要診斷 Marker security hold 時查 PDF workflow |
| OCR PDF | `ocr_pdf_document` | 需要背景 job artifact path 時查 Background Jobs |
| 看章節樹 | `document_asset(op="tree")` / `list_section_tree` | 需要 resource URI 時查 MCP Resources |
| 找可引用文字 | `evidence(op="find")` / `find_evidence_spans` | 需要 source locator 搜尋時用 `evidence(op="locate")` |
| 驗證 AssetRef | `evidence(op="verify")` / `verify_citation_ref` | promotion 到 wiki 前一定要驗證 |
| 寫 Foam evidence pack | `evidence(op="bundle")` / `citation_bundle` | 需要完整寫檔規則時查 LLM Wiki |
| 寫 table/figure note | `document_asset(op="foam_notes")` | asset note drift 用 `evidence(op="health")` |
| 建立 KG index | `ingest_documents(index_knowledge_graph=true)` | 需先 `ENABLE_LIGHTRAG=true` 並重啟 MCP |
| 查 KG | `knowledge(op="consult")` / `consult_knowledge_graph` | 先用 `export_knowledge_graph(format="summary")` 確認 graph 有內容 |
| 匯出 KG | `knowledge(op="export")` / `export_knowledge_graph` | 視覺化前先匯出 JSON |
| 讀寫 DOCX/DFM | `docx(op="ingest|get|save|validate")` | 需要舊工具名時查 DOCX workflow |
| DOCX table bridge | `docx_table(op="to_context|from_context|edit_plan")` | 真正編輯 rows/cells 後進 A2T tools |
| 建立 A2T table | `plan_table` + `table_manage` | rows/cells 用 `table_data` |
| 表格引用 | `table_cite` | draft/commit 用 `table_draft` |
| 背景任務 | `job(op="get|list|cancel")` / legacy job tools | 長任務狀態、取消、artifact path |
| ETL profile | `etl_profile(op=...)` / legacy profile tools | 匯入 profile 或切 active profile |

## 建議路徑

### PDF 到可引用結論

```text
document(op="ingest") -> document_asset(op="tree") -> evidence(op="find")
-> evidence(op="bundle") -> evidence(op="verify")
```

若要寫入 wiki：

```text
evidence(op="bundle", output_format="foam", wiki_root="/path/to/wiki")
-> evidence(op="health", wiki_root="/path/to/wiki")
```

### DOCX 到可回寫表格

```text
docx(op="ingest") -> docx_table(op="to_context") -> table_data(...)
-> docx_table(op="from_context") -> docx(op="validate")
```

### KG 到 LLM wiki

```text
ingest_documents(index_knowledge_graph=true)
-> export_knowledge_graph(format="summary")
-> knowledge(op="consult", verify_references=true)
-> evidence(op="bundle", output_format="foam")
-> topic note with [[wikilinks]]
```

## Resources 何時更適合

用 tool 做動作；用 resource 讀穩定狀態：

| 想讀 | Resource |
|---|---|
| 文件 manifest | `document://{doc_id}/manifest` |
| 章節列表 | `document://{doc_id}/sections` |
| 文件 blocks | `document://{doc_id}/blocks` |
| 表格狀態 | `table://{table_id}/status` |
| 表格 preview | `table://{table_id}/preview` |

## 避免常見誤用

- `document_asset(op="search")` 是 section search，不是 source locator。
- KG answer 不是 citation-ready source；用 `verify_references=true` 或回到 evidence bundle。
- `parse_pdf_structure` 是 Marker-required，Marker 不可用時會 fail closed。
- `ingest_documents(use_marker=true)` 只是偏好 Marker；目前公開參數沒有 `require_marker`。
- `table_manage` 不讀 row/cell；row/cell 讀寫在 `table_data`。
