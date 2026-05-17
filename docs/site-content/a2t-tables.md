<!-- Generated from A2T-Tables.md by scripts/build_docs_site.py -->

# A2T Tables

![A2T table workflow](wiki/assets/a2t-table-workflow.jpg)

## 核心模型

A2T 是 Anything to Table。它用 `TableContext` 表示可由文件、DOCX 表格、圖表或 LLM extraction 建立的結構化表格，並讓每個 cell 可以帶來源引用。

來源：`src/domain/table_entities.py`、`src/application/table_service.py`、`src/application/dfm_table_bridge.py`、`src/presentation/tools/table_tools.py`、`src/presentation/resources/table_resources.py`。

## 功能模組

| Tool | 責任 |
|---|---|
| `plan_table` | schema 設計、模板查詢、模板建表 |
| `table_manage` | 建立、刪除、列表、預覽、render、schema 演進 |
| `table_data` | rows/cells CRUD plus `query_rows` paging, search, filters, selected columns, and row coverage |
| `table_cite` | cell citation refs, row/cell lookup by stable `row_id`, and citation coverage |
| `table_history` | changelog、token estimate |
| `table_draft` | draft workflow |
| `discover_sources` | 從文件和 KG 搜尋可抽取來源 |

## TableContext 保存內容

- table id
- title
- columns (`ColumnDef`)
- rows
- stable row IDs (`schema_version: a2t-table-v2`)
- row provenance
- source description
- cell citations
- change log
- created/updated timestamps
- source revision/hash metadata when bridged from DOCX

## Cell Citation

每個 cell 可附多個 AssetRef。這支援：

- 同一數值由多個來源佐證。
- confidence / notes。
- 移除 stale citation。
- 將 table 轉 Markdown/HTML 時保留 footnote-like refs。

## Large Table UX

- `table_data(op="query_rows", offset=..., limit=..., search=..., filters=...)`
  is the preferred way to inspect large tables without inlining the whole table.
- `table_manage(op="render", format="markdown" | "html", artifact_only=true)`
  writes a full artifact with a SHA-256 hash and returns only a bounded preview.
- `table_cite(op="coverage")` reports current/stale citation coverage.
- Startup skips persisted table JSON files above
  `ASSET_AWARE_TABLE_STARTUP_LOAD_MAX_BYTES`, but `table_manage(op="list")`
  still shows `load_status=skipped_large`, artifact path, size, and manifest
  metadata when available.
- Skipped large tables can be deleted by table id; normal operations fail
  closed with an actionable message instead of silently returning "not found".

## Draft Workflow

`table_draft` 讓 agent 先建立草稿：

```text
create -> update -> add_rows -> resume -> commit
```

這適合多步 extraction：先規劃欄位，再逐文件補資料，最後提交為正式 TableContext。

## DOCX Bridge

DOCX table block 可以用 `docx_table_to_context(register=true)` 轉成 TableContext。初次 register 會讓 table 在目前 session 可見；經過 mutating table operation 後，TableContext 會進入 durable table persistence。結構化編輯後可用 `docx_table_from_context` 寫回 DFM。Chart data 則用 `docx_chart_data` 擷取底層資料。

## Resources

- `tables://list`
- `table://{table_id}/content`
- `table://{table_id}/status`
- `drafts://list`
- `draft://{draft_id}/content`
