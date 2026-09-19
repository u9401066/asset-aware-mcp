# A2T Tables

原生 XLSX 套用 A2T 修改後，可用 `create_workbook_rendition` 將該版本固定成
PDF，完整讀取 `read_rendition`，再以實際頁面核對公式與版面。列印範圍、隱藏
工作表及快取政策會影響結果；詳見 [工作簿版面核對](Native-File-Assets)。
公開版維持 1.4.0，本項為 Unreleased／1.4.x。

## Native Table totals lifecycle (Unreleased)

`table_totals_lifecycle_enabled` 啟用時，以 `update_workbook_table` 的
`table_update.totals_row` 明確新增或移除合計列。仍須提供目前版本、worksheet key、
Table part 及 `expected_ref`；若只有合計列轉換，可省略 `columns`。

| 意圖 | 行為 |
|---|---|
| `{action:"add",reuse_definitions:true,cell_styles:"preserve"}` | Table 向下延伸一列；目標格須空白，重用保留的標籤／函式／自訂公式 |
| `reuse_definitions:false` | 新合計列先使用空白定義；同次 columns[].totals 可明確覆寫 |
| `cell_styles:"last_data_row"` | 從最後資料列複製直接儲存格樣式；列高及列／欄預設格式不變 |
| `{action:"remove",cells:"clear",retain_definitions:true}` | 移除合計角色並清空原列內容，保留儲存格樣式及可重用定義 |
| `cells:"keep_cells"` | 保留文字／富文字；留下公式對此 Table 的引用改為移除前的絕對座標 |
| `retain_definitions:false` | 一併丟棄保留的合計定義 |

兩種轉換都保留既有資料列，沒有插入或刪除整張工作表的列。需要騰出空間時，
Agent 先明確使用 `update_worksheet_grid`，再讀回新版本執行合計操作。移除後選擇
保留的公式固定原範圍，不再隨未來 Table 增長；工作簿其他位置的 Table 引用保持
結構化形式，包含移除後不再有可用列的 `[#Totals]`。

MCP 檢查空間、合併格、特殊公式、保護與來源依賴；篩選／排序維持原資料範圍，
樞紐來源檢查包含新增或卸離的合計列。引用字串以解析結果轉換，保留字面字串及
外部工作簿引用；不明確的混合範圍需要先修改公式。合計列中的 `#This Row`／
`[@欄名]` 沒有資料列交集，保留公式前必須先明確處理，不能轉成有效座標。
共享字串內容與 runs 保留，
引用計數可隨清除操作重新計算。操作紀錄含原始 before 值、範圍與明確選項。

完整讀回新 references、儲存格及 operation_result 後，Agent 核對語意、未來公式
範圍、篩選、計算結果及實際畫面。舊證據與 Wiki 不自動遷移；公開版維持
**1.4.0**，這些變更累積於 **Unreleased／1.4.x**。

## Native Table creation (Unreleased)

`workbook_table_creation_enabled` 啟用時，可先用 `create` 建立獨立 XLSX，
或註冊既有工作簿，再以 `add_workbook_table` 將指定範圍建立成原生 Excel Table。
先讀完 `read_workbook(workbook_view="references")`，固定 asset_id、
expected_revision 與 worksheet 的 sheet_id／part。

`table_create` 指定 ref、工作簿內唯一的 name，以及依順序排列的 columns。
每欄含 name，可選 calculated 與 totals，使用下節相同的公式／合計格式。
ref 包含標題、至少一筆資料及選用合計列；操作不插入工作表列。

| 選項 | 行為 |
|---|---|
| `header_policy="require_matching"` | 保留與欄名完全相同的字串標題，含富文字／共享字串 |
| `header_policy="fill_blank"` | 另允許填入空白標題；既有值仍須完全相同 |
| `header_row=false, autofilter=false` | 建立沒有標題列的 Table，第一列仍是資料 |
| `totals_row=true` | 指定範圍的最後一列須先為空白，避免誤吞資料 |
| `calculated.policy="require_matching"` | 新計算欄填入空白格；既有值須明確使用 replace_all |
| `style` | 預設 TableStyleMedium2 與列條紋；可指定內建或工作簿已有樣式及條紋選項 |

一般資料、前導零、儲存格樣式和未修改 package parts 保留。名稱、重疊 Table、
合併格、工作表篩選、特殊公式及保護條件會先檢查；已卸離的 Table parts 也保留
名稱／ID，避免重用。空的或明確未啟用的 workbookProtection 不再誤判為已上鎖。

一次提交後，完整讀回 created_table、欄位 ID、header_cells、before／after
及機械檢查紀錄，再核對語意、篩選、公式結果與實際畫面。MCP 請求重算，
不宣稱已執行 Excel 計算。歷史引用、Wiki 與 A2T 綁定不會自動轉成新版。
公開版維持 **1.4.0**，此項累積於 **Unreleased／1.4.x**。

## Native Table column edits (Unreleased)

`workbook_table_edit_enabled` 啟用時，先完整讀取目前版本的
`read_workbook(workbook_view="references")`，再使用 `update_workbook_table`。
`table_update` 指定 worksheet key、Table part、expected_ref，外層指定
asset_id／expected_revision。每個 columns 項目固定 column_id／expected_name。

| 欄位 | 行為 |
|---|---|
| `name` | 同步改欄位名稱與標題，既有結構化引用依原欄位身分更新 |
| `header_runs` | 富文字標題必填，段數與原 runs 相同，串接後等於新 name；保留各段格式 |
| `calculated={formula:"=A2*2",policy:"require_matching"}` | 公式以第一筆資料列定位並逐列搬移；只接受空白或符合舊計算欄公式的格子 |
| `calculated={formula:"=A2*2",policy:"replace_all"}` | 明確覆寫該欄的一般值／公式，保留樣式 |
| `calculated={formula:null,policy:"keep_cells"}` | 移除自動填入公式的欄位定義，保留現有儲存格 |
| `totals={kind:"function",value:"sum"}` | 修改既有總計列的 SUBTOTAL 函式；也可用 blank、label 或 formula |

新公式使用修改後的欄名。完整 `tables[].header_cells` 提供儲存格與解析後共享
字串 XML，供 Agent 檢查 runs；改一格不會覆寫其他格共用的文字。原 Table 範圍、
篩選範圍、欄位 ID 與樣式保留；總計列操作不會默默占用資料列。

一般儲存格的保護仍有效。已保護、合併、陣列／共享公式、音標／未知擴充文字
需要對應操作；樞紐來源標題與映射／查詢結構須先協調欄位身分。修改會清除過期
公式／圖表快取並請求重算；核對完整 operation_result 與新舊引用後，Agent 再核對
語意、篩選狀態、公式結果及實際畫面。舊引用與 A2T 綁定不自動前進。
公開版仍 **1.4.0**，此功能列於 **Unreleased／1.4.x**。

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
Table 邊界需要下節的明確 expand_tables 指定；表格成員、動態引用、公式求值及
實際畫面仍由 Agent 核對。獨立建立工作簿可另外使用 create_workbook_from_table。

## Native Table expansion (Unreleased)

先確認 `table_expansion_enabled`。完整 `read_workbook` 的 `tables` 會列出
Table 的 part、worksheet、attributes、column IDs、原始 part SHA-256 與完整
解析 XML。Table 定義與工作表儲存格是不同 parts，兩者都必須核對。

列欄插入可明確納入某個 Table。在插入步驟加入 `expand_tables`，例如原本
Table 為 A1:F3，先新增資料列、再新增右側欄位：

```json
{
  "edits": [
    {"axis":"row","operation":"insert","at":4,
     "expand_tables":[{"part":"xl/tables/table1.xml","expected_ref":"A1:F3"}]},
    {"axis":"column","operation":"insert","at":7,
     "expand_tables":[{"part":"xl/tables/table1.xml","expected_ref":"A1:F4"}]}
  ]
}
```

這是 `worksheet_grid` 的 edits 部分；仍須帶上目前 worksheet key。
每個 expected_ref 對應該步開始時的範圍。可在首／尾資料邊界或左右欄邊界擴展；
有總計列時在總計列之前插入。相鄰 Table 不會被連帶選入。整列欄仍會搬移。
MCP 保留原欄位 ID，為新欄位建立新 ID 與不重複的標題，同步 Table、filter、
sort 範圍與計算欄公式。篩選條件、排序欄身分及未修改格式保留；不代替 Excel
重新篩選、排序或計算。

A2T 若要沿用這次操作產生的標題／計算欄格，明確指定
`{"kind":"native_generated","value":null}`。一般未給值或 blank 仍表示空白，
不能用它們暗示保留公式。native_generated 只適用於這次新生成的格，不能用在
一般格、既有格或直接另建工作簿。先讀回原生結果，再投影即可取得已解析值。
操作紀錄的 `generated_table_cells` 列出最終座標，`resolve_native_generated_values`
記錄目的範圍內的實際值；凍結 A2T 保存原始意圖，來源引用維持舊版。

自訂 Table 標題、計算欄／總計公式編輯、來源欄位映射及原生重排仍有各自的
處理範圍。Agent 核對語意、計算結果、篩選可見性、排序及實際畫面。
設計參考 [Microsoft SpreadsheetML tables](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-tables)
與 [XlsxWriter tables](https://xlsxwriter.readthedocs.io/working_with_tables.html)。

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
