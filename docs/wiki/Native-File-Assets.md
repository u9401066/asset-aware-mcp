# Native File Assets（v1.4.0）

Agent 可以登錄人類交付的檔案，也可以直接建立 XLSX 工作簿。每份檔案都有固定
`asset_id`、不可變的 SHA-256 版本與操作能力；PDF、DOCX 等既有工作流程仍使用
各自的工具。登錄其他格式會保留原始內容，不代表已具備該格式的編輯器。

Native file assets have stable IDs, immutable revisions and explicit format
capabilities. Version 1.1.0 adds XLSX creation and scoped XLSX/XLSM
cell reads/edits through the existing `document` tool. It does not complete
cross-format CRUD or visual fidelity verification. Version 1.2.0 adds native
reference verification and immutable wiki snapshots, described below.

Version 1.3.0 adds the DOCX bridge and block evidence described below.
Discover the installed contract
before using the new operations.

## Contract v2 (1.4.0)

1.4.0 的 `contract` 回傳 `contract_version="native-contract-v2"`。
此回應變更需要客戶端遷移；請先查安裝版本。客戶端應查看 `schema_delivery`，
不要假設 `schema` 一定存在。只查單一操作可使用：

```python
document(op="native", native_request={"op": "contract", "for_op": "update_docx"})
```

需要完整規格時，將回傳的 `schema_request` 原樣放入 `native_request`。
依 `next_text_offset` 繼續讀取，每頁保留同一個 `schema_sha256` 與 `for_op`；
續讀缺少雜湊、安裝版本改變或 scope 不同會拒絕。串接 `text_excerpt` 後，
先核對 UTF-8 SHA-256 與 `text_length`，再解析 JSON。單一操作的 schema
保留必要欄位、非空限制與相依定義；實際語意和檔案狀態仍由 runtime 檢查。

Clients migrating from the v1.3 always-inline response must inspect
`schema_delivery` and follow `schema_request` for paged schemas. `for_op` limits
fields to one operation; the full declared request schema remains in MCP
`tools/list` and is also available through `schema`. Canonical JSON pages use
character offsets and a UTF-8 SHA-256. Existing native document inputs are unchanged.

## 開始使用

先查詢契約，取得實際支援的操作與 typed request schema：

```python
document(op="native", native_request={"op": "contract"})

document(op="native", native_request={
    "op": "create",
    "workbook": {
        "name": "budget.xlsx",
        "sheets": ["Budget"],
        "edits": [
            {"sheet": "Budget", "cell": "A1", "value": "費用"},
            {"sheet": "Budget", "cell": "B1", "kind": "number", "value": 250},
            {"sheet": "Budget", "cell": "B2", "kind": "formula", "value": "=B1*2"}
        ]
    }
})
```

回應包含 `asset.asset_id` 與 `asset.revision`。範例下方的 `asset_id`、
`revision`、`source_sha256` 皆指前一步回傳值。

```python
document(op="native", native_request={
    "op": "register", "source_path": "/absolute/path/existing.xlsx"
})
document(op="native", native_request={
    "op": "inspect", "asset_id": asset_id, "sheet": "Budget", "limit": 10
})
document(op="native", native_request={
    "op": "update", "asset_id": asset_id, "expected_revision": revision,
    "edits": [{"sheet": "Budget", "cell": "B1", "kind": "number", "value": 300}]
})
```

`update` 產生新的受管理版本，回傳 `source_written=false`，不會立即改寫人類檔案。
後續寫入必須使用新回傳的版本。`kind="blank", value=None` 清空值並保留儲存格樣式。
字串預設是文字，包含 `=1+1`；公式必須明確指定 `kind="formula"`。

## 操作範圍

| 操作 | 用途與必要欄位 |
|---|---|
| `contract` | request schema、能力與驗證分工 |
| `register` | `source_path`：登錄本地原始檔與來源狀態 |
| `create` | `workbook`：建立獨立 XLSX，不需要 PDF 或 A2T context |
| `list` | `offset`、`limit`：列出已登錄資產，含 archived entries |
| `inspect` | `asset_id`；可選 `revision`、`sheet`、`offset`、`limit` |
| `read_cell` | `asset_id`、`sheet`、`cell`；可選版本與文字分段範圍 |
| `update` | `asset_id`、`expected_revision`、`edits`：原子提交一批 typed cell edits |
| `history` | `asset_id`：分頁查詢版本與父版本，舊版本仍可讀取 |
| `publish` | `asset_id`、`expected_revision`、`output_path`：建立新的外部檔案 |
| `writeback` | `asset_id`、`expected_revision`、`expected_source_sha256`：明確回寫來源 |
| `refresh` | 同上三個欄位：採納人類對來源的修改，保留資產身分及舊版本 |
| `archive` | `asset_id`、`expected_revision`：封存，保留內容與人類原始檔 |

`publish` 保留副檔名，拒絕覆蓋既有路徑。`writeback` 檢查來源雜湊、大小、mtime
與檔案身分，保留備份，再驗證寫入結果。若來源已寫入而後續 metadata 儲存失敗，
回應會明確標示 `source_written=true`、`reconciliation_required=true` 與備份路徑。
Agent 檢查來源和備份後，可用 `refresh` 同步 metadata。

`refresh` 只會採納不丟失待回寫修改的來源版本。人類和 Agent 同時修改同一基礎版本，
會回報 divergence 並保留雙方內容，由 Agent 比較及協調。服務內的操作使用 OS lock；
外部應用程式不受這把鎖控制，Agent 仍需協調同時編輯，備份也不自動刪除。

## 必要檢查與 Agent 核對

| MCP 可檢查／處理 | Agent 仍須核對 |
|---|---|
| 不相關 OOXML member 解壓後的 bytes 相同，styles／charts／comments 等保留 | 在 Excel／相容應用程式中的實際畫面與可讀性 |
| 儲存後重新解析目標儲存格，核對 typed value 與定位 | 值與公式是否符合工作目的、來源證據是否支持結論 |
| worksheet dimension、row span cache、shared-string count、calc chain 的確定性維護 | 公式重算結果與圖表顯示是否正確 |
| 來源版本比對、不可變歷史、失敗時保留先前 metadata | 衝突如何合併，以及應否採用人類／Agent 的修改 |

目前支援 transitional OOXML 的一般儲存格更新。保護中的 sheet、合併區域的
非 anchor、shared／array／data-table formula 範圍、rich text、table header／totals／
calculated columns、帶有特殊 metadata 的 cell 與已簽章 package，會拒絕不受支援的修改。
XLSM 中未動到的 VBA parts 保留，但工具不執行巨集，也不驗證巨集行為。
尚未提供插刪 rows／columns、格式設計、整張 sheet CRUD、原生表格／A2T 橋接或公式引擎。

儲存格值與 `style_index` 代表原生資料，不是 Excel 渲染後的顯示字串；日期、百分比
及貨幣等顯示需結合 number formats 解讀。公式 cached value 一律標示未驗證，
shared formula follower 尚未解析時回傳 `formula_resolved=false`，不捏造公式。

## 長文字與來源定位

`inspect` 的 cell 含 `native-cell-ref-v1`：asset ID、不可變版本、sheet ID／part／cell
locator，以及完整原生 cell 表示的 SHA-256。它與 PDF 的 AssetRef 是不同契約，
不能交給 PDF `verify_citation_ref`；請使用本頁的原生引用驗證與 wiki 匯出操作。

大型工具回應會明確標示截短。降低 `limit`，或逐一使用 `read_cell`：

```python
document(op="native", native_request={
    "op": "read_cell", "asset_id": asset_id, "revision": revision,
    "sheet": "Budget", "cell": "A1", "text_offset": 0, "text_limit": 2000
})
```

文字回應使用 `value_excerpt`，附字元範圍、`next_text_offset`、完整文字 hash
與完整 cell 的 evidence ref；不把片段冒充完整值。數字／布林值仍使用 `value`。
`value_sha256` 是完整 cell 表示的 hash；`value_text_sha256` 才是完整文字的 hash。

Limits: 64 MiB native files, 128 MiB decompressed packages, 32 MiB per ZIP member,
10,000 package members, 20,000 edits per request, and 10,000 stored revisions.
Pagination defaults to 20 items; `read_cell` returns up to 4,000 characters per call.
DTD/entity expansion, ambiguous locators and duplicate ZIP members are rejected.

Implementation references: [XlsxWriter](https://github.com/jmcnamara/XlsxWriter)
constructs new packages; existing packages use scoped XML changes because
[openpyxl documents preservation limitations](https://openpyxl.readthedocs.io/en/stable/tutorial.html).
Independent openpyxl reads supplement package-level tests for common workbook
features; they do not substitute for visual review or prove every escape/rendering case.
Text escaping follows [Microsoft's ST_Xstring implementation notes](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oe376/bd0aa042-434a-4ca7-b25f-4e1fd25a954d),
including carriage returns and literal escape-looking underscores.

## 1.2.0：原生引用驗證

1.2.0 新增 `document(op="native", native_request={"op":"verify", "reference": ref})`，
其中 `ref` 為 `inspect` 或 `read_cell` 回傳的 `evidence` 物件。它核對不可變版本的
檔案 hash、worksheet／cell 定位與完整 cell 表示 hash，回傳 `valid`；另外以
`is_current_managed_revision` 標示是否仍是目前受管理版本。舊引用及已封存資產仍可驗證。
來源人類檔案的新鮮度、語意、視覺與公式計算不在這項完整性核對之內。

Version 1.2.0 verifies native references against their immutable
revision, including references obtained with a short excerpt. It is separate from
PDF reference verification; native wiki export is described below.

## 1.2.0：版本固定的 Wiki 匯出

```python
document(op="native", native_request={
    "op": "export_wiki",
    "asset_id": asset_id,
    "output_dir": "/absolute/path/wiki/evidence",
    # 可指定舊的 revision；省略時使用目前受管理版本
    "citation_contract": {"preset": "author-year"},
    "citation_metadata": {"authors": "Lin", "year": "2026"}
})
```

回傳的 `output_dir` 是 wiki 目錄內的新快照，`index_note` 是閱讀入口。快照包含
原始附件、`manifest.json` 檔案 hash 清單、`records.jsonl` 完整 cell 表示及引用，
以及可直接連結的 Foam 儲存格筆記。使用 `verify` 可核對每筆 `evidence`。
其他格式會匯出原始附件及 metadata，明確標記 `opaque_binary`。

每個引用固定 asset ID、revision 與 worksheet／cell 定位。更新原檔或受管理版本後，
再次匯出會建立另一份快照；舊 wikilink 不會偷偷指向新的內容。Agent 可在相鄰的人工
筆記撰寫跨版本比較與語意整合，MCP 不會改寫這些筆記。

同一版本重複匯出必須通過完整檔案清單與內容核對；遇到人工修改、額外檔案、缺檔或
symlink 會拒絕覆蓋。若要用不同引用格式重新呈現同一版本，請指定另一個匯出目錄，
將其當作另一份 wiki 使用；目前沒有原地重寫快照或自動合併人工筆記的操作。
筆記名稱與 canonical reference 不受顯示格式影響；引用定位如 `'Budget'!B2`
由來源產生，不能透過 citation metadata 覆寫。這不是完整 APA／CSL 排版引擎。

上限為 20,000 個已儲存 cell、128 MiB 匯出內容，超過時整次拒絕，不會靜默截斷。
尚未儲存的空白座標及 chart／dialog sheets 不產生儲存格筆記。公式快取未重新計算；
數字是原生表示，尚未套用日期或貨幣顯示格式。

建立快照使用排他新增，最後寫入 manifest 作為完成標記。中斷時保留已寫入的檔案，
回傳 `success=false` 與 `reconciliation_required=true`；Agent 應檢查保留內容，
再選新目錄匯出或協助使用者處理。這不保證整個目錄一次出現，也不鎖住外部編輯器。

Native exports preserve immutable source bytes and full cell references, while
custom citation templates only affect presentation. Existing snapshots are never
replaced. Agents retain responsibility for semantic, rendered and formula review.


## 1.3.0: native DOCX bridge

1.3.0 新增 `read_docx`／`update_docx`，使用既有 DFM 流程處理已登錄
DOCX 的指定版本。先查 `contract` 確認安裝版本支援，再操作：

```python
document(op="native", native_request={
    "op": "read_docx", "asset_id": asset_id, "revision": revision,
    "text_offset": 0, "text_limit": 4000, "offset": 0, "limit": 2
})
```

`dfm.text_excerpt` 是字元分段；持續以同一個 `revision` 讀到
`next_text_offset=null`，依序組合並核對 `text_sha256`。完整 DFM 上限為 4 MiB UTF-8。
`blocks` 另用 `offset`／`limit` 分頁，含 preview、類型、原生 locator metadata 與
`native-docx-block-ref-v1` evidence。Block IDs 僅對該版本有效，不是跨版本元件 ID；
引用包含完整版本與套件位置，可交給原生 `verify`。
DFM 中附件路徑是保留資訊，不是持久公開的檔案路徑；工作暫存於操作結束後清除。

```python
document(op="native", native_request={
    "op": "update_docx", "asset_id": asset_id, "expected_revision": revision,
    "docx_edit": {
        "dfm_text": complete_edited_dfm,
        "track_changes": True,
        "revision_author": "研究作者"
    }
})
```

保留完整 frontmatter 與每個區塊標記的原始順序。工具核對原生 asset/revision 綁定，
再執行既有 DFM session/checksum、儲存前後、表格形狀及未修改區塊檢查；沒有 `force`
選項。簽章與保護文件可讀，但目前拒絕更新。支援既有本文段落及同形表格內容更新，
不支援插刪區塊、重新排序、文件樣式設計或 DOC/DOCM 轉換。

回應提供新 `asset.revision`、`operation_result` 的實際 changed parts／block IDs、
未修改 parts 數量、必要檢查及 Agent 核對項目。除 `word/document.xml`，以及明確
指定修訂追蹤時的 `word/settings.xml`，其他 ZIP member 內容必須逐一相同。這仍不
證明 Word 顯示、欄位更新或內容語意正確；Agent 需開啟／渲染新版本核對與修正。

更新只寫入受管理版本，`source_written=false`。接著可 `publish` 新檔供審閱，再用
既有 `writeback` 明確回寫來源，保留備份並檢查來源是否已被人類修改。舊版本仍可
`read_docx`、`read_docx_block` 與 `verify`，也可重新匯出該版本的 Wiki 快照。

### DOCX block evidence and wiki projection

1.3.0 也提供元件證據：

```python
block = document(op="native", native_request={
    "op": "read_docx_block", "asset_id": asset_id, "revision": revision,
    "block_id": block_id, "text_offset": 0, "text_limit": 1000
})
document(op="native", native_request={
    "op": "verify", "reference": block["block"]["evidence"]
})
document(op="native", native_request={
    "op": "export_wiki", "asset_id": asset_id, "revision": revision,
    "output_dir": "/absolute/path/wiki/sources"
})
```

引用的 hash 涵蓋既有 DFM parser 產生的完整區塊表示，包含 runs、cell formats 及
來源 metadata；80 字預覽或分段文字不參與替代雜湊。`read_docx_block` 回傳 bounded
text、完整文字 hash 與完整 evidence，`representation_complete=false` 表示完整表示
需讀取 Wiki 的 `records.jsonl`。引用驗證核對不可變版本、part/block locator 與表示
hash；目前 managed revision、封存狀態及人類來源是否已同步是各自獨立的狀態。

DOCX Wiki 使用 `docx-blocks-v1` projection，包含各區塊的 Foam note、完整 JSONL
證據、原始 DOCX，以及每個 package part 的原始位元組。`manifest.json` 的
`part_attachments` 保存原生路徑、附件檔名、hash 與大小。DFM 暫存檔名不被假裝成
永久媒體連結；parser 未理解的圖表、嵌入物或特殊內容仍保留在原始檔與套件附件中。
自訂引用的 `{locator}` 使用 `word/document.xml#p...` 等來源 part/block。

新的 projection 會建立不同目錄，保留 1.2.0 的 opaque DOCX 快照；XLSX/XLSM 匯出
內容與連結不變。既有快照若被人工修改，重匯出會拒絕覆蓋。每份匯出上限為
20,000 個區塊、10,000 個套件檔案及總計 128 MiB；超限即拒絕整份匯出。

完整性通過僅代表紀錄可對回指定版本的解析表示，不代表 parser 抽取了每個特徵，
也不代表該段內容支持某項結論。Agent 仍須核對語意、Word 版面、欄位與修訂追蹤。


## Native PPTX (1.4.0)

1.4.0 新增原生簡報能力。先查安裝版本的 `contract`。
PPTX 可直接建立，位置與大小使用 EMU（914400 EMU = 1 inch）：

```python
document(op="native", native_request={
    "op": "create_pptx",
    "presentation": {
        "name": "research.pptx",
        "slides": [{
            "textboxes": [{
                "paragraphs": [[
                    {"text": "研究結果", "bold": True, "font_size_pt": 24},
                    {"text": " — 待核對"}
                ]]
            }],
            "notes": "由 Agent 核對數據、版面與文字溢出。"
        }]
    }
})
```

`read_pptx` 使用 `asset_id`、可選的 `revision`／`offset`／`limit`，回傳
投影片清單與形狀摘要。形狀與投影片清單分別有 `next_offset` 和
`next_slide_offset`；兩者都用 `offset` 續讀。空白投影片仍會列出。
形狀的 locator 包含 `slide_id`、原生 `part`、`region`（slide 或 notes）及
`shape_id`；不要把投影片順序當成檔名或穩定識別。

`read_pptx_shape` 使用回傳的 `pptx_locator`，提供完整形狀表示的 JSON 分段。
保留同一個 `revision`，依 `next_text_offset` 串接 `text_excerpt`，核對
UTF-8 `text_sha256` 後再解析。JSON 包含原始形狀 XML、群組路徑、本地座標、
段落、一般文字 run、欄位、換行與表格儲存格。繼承格式與畫面座標不會臆測。

```python
document(op="native", native_request={
    "op": "update_pptx", "asset_id": asset_id, "expected_revision": revision,
    "pptx_edits": [{
        "locator": {**shape_locator, "paragraph": 0, "run": 0},
        "expected_text_sha256": original_run["text_sha256"],
        "text": "修訂後的文字"
    }]
})
```

`paragraph`／`run` 與表格 `row`／`column` 從 0 開始。`run` 只索引一般
`a:r`，欄位與換行不會佔用 run 索引；以讀取結果提供的索引為準。表格需同時
提供 row 和 column，合併儲存格只可修改起點。更新保留 run 格式及其他 XML，
回傳受管理新版本；來源仍須明確 `writeback`。空字串可清空既有 run，
但不刪除段落、形狀或投影片。

`verify` 可核對 `native-pptx-shape-ref-v1`，舊版本與封存後仍可驗證；
目前版本狀態另外回報。`export_wiki` 使用 `pptx-shapes-v1`，保留形狀筆記、
完整 records.jsonl、原始 PPTX 及每一個原生套件附件。圖片、圖表、內嵌工作簿、
母片、版面、主題及 relationship 檔都保留原始位元組與路徑對照；舊的 opaque
快照不會被取代，人工改動過的受管理筆記會阻擋重新匯出。

Version 1.4.0 scope: transitional `.pptx`, explicit creation and precise existing text-run
updates. Signed/protected presentations, field-run edits, new tabs/line breaks,
merged-cell continuations and structural/style redesign are rejected. Legacy `.ppt`,
macro `.pptm` and strict PresentationML are outside this adapter. Direct slide/notes
shape trees are parsed; unsupported and inherited features remain in exact source
attachments. Package preservation does not prove semantic accuracy, visual fidelity
or extraction completeness. Agents perform the complete review and correction.

## PPTX shape operations (Unreleased)

目前僅 `main` 開發版提供，公開版仍是 1.4.0，後續沿用 1.4.x。
先查 `contract(for_op="add_pptx_shapes")` 或 `delete_pptx_shapes`，確認安裝版本
有提供操作。兩者都要求 `asset_id` 與 `expected_revision`，每批 1–100 個。

`add_pptx_shapes` 的 `pptx_shapes` 指定既有投影片、既有備註或群組容器：

```python
document(op="native", native_request={
    "op": "add_pptx_shapes", "asset_id": asset_id,
    "expected_revision": revision,
    "pptx_shapes": [{
        "container": {
            "slide_id": shape_locator["slide_id"],
            "part": shape_locator["part"],
            "region": shape_locator["region"]
        },
        "textbox": {
            "left": 914400, "top": 914400,
            "width": 3657600, "height": 914400,
            "paragraphs": [[{"text": "待 Agent 核對", "bold": True}]]
        }
    }]
})
```

容器可加 `group_shape_id`。位置使用容器的本地 EMU 座標；既有群組轉換不會
自動重算，零 extent 的群組會拒絕新增。文字框加在容器最後一層（最上層）；
不支援指定插入位置。每批合計最多 20,000 個文字 run／4 MiB UTF-8 文字。
只支援新增文字框；圖片／圖表／投影片建立及重排尚未納入這項操作。

新增後使用回傳的 `review_request` 讀取新版本，依 `next_offset` 續讀形狀清單，
再用 `read_pptx_shape` 分段核對完整表示。既有 `update_pptx` 可修改新文字框的
run。大型操作回應若標為 `response_truncated`，不能把摘要當成完整操作紀錄；
以受管理版本的分頁讀回為準。

`delete_pptx_shapes` 的 `pptx_shape_refs` 必須是目前預期版本讀回的完整
`native-pptx-shape-ref-v1`（含 asset、revision、locator、value_sha256）：

```python
document(op="native", native_request={
    "op": "delete_pptx_shapes", "asset_id": asset_id,
    "expected_revision": current_revision,
    "pptx_shape_refs": [complete_shape["evidence"]]
})
```

刪除群組包含其子形狀；不能同批重複指定形狀或同時指定祖先與子形狀。
仍被連接線、動畫或 build 的已知 shape-ID 引用指向時會拒絕刪除；相依連接線
可和目標同批刪除。檢查涵蓋 `a:stCxn/endCxn @id` 及數值 `spid/shapeid`，
並未涵蓋所有廠商擴充／GUID 相依。Agent 仍須檢查實際開啟與播放結果。

MCP 重新讀回新套件，檢查 ID、套件檔案清單、未修改 part 的原始位元組，並將
指定 XML 操作反向還原後核對其餘 XML。關係、圖片、圖表與內嵌附件即使不再被
形狀使用也會保留，**這不是機密資料清除功能**。舊版本、舊引用與 Wiki 快照
仍可讀取及驗證。操作只建立受管理版本；來源檔另行 `writeback`，保留備份與
來源衝突檢查。MCP 負責這些必要檢查，Agent 負責完整語意／視覺核對與修正。

## PPTX whole-slide previews (Unreleased)

`render_pptx_slide` 回傳整張投影片的實際 PNG，讓 Agent 核對文字、表格遮擋、溢出與版面。
先查 contract 的 `pptx_rendering`，再從 `read_pptx` 取得固定版本的 slide ID／part：

```json
{"op":"render_pptx_slide","asset_id":"file_…","revision":"完整 SHA-256",
 "pptx_slide_key":{"slide_id":"256","part":"ppt/slides/slide1.xml"},"render_size":1024}
```

需要另外安裝 LibreOffice **含 Impress**；可用 `LIBREOFFICE_BIN` 指定執行檔。
`configured` 只表示 adapter 已接線，實際可用性在請求時檢查。僅有 Writer／soffice
不足以轉換 PPTX。回應包含來源版本、slide key、原始順序、隱藏狀態、圖片 SHA-256
與渲染器版本；歷史版本也可預覽。來源與 managed revisions 不會被改寫。

轉檔使用暫存副本和獨立使用者設定，保留完整簡報上下文，包含隱藏投影片、排除備註頁，
核對 PDF 頁數後才取出對應頁。輸入最多 100 張投影片，PNG 最長邊 64–2048 px；
一般 OOXML／PDF 位元組限制及 60 秒執行期限仍適用。外連內容、SVG media、自訂播放
清單與播放範圍目前會拒絕；一般超連結可保留。獨立程序／設定檔不等同 OS 沙箱。

**這是 LibreOffice 靜態預覽。** 字型替代、PowerPoint 差異、動畫及影音播放仍須另行核對；
MCP 不會把「產生圖片成功」視為「視覺驗證通過」。Agent 應比較修改前後畫面與完整原生
內容，必要時提出後續修改。`read_pptx_picture` 則只顯示內嵌圖片，兩者用途不同。
參考 [LibreOffice PDF 匯出選項](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html)
與 [獨立 profile 參數](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)。
公開版本仍為 **1.4.0**，這項功能累積於 **1.4.x／Unreleased**。

## PPTX slide structure (Unreleased)

先查安裝版本的 contract。`read_pptx_layouts` 以 `asset_id`、`revision` 與
`offset`／`limit` 探索所有母片下的版型；沿用同一版本並追蹤 `next_offset`。
每筆提供 `part`、`master_part`、名稱、類型及預留位置數量，不假設固定版型索引。

```python
document(op="native", native_request={
    "op": "add_pptx_slides", "asset_id": deck_id,
    "expected_revision": revision,
    "pptx_slide_insert": {
        "index": 1,
        "slides": [{
            "layout_part": chosen_layout["part"],
            "textboxes": [{"paragraphs": [[{"text": "007 µg", "bold": True}]]}]
        }]
    }
})
```

`index` 為從 0 開始的插入位置，可插在最前、頁與頁之間或最後。每批新增 1–100
頁，使用明確的既有版型。一般文字預留位置依版型建立空內容，母片提示文字不會
變成新頁正文；日期、頁尾及頁碼保留繼承行為。既有版型／母片及其樣式保持原樣。
可另外指定文字框的本地 EMU 尺寸與格式化 runs，或省略 `textboxes`。

以目前版本的 `read_pptx` 完整取得 `slides`，追蹤 `next_slide_offset`。
每頁的 `{slide_id, part}` 是版本內身分；不要用會隨重排改變的顯示頁碼代替：

- `reorder_pptx_slides` 的 `pptx_slide_order` 必須包含全部目前頁面且各出現一次。
- `delete_pptx_slides` 的 `pptx_slide_keys` 指定 1–100 頁，可刪到空簡報。
- 兩者皆需 `asset_id` 與 `expected_revision`。新增後沿用 `review_request`
  讀回新版本；以既有 `read_pptx_shape`／`update_pptx` 核對及修改新文字框。

倖存頁面的 ID、part、圖片、圖表、備註與 XML 保持不變。刪頁會移除主頁序清單
與主簡報關聯，原頁／備註／附件仍留在套件，**不等同安全抹除**。其他保留頁面、
自訂播放或其他 parts 若仍引用被刪頁面，操作會拒絕；屬於被刪頁面的備註回指可保留。
重排不改動自訂播放的獨立順序。章節清單與以頁碼定義的播放範圍目前會阻擋結構
操作，避免自行猜測應如何修改。跨簡報複製／匯入與新增備註結構仍待擴充。

本組操作最多 2,000 頁；新增文字合計最多 20,000 runs／4 MiB UTF-8，並沿用套件
容量與元件上限。MCP 核對版本、相依、頁序、型別關聯、新增內容與未修改 parts，
更新已知的投影片／備註數量屬性。其他檢視器快取屬性可能需重新整理；完整畫面、
文字溢出、繼承樣式與播放互動由 Agent 核對。來源回寫仍需明確操作及備份，
舊形狀證據與 Wiki 原始附件持續可用。

實作參考 [python-pptx 版型語意](https://python-pptx.readthedocs.io/en/latest/user/slides.html)
與 [Microsoft 刪頁相依說明](https://learn.microsoft.com/en-us/office/open-xml/presentation/how-to-delete-a-slide-from-a-presentation)。

## Native PDF pages (Unreleased)

`main` 開發版提供原生 PDF 頁面協作；公開套件仍是 **1.4.0**，後續沿用
**1.4.x**。先用 `contract(for_op="create_pdf")` 確認安裝版本有這些操作。

| 操作 | 用途與必要輸入 |
|------|----------------|
| `create_pdf` | `pdf_create` 的 name、pages；每頁恰好指定 blank 或完整 reference |
| `read_pdf` | asset_id；以 offset／limit 分頁讀取 locator 與頁面幾何 |
| `read_pdf_page` | asset_id、pdf_locator；分段讀取完整頁面 JSON 與 evidence |
| `render_pdf_page` | asset_id、pdf_locator；render_size 為最長邊 64–2048 px，回傳 MCP PNG |
| `add_pdf_pages` | asset_id、expected_revision、pdf_insert（position、pages） |
| `update_pdf` | asset_id、expected_revision、pdf_edits（reference、rotation／crop_box） |
| `delete_pdf_pages` | asset_id、expected_revision、pdf_page_refs；至少保留一頁 |
| `reorder_pdf_pages` | asset_id、expected_revision、pdf_order；每頁完整引用恰好一次 |

`page_index` 從 0 開始。頁面 locator 同時含 object_id 與 generation，僅適用
該不可變版本；寫入後重新讀取新版本，不能沿用舊 locator／引用來修改。
`read_pdf_page` 須固定 revision，沿用 next_text_offset 讀完 text_excerpt，
核對完整 UTF-8 text_sha256 後才解析 JSON。evidence 是
`native-pdf-page-ref-v1`，含 asset、revision、locator 與完整表示的 hash。
原生 text_blocks 不執行 OCR；掃描頁需 Agent 檢視實際 PNG 或另走 OCR／A2T。

```python
# refs 是來源每頁完整讀回的 record["evidence"]。
document(op="native", native_request={
    "op": "create_pdf",
    "pdf_create": {"name": "review.pdf", "pages": [
        {"reference": refs[2]}, {"reference": refs[0]},
        {"blank": {"width": 595, "height": 842}}
    ]}
})
# 以下使用新資產目前版本重新讀回的 current_ref。
document(op="native", native_request={
    "op": "update_pdf", "asset_id": new_asset_id,
    "expected_revision": current_revision,
    "pdf_edits": [{"reference": current_ref, "rotation": 180}]
})
```

rotation 為絕對角度 0／90／180／270。crop_box 是 PDF 原生、未旋轉的
左下原點使用者座標 `[x0,y0,x1,y1]`，必須在 MediaBox 內；單位受 UserUnit
縮放。它不同於 text_blocks 使用的 PyMuPDF 未旋轉 point 座標。頁面紀錄
提供 user_unit 與 coordinate_systems，不應把兩種 bbox 直接混用。

pikepdf/QPDF 負責保留物件關係的編輯，PyMuPDF 獨立讀取文字與像素。
MCP 核對來源／版本、完整物件圖與 encoded stream hash、剩餘頁面相依、
文件屬性、表單登記、存檔後讀回，以及未修改頁面的最長邊 512 px 渲染。
指定旋轉／裁切的頁面由 Agent 另行顯示核對。已知複製造成的 annotation
Popup／Parent／IRT 回指可依來源關係確定性修復，修復後仍須通過完整圖比對。
PDF 物件編號、xref 與檔案 ID 可因存檔改變；不保證整份 PDF 位元組不變。
原始檔與舊版本則保持原始位元組。

同文件操作保留受檢查的書籤／連結、頁標籤、表單、metadata 與附件。
跨文件複製保留選定頁面與可完整整合的表單，不匯入文件層 metadata／附件；
來源引用寫入新資產的歷程。加密、簽章、XFA、需要 parser 修復的檔案、
刪除／複製後懸空的頁面引用、部分表單或欄位改名會被拒絕。跨文件的 tagged
PDF、layer 與 named-destination 整合目前也拒絕，避免默默丟失文件相依。
同批不能重複複製同一來源頁面。每份最多 2,000 頁／64 MiB；新增、複製、幾何修改或刪除每批最多 100 頁。
Worker 有 60 秒期限及支援平台的記憶體上限；超出界限不發布部分結果。

`verify` 可核對舊頁面引用，並另外回報是否仍為目前版本。
`export_wiki` 使用獨立 `pdf-pages-v1` projection：Foam 頁面筆記、完整
records.jsonl、768 px 預覽與完整 PDF 附件，支援既有 citation contract。
舊 opaque 快照保持不變；修改過的受管理筆記會阻擋重用，人工綜合筆記放在旁邊。
更新先建立受管理版本，明確 publish／writeback 才輸出或回寫，回寫保留備份
及來源衝突檢查。任意文字物件編輯、OCR、自動語意校正、機密資料清除皆不在
這個頁面操作範圍；裁切／刪頁不是 secure redaction。Agent 負責完整解析度
版面、語意、表單／檢視器行為、腳本頁索引、閱讀順序與可及性的完整核對與修正。

## PPTX picture assets (Unreleased)

公開版仍是 **1.4.0**，以下是 `main` 的 **1.4.x** 開發內容。先查安裝版本的
`contract.for_op`。人類圖片經 `register` 成為固定 asset_id 與 SHA-256 版本；
回傳的 `file_reference`（`native-file-ref-v1`）代表完整不可變檔案位元組。
任何格式均可用 `verify` 核對這種引用，但檔案 hash 正確不代表模型理解內容，
也不代表磁碟上的人類來源仍未變動；需要時使用 `refresh`。

| 操作 | 必要輸入與結果 |
|------|----------------|
| `add_pptx_pictures` | asset_id、expected_revision、pptx_pictures；插入圖片，回傳新 shape locator |
| `replace_pptx_pictures` | asset_id、expected_revision、pptx_picture_edits；只替換指定形狀的圖片關聯 |
| `read_pptx_picture` | asset_id、pptx_locator；可指定 revision／render_size，回傳實際 MCP PNG 與原始 media hash |
| `extract_pptx_picture` | asset_id、pptx_locator；可指定 revision，建立獨立圖片資產，保留來源簡報／形狀／media 歷程 |
| `delete_pptx_shapes` | 既有操作；以目前版本完整形狀引用刪除圖片，保留底層 media |

```python
# image_asset 是 register 人類 PNG/JPEG 檔的回應；container 由 read_pptx 查得。
document(op="native", native_request={
    "op": "add_pptx_pictures", "asset_id": deck_id,
    "expected_revision": deck_revision,
    "pptx_pictures": [{
        "container": container, "image": image_asset["file_reference"],
        "left": 914400, "top": 914400, "width": 3657600, "height": 1828800,
        "fit": "contain", "name": "Evidence figure", "description": "圖像替代文字"
    }]
})
# 先在新版本完整讀回 read_pptx_shape，不能沿用舊版引用。
document(op="native", native_request={
    "op": "replace_pptx_pictures", "asset_id": deck_id,
    "expected_revision": current_revision,
    "pptx_picture_edits": [{
        "reference": current_picture["evidence"],
        "image": replacement_image["file_reference"],
        "mapping": "preserve_existing"
    }]
})
```

新增支援既有投影片、備註與非零 extent 群組，座標是容器本地 EMU。
`contain` 等比例置中、`cover` 等比例填滿並設定中央裁切、`stretch` 明確拉伸。
圖片加入容器頂層，群組既有 transform 不重算。圖片本身保持原始 PNG／JPEG
位元組，沒有重編碼；name／description 是呼叫者提供的名稱與替代文字。

替換使用 `preserve_existing`：只改 `r:embed` 指向新的圖片關聯，保留位置、
大小、旋轉、翻轉、裁切、效果與堆疊順序。新圖片長寬比不同時，既有映射可能
使內容變形或裁切不同，Agent 必須核對。即使多個形狀共用原圖，其他形狀與
原始圖片 part 都不變。刪圖也保留 media，因此不是機密資料清除。

`read_pptx_picture` 顯示的是**內嵌圖片本身**，不是投影片的最終畫面；
不套用投影片裁切、群組 transform、效果或色彩管理。回應分別提供原圖 SHA、
預覽 PNG SHA、media part 與形狀引用。完整形狀仍用 `read_pptx_shape` 分段
讀回；既有 shape-v1 引用格式保持不變。`extract_pptx_picture` 複製原圖位元組
成新資產，初始歷程記錄來源簡報版本、形狀引用、media part 與 hash。

目前支援經驗證的單幀 PNG／JPEG；EXIF 需旋轉、動畫、多幀、外部連結、
替代圖片表示及不一致的 content type 會拒絕，避免默默選錯顯示來源。
每張最多 16 MiB／1,600 萬像素，每批 1–100 張、合計 32 MiB／6,400 萬像素
（重複來源也計入）；套件整體仍受原生檔案與解壓縮上限保護。

MCP 檢查來源與目標版本、圖片內容、關聯、content type、完整新增位元組及
未變更 part，並反向還原指定 XML 編輯後比對其餘內容。新增與拆出操作保留
跨資產來源歷程。Wiki 沿用 `pptx-shapes-v1`，完整 media／關聯與 PPTX 附件
仍可驗證，既有快照不會改寫。來源 publish／writeback 沿用明確操作、備份與
衝突檢查。Agent 負責實際簡報畫面、語意、替代文字、裁切與色彩的完整核對。

## Native PPTX tables (Unreleased)

`add_pptx_tables` 可在既有投影片、備註或非零大小的群組中新增可編輯表格。
公開版仍是 **1.4.0**，此功能屬於 `main` 的 **1.4.x** 開發內容；先查
`contract.for_op="add_pptx_tables"`，需要時完整讀回分頁 schema。

```python
document(op="native", native_request={
    "op": "add_pptx_tables", "asset_id": deck_id,
    "expected_revision": current_revision,
    "pptx_tables": [{
        "container": container,
        "table": {
            "left": 914400, "top": 914400,
            "column_widths": [2743200, 1828800],
            "row_heights": [457200, 457200, 457200],
            "cells": [
                [{"paragraphs": [[{"text": "結果", "bold": True}]]}, {}],
                [{"paragraphs": [[{"text": "Sample"}]]},
                 {"paragraphs": [[{"text": "Count"}]]}],
                [{"paragraphs": [[{"text": "A101"}]]},
                 {"paragraphs": [[{"text": "007"}]]}]
            ],
            "merges": [{"row": 0, "column": 0, "end_row": 0, "end_column": 1}],
            "name": "結果表", "description": "樣本與顯示數值"
        }
    }]
})
```

座標、欄寬與列高都是容器本地 EMU；表格總寬／高等於各欄／列的合計。
`cells` 必須是相符的矩形，數字、前導零和 `=SUM(...)` 都是原樣文字，
不做公式計算。每格可有多段／多個 run；run 支援文字、粗斜體與整數字級。
儲存格支援 `alignment`（left/center/right）、`vertical_anchor`
（top/middle/bottom）、四邊共同 `margin`，以及六位 RGB `fill_rgb`／`text_rgb`。

合併座標從 0 起算，終點包含在範圍內。範圍不能重疊、反向或超界；除左上角
外，被覆蓋的格子必須是空白預設 `{}`，避免文字或格式默默消失。MCP 先建立
合併，再填入內容，最後核對 XML 中的合併範圍、列欄尺寸、原樣文字與直接格式。

新增表格採目的簡報 `tableStyles` 的預設 GUID，不匯入其他簡報的樣式或 parts；
若沒有樣式關聯，就不臆造樣式 ID。`first_row`、`last_row`、`first_column`、
`last_column`、`row_banding`、`column_banding` 控制對應的樣式角色。
實際字型、主題、框線、裁切、文字溢出與畫面仍需 Agent 在簡報檢視器核對。

新增後使用 `read_pptx_shape` 完整分段讀回格子／文字 run／合併與格式；
`update_pptx` 修改指定格子的 run（合併格只能改左上角），
`delete_pptx_shapes` 使用完整目前版本引用刪除整個表格。
`verify` 和 `export_wiki` 保留歷史表示與完整 PPTX／parts。來源回寫仍須明確
操作並保留來源檢查和備份。列欄結構操作見下一節；A2T 自動橋接與逐格語意來源映射仍待完成。
轉製帳本可連結 PDF 頁面與整個表格的版本引用。

每批 1–100 個表格，每表最多 100 列／100 欄；合計最多 10,000 格、20,000 runs
與 4 MiB UTF-8 文字。每個尺寸及合計寬／高最多 100,000,000 EMU。超界、
來源版本過期、並行更新或任一表格失敗時，不提交部分版本。

### Table grid CRUD (Unreleased)

`update_pptx_table_grid` 可插入、刪除列欄與調整尺寸。先完整讀取目標表格的
`read_pptx_shape` JSON，使用目前完整引用和 `expected_revision`：

```python
document(op="native", native_request={
    "op": "update_pptx_table_grid", "asset_id": deck_id,
    "expected_revision": revision,
    "pptx_table_grid": {
        "reference": full_table_reference,
        "edits": [
            {"op": "insert", "axis": "column", "index": 1, "sizes": [500000]},
            {"op": "resize", "axis": "row", "index": 0, "sizes": [700000]},
            {"op": "delete", "axis": "row", "index": 3, "count": 1}
        ]
    }
})
```

每次接受一個表格與 1–32 個依序執行的操作，`index` 為從 0 開始的當下位置。
`axis` 為 `row` 或 `column`；`sizes` 使用 EMU，刪除使用 `count`。
插入可省略 `cells` 建立空格，或使用與新增表格相同的文字／格式規格，提供
row-major 矩陣：插列為「新增列數 × 現有欄數」，插欄為「現有列數 × 新增欄數」。

插在合併區內部會擴張範圍，插在起點之前會移動範圍；刪除部分列欄會縮小。
若刪到合併起點而仍有格子留下，原起點的內容與格式會移到新左上角；目的格
若含隱藏文字、欄位、關聯、擴充或身分資訊，則拒絕操作。完全刪除的合併區
隨之消失，剩一格則解除合併。新插入的被覆蓋格必須保持預設／空白。

保留其他儲存格 XML、樣式、列欄 metadata、關聯與未修改套件成員；起點移動
會取代目的被覆蓋格的格式。位置不變，外框按新格網合計尺寸及原縮放比例調整。
每個中間格網都須維持 1–100 列／欄、最多 10,000 格、20,000 runs、4 MiB 文字，
合計尺寸及外框最多 100,000,000 EMU；每批最多插入 10,000 格。任何步驟失敗
皆不提交部分版本。舊引用仍可驗證，新版本的格子位置與轉製關係需重新核對。

MCP 核對引用、合併拓樸、尺寸與序列化結果；Agent 仍需核對實際畫面、文字溢出、
主題／條紋樣式及內容意義。合併／拆分見下節；刪除不等同安全抹除。

### Table cell merge/split (Unreleased)

同一個 `update_pptx_table_grid` 的 `edits` 也接受合併與拆分：

```json
[
  {"op":"merge", "row":1, "column":0, "end_row":2, "end_column":1,
   "content_policy":"append_paragraphs"},
  {"op":"split", "row":1, "column":0}
]
```

位置從 0 起算，合併終點包含在內，且至少涵蓋兩格。`content_policy` 必填：

- `require_empty`：左上角以外不可有內容；文字、空白字元、欄位、連結、擴充或
  段落身分等會阻擋操作，避免隱藏資料。
- `append_paragraphs`：將有內容格子的完整段落按「由上到下、由左到右」搬到
  左上角，保留原樣文字、粗斜體、欄位、連結與段落 XML。有內容格中的空段落
  也保留；來源格留下空段落。原起點既有空段落不會被猜測為多餘而刪除。

儲存格屬性、框線與文字框設定留在各自格子，合併後顯示仍由左上角及簡報
樣式決定。既有合併區必須完整包含在新矩形內；部分相交須先拆分，否則拒絕。
`split` 必須指向既有合併區的左上角，只解除合併，**不會把段落分回原格子**。
若要新增格線，可依序拆分、插列／欄、再合併；每一步仍受格網與資源上限檢查。

MCP 檢查完整引用、段落搬移前後 XML、合併結構與序列化結果，並保留未修改
parts。Agent 需重新完整讀取形狀，核對段落順序、格子意義、實際畫面與溢出。
更新仍先建立受管理版本；來源回寫須明確指定。此行為參考
[python-pptx 的合併／拆分語意](https://python-pptx.readthedocs.io/en/latest/user/table.html#un-merging-a-cell)，
並增加明確內容策略與版本檢查。

### Citation display schema (Unreleased)

原生 `export_wiki` 的 `citation_contract` 現在有可探索的型別規格：
`{"preset":"source"}`、`author-year`／`numeric` 預設，或同時提供
`inline_template` 與 `reference_template` 的自訂格式。既有有效 JSON 不變。
這是**引用顯示格式**，不能放入來源引用、驗證報告或任意轉錄資料；正規證據
仍保存在版本、locator、hash 與 Wiki records 中，不能用格式欄位覆寫。

## Native derivations (Unreleased)

Agent 把掃描 PDF 轉成可編輯表格後，兩份檔案各有完整引用，仍需要明確
記錄「產物來自哪裡」。`record_derivation` 保存這個關係；MCP 核對兩端
的不可變版本與定位，Agent 則說明轉製活動，以及實際完成了哪些核對。
公開版仍是 1.4.0；先查目前安裝版本是否宣告 `derivations_enabled`。

對 Agent 而言，可重用的資產需要身分、版本、可讀的表示、可操作能力與
來源關係。帳本補上最後一部分；它保存可檢查的主張，不會自行理解或證明
內容。已有的整份檔案、XLSX 儲存格、DOCX 區塊、PPTX 形狀與 PDF 頁面
引用都能連結；PDF 頁到 PPTX 表格使用頁／形狀粒度，尚非逐格 OCR 映射。

```python
# 先完整讀取來源與產物，再讀取帳本取得 derivations_sha256。
document(op="native", native_request={
    "op": "record_derivation", "asset_id": target_asset_id,
    "expected_derivations_sha256": ledger_hash,
    "derivation": {
        "target": full_target_reference,
        "sources": [full_source_page_reference],
        "activity": "依掃描頁轉錄表格，保留前導零與原始顯示字串",
        "agent": "my-document-agent",
        "review": {
            "semantic_accuracy": "passed",
            "rendered_layout": "not_checked",
            "formula_results": "not_applicable",
            "notes": "已逐項對照來源影像；尚未核對簡報渲染畫面"
        }
    }
})
```

核對狀態可用 `not_checked`、`passed`、`failed`、`not_applicable`。只記錄實際
執行的核對；`agent` 與 review 都是呼叫者聲明，不是身分認證或 MCP 的語意
背書。即使 `references_valid=true`，語意核對仍可是 `failed`。

- `read_derivations(asset_id)`：完整帳本以 canonical JSON 分頁；接續使用
  `text_offset=next_text_offset` 與同一 `derivations_sha256`，串接後核對 UTF-8
  SHA-256。`text_limit` 上限 4,000，編碼後仍有額外大小限制。
- `record_derivation`：使用最新帳本 hash 新增；可在 `derivation.supersedes`
  指定同一資產的活躍紀錄 ID，以單次原子操作修訂聲明。舊紀錄保留。
- `retract_derivation`：使用 `asset_id`、`expected_derivations_sha256` 與
  `retraction={derivation_id, agent, reason}` 撤回。這不會刪除文件或歷史。
- `verify_derivation(asset_id, derivation_id)`：分別回傳關係是否活躍、引用
  完整性、是否仍是目前受管理版本與 Agent 核對狀態。來源查驗結果每頁
  至多 10 筆，依 `next_offset`／`derivations_sha256` 接續；核對備註由完整
  帳本讀取。外部人工作業是否改動來源，仍需另行 refresh／reconcile。

每筆最多 64 個不同來源，每個帳本最多 1,000 個事件與 16 MiB。帳本使用
原生資產相同的操作鎖、hash 比對與原子寫入，文件位元組不變。過期寫入、
不存在的引用、重複來源、對自身的精確引用、撤回不存在／不活躍的紀錄，
以及對已封存產物的修改都會被拒絕。舊版本引用不會自動移到新版本。

`export_wiki` 可帶 `derivations_sha256` 固定此次帳本；快照身分包含帳本
hash，因此修訂／撤回會形成新快照。完整帳本保存在 `derivations.json`；
只針對「活躍且指向匯出版本」的主張重新查驗，附上完整來源檔案與 wikilink
說明。Manifest 列出原始檔名、格式、版本及附件路徑；支援的原生格式保留副檔名，
可直接重新註冊進 MCP，未知格式使用 .bin。總輸出預算仍適用。
其他版本與已撤回紀錄留作歷史，該次匯出不重新查驗／附上它們的來源。
舊 Wiki 與人工整理的筆記不覆寫；`citation_contract` 仍僅控制引用顯示。

此設計參考 [W3C PROV-O 的衍生關係](https://www.w3.org/TR/prov-o/#Derivation)
與 [Docling Graph 的來源帳本](https://github.com/docling-project/docling-graph/blob/main/docs/fundamentals/graph-management/provenance.md)，
並非完整 PROV-O／RDF 格式實作。
