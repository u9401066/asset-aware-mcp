# A2T Tables

## Native workbook workspaces (Unreleased)

公開版仍為 **1.4.0**，此功能累積於 **1.4.x**。先查原生 `contract` 的
`table_workspaces_enabled` 與各操作的 `for_op` schema。

1. `read_workbook` 取得固定 revision 的工作表 `sheet_id`／`part`。
2. `project_workbook_table` 指定 asset_id、revision 與
   `table_projection={worksheet:key,start_cell:"A1",end_cell:"E3"}`。
   所有列（含標題列）都是資料，欄名為 Excel 欄字母，不猜型別或標題。
3. `read_table_workspace(table_id=...)` 讀回完整 JSON；依 `next_text_offset`
   續讀，每頁固定 `table_sha256`，拼接後以 UTF-8 核對 `text_sha256`。
   最多 20,000 格、完整表示 16 MiB，每頁至多 4,000 字元。
4. 使用 `table_data` 更新穩定 row_id 的儲存格，例如
   `value={"kind":"string","value":"007"}`。可用 string／number／boolean／
   formula／blank；formula 明確以 `=` 開頭，一般字串 `=1+1` 不會變公式。
   `source_only` 保留無編輯器的原值；不能當成可寫型別。
5. 重新完整讀取後，`apply_table_workspace` 指定 table_id、
   `expected_table_sha256`、asset_id 與原綁定的 `expected_revision`。
   只套用變動格，保留原格式與未修改 parts；合併尾格、富文字及表格標題等
   既有編輯保護仍有效。核對新版儲存格及 `read_workbook.operation_result`。

每次套用或另建工作簿都保存實際使用的 A2T JSON，回傳 `workspace_reference`。
它可用 `verify` 驗證，也可傳回 `read_table_workspace`；即使可變表格後來更新或
刪除，仍能重讀原快照。綁定不會自動改指新版檔案；下一輪同步請重新投影。
來源檔只在明確 publish／writeback 時輸出或回寫。

結構修改可使用下節的明確回寫計畫。也可使用
`create_workbook_from_table`，指定 table_id、expected_table_sha256 與
`table_workbook={name:"table.xlsx",sheet:"Data",include_headers:false}`，另建
獨立 XLSX；也可指定 workspace_reference 重用固定輸入。新檔保留型別與公式文字，
會回報列欄對應，但不複製來源樣式、不搬移公式引用。普通 A2T 的純量也可匯出；
native 欄位不可經舊的 Excel renderer 字串化輸出。

完整工作區同時保留目前值與原版 source_cells 引用。引用表示抽取來源，並不宣稱
它支持修改後的語意；既有 PDF／DFM CellCitation 另行保留。Agent 仍需核對語意、
公式計算與畫面；來源引用不會自動變成修改後內容的證據。

## Structural A2T writeback (Unreleased)

先確認 `contract(for_op="apply_table_workspace")` 的 `table_grid_apply_enabled`。
新工作區保存 row_ids 與 column_ids；欄位改名保留身分，刪除再建立同名欄位會
產生新 ID。`table_manage` 的 native 欄位可使用帶型別 JSON 作為 default_value。
舊快照仍能依原 hash 讀回；已有模糊結構歷史的舊工作區需要重新建立明確對應。

以 `table_data`／`table_manage` 增刪列欄後，再完整讀取 `read_table_workspace`。
`structural_plan` 提供依身分推導的 `worksheet_grid` 與目的範圍；MCP 不會自行套用。
核對計畫及目前工作簿的完整 references，才將該計畫明確傳入：

```python
document(op="native", native_request={
    "op": "apply_table_workspace",
    "asset_id": asset_id,
    "expected_revision": bound_revision,
    "table_id": table_id,
    "expected_table_sha256": current_table_hash,
    "worksheet_grid": complete_workspace["structural_plan"]["worksheet_grid"],
})
```

結構與值只產生一次原生版本提交。未改值的來源儲存格隨原生列欄搬移，保留格式、
富文字及公式調整；新建／明確修改的公式使用目的座標，新格未給值視為空白。
完整讀回新版 `read_workbook(workbook_view="references")`、操作紀錄及目的範圍，
並重讀／驗證 workspace_reference。原綁定與舊證據維持歷史版本。

計畫操作的是整列／整欄，投影外的內容也會移動。刪除計畫使用
`merged_anchor="delete"`，不把已刪身分的內容挪給其他儲存格。既有列欄重排仍需
原生移動支援；原生 Excel Table 標題、計算欄、部分陣列等保護仍有效。
在原生 Table 範圍外插入列欄不會自動擴大它；表格成員、動態引用、公式求值及
實際畫面仍由 Agent 核對。獨立建立工作簿可另外使用 create_workbook_from_table。

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

### 完整引用讀回（main 開發中，尚未發布）

`get` 保留原有 cell／row／table 摘要。當安裝版本的工具規格列出 `read` 時，
可讀回完整儲存格值、來源引用、notes 與 confidence：

```python
table_cite(operation="read", table_id="tbl_...", row_id="row_...",
           column_name="Reading", text_limit=4000)
# Continue if next_text_offset is not null:
table_cite(operation="read", table_id="tbl_...", row_id="row_...",
           column_name="Reading", text_offset=next_text_offset,
           citation_sha256=citation_sha256)
```

依序拼接 `text_excerpt`，以 UTF-8 計算 SHA-256 核對 `citation_sha256`，再解析
完整 JSON。所有頁必須使用同一 hash；值、引用或 cell 身分不同就拒絕續讀。
穩定 `row_id` 不受其他列刪除後的索引位移影響。完整表示最多 16 MiB，每頁最多
4,000 字元，實際頁長還受 MCP 回應上限限制。缺少引用時 `citation` 明確為 null。

回傳保留儲存的 `doc_id`、`asset_id`、頁碼、範圍、完整 quote/hash 與其他欄位；
沒有的 locator 不會補造。分頁片段不是 canonical AssetRef，摘要也不能當完整
引文。hash 只核對儲存內容，Agent 仍須查看來源並判斷它是否支持該儲存格。

main 開發版也修正操作結果的列識別：傳入 `row_id` 時以穩定 ID 為準，讀取、
更新、清空與刪除結果顯示實際解析的列索引；刪除回報的是刪除前索引。引用歷史
使用列 ID 標示，避免預設 `row_index=-1` 或舊索引造成誤導。

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
