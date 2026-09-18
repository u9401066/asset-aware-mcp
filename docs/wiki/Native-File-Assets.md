# Native File Assets（v1.1.0）

Agent 可以登錄人類交付的檔案，也可以直接建立 XLSX 工作簿。每份檔案都有固定
`asset_id`、不可變的 SHA-256 版本與操作能力；PDF、DOCX 等既有工作流程仍使用
各自的工具。登錄其他格式會保留原始內容，不代表已具備該格式的編輯器。

Native file assets have stable IDs, immutable revisions and explicit format
capabilities. Version 1.1.0 adds XLSX creation and scoped XLSX/XLSM
cell reads/edits through the existing `document` tool. It does not complete
cross-format CRUD, native wiki export or visual fidelity verification.

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
不能交給 PDF `verify_citation_ref`；1.1.0 套件尚未提供原生 wiki／引用格式匯出，
main 的後續實作請見本頁「開發中」章節。

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

## 開發中：原生引用驗證（未包含於 1.1.0）

目前 main 新增 `document(op="native", native_request={"op":"verify", "reference": ref})`，
其中 `ref` 為 `inspect` 或 `read_cell` 回傳的 `evidence` 物件。它核對不可變版本的
檔案 hash、worksheet／cell 定位與完整 cell 表示 hash，回傳 `valid`；另外以
`is_current_managed_revision` 標示是否仍是目前受管理版本。舊引用及已封存資產仍可驗證。
來源人類檔案的新鮮度、語意、視覺與公式計算不在這項完整性核對之內。

This development addition verifies native references against their immutable
revision, including references obtained with a short excerpt. It is separate from
PDF reference verification; native wiki export is described below.

## 開發中：版本固定的 Wiki 匯出（未包含於 1.1.0）

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
