# DFM (Docx-Flavored Markdown) Specification v1.0

> Asset-Aware MCP 的 Word 文件雙向編輯格式規範

## 1. 目標

在 VS Code + MCP 環境中實現 `.docx` 檔案的**無損雙向編輯**：

- **docx → DFM**：解析 Word 文件為人類可讀、可編輯的 Markdown + YAML 元資料
- **DFM → docx**：將編輯後的 DFM 精確還原為 Word 文件，保留所有格式

## 2. 設計原則

1. **可編輯的用 Markdown**：標題、段落、列表、簡單表格、連結、粗體/斜體
2. **不可編輯的用 YAML 封裝**：複雜格式 runs、合併儲存格、嵌入圖表、巨集、頁首頁尾
3. **二進位資產用引用**：圖片、嵌入物件、OLE 物件指向 `assets/` 目錄
4. **XML 部件完整保留**：styles.xml, numbering.xml, settings.xml 等原封保存
5. **Block ID 追蹤**：每個區塊有唯一 ID，確保回寫時精確對應原始段落

## 3. DFM 檔案結構

```
data/docx_{id}/
├── content.dfm              ← 使用者編輯的主文件
├── ir.json                  ← 完整 IR（中間表示），含所有 block 格式元資料；每次儲存更新
├── baseline_ir.json         ← ingest 時的 IR 快照（永不修改；累積回寫的比對基準）
├── edit_state.sqlite3       ← 內容版本歷史、區塊租約（lease）與修訂作者（§12）
├── original.docx            ← 原始檔備份（永不修改）
├── parts/                   ← 無法用 YAML 表達的 XML 部件
│   ├── styles.xml
│   ├── numbering.xml
│   ├── settings.xml
│   ├── header1.xml
│   ├── header2.xml
│   ├── footer1.xml
│   ├── footer2.xml
│   └── footnotes.xml
└── assets/                  ← 媒體資產
    ├── image1.png
    ├── image2.jpg
    ├── chart_01.bin         ← 嵌入圖表二進位
    └── ole_01.bin           ← OLE 物件二進位
```

## 4. DFM 格式語法

### 4.1 Frontmatter（文件元資料）

```yaml
---
dfm_version: "1.0"
source: "研究計畫.docx"
doc_id: "docx_abc123"
created: "2026-02-21T10:00:00"
checksum: "sha256:..."     # 原始 docx 的 hash（來源身分），ingest 後永不改變
revision: "rev-..."        # 這份 DFM 呈現的內容版本；每次成功儲存都會改變（§12）
---
```

`checksum` 只證明 DFM 來自同一份來源 `.docx`；它在儲存後不會改變，因此
不能偵測「別人已經存過」。`revision` 才是內容版本：`save_docx` 用它判斷這份
DFM 是否基於最新狀態，必要時做 3-way merge 或拒絕（見 §12）。`format.yaml`
（split 格式）也帶同一個 `revision` 欄位。

### 4.2 樣式定義區塊

```markdown
<!-- dfm:styles
page_setup:
  size: A4
  orientation: portrait
  margins: {top: 2.54, bottom: 2.54, left: 3.17, right: 3.17}
  header_distance: 1.27
  footer_distance: 1.27
default_font:
  name: "新細明體"
  size: 12
  color: "#000000"
-->
```

### 4.3 段落區塊類型

#### 4.3.1 純文字段落（原生 Markdown）

```markdown
<!-- @b:p001 -->
這是普通段落，直接用 Markdown 編輯。**粗體**和*斜體*正常顯示。
```

- `@b:p001` — Block ID，用 HTML 註解嵌入，md 預覽不可見
- 純文字段落在 md 中完全原生呈現

#### 4.3.2 標題（原生 Markdown）

```markdown
<!-- @b:h001 s:Heading1 -->
# 第一章　緒論
```

- `s:Heading1` — 原始 Word 樣式名稱

#### 4.3.3 混合格式段落（dfm:format）

當一個段落內有**多種字型、顏色、大小**混合時：

```markdown
<!-- dfm:format @b:p002
runs:
  - text: "這段有"
    bold: true
    color: "#FF0000"
    font: "標楷體"
  - text: "混合格式"
    italic: true
    font: "Arial"
    size: 14
  - text: "的文字"
    underline: true
-->
這段有混合格式的文字
<!-- /dfm:format -->
```

- YAML 中的 `runs` 保留精確格式
- runs 下方的純文字是 **fallback 可編輯區**
- 回寫時：比對純文字與 runs 的差異，智慧合併格式

#### 4.3.4 列表（原生 Markdown）

```markdown
<!-- @b:l001 s:ListBullet level:0 -->
- 第一項
<!-- @b:l002 s:ListBullet level:1 -->
  - 子項目
<!-- @b:l003 s:ListNumber level:0 numId:1 -->
1. 編號項目
```

### 4.4 表格區塊

#### 4.4.1 簡單表格

```markdown
<!-- dfm:table @b:t001
style: "Grid Table 4 - Accent 1"
col_widths: [3.5, 2.0, 2.0, 2.5]
-->
| 年度 | 項目 | 預算 | 備註 |
|------|------|------|------|
| Year 1 | 資料收集 | 50萬 | 含人事費 |
| Year 2 | 模型開發 | 80萬 | 含設備 |
<!-- /dfm:table -->
```

#### 4.4.2 合併儲存格表格

```markdown
<!-- dfm:table @b:t002
style: "Grid Table 4 - Accent 1"
col_widths: [3.5, 2.0, 2.0, 2.5]
merged_cells:
  - {row: 0, col: 0, row_span: 1, col_span: 2}
  - {row: 2, col: 1, row_span: 2, col_span: 1}
cell_formats:
  "0:0": {bold: true, align: center, bg_color: "#4472C4", font_color: "#FFFFFF"}
  "0:2": {bold: true, align: center}
-->
| 年度與項目 |  | 預算 | 備註 |
|------------|--|------|------|
| Year 1 | 資料收集 | 50萬 | 含人事費 |
| Year 2 | 模型開發 | 80萬 | 含設備 |
| Year 3 | ^ | 60萬 | 維護 |
<!-- /dfm:table -->
```

- `merged_cells`: 記錄合併資訊，`row_span`/`col_span`
- `cell_formats`: key 格式 `"row:col"`，記錄個別儲存格格式
- `^` 表示被合併的儲存格（垂直合併）
- **文字可編輯**，結構（合併）保護

#### 4.4.3 巢狀表格（Word 特有）

```markdown
<!-- dfm:table @b:t003
nested: true
parent_cell: "1:2"
raw_xml_ref: "parts/nested_table_t003.xml"
-->
📋 *[巢狀表格 — 文字可在下方編輯，結構保護]*

| 子表欄位A | 子表欄位B |
|-----------|-----------|
| 資料1     | 資料2     |
<!-- /dfm:table -->
```

### 4.5 圖片區塊

```markdown
<!-- dfm:image @b:i001
path: "assets/figure1.png"
width_cm: 14.5
height_cm: 8.2
anchor: "inline"
alt: "系統架構圖"
-->
![系統架構圖](assets/figure1.png)
<!-- /dfm:image -->
```

- 圖片存於 `assets/`，md 預覽可見
- `width_cm`/`height_cm` 保留 Word 中的精確尺寸

### 4.6 圖片標題（Caption）

```markdown
<!-- @b:cap001 s:Caption -->
*圖 1：系統架構圖*
```

### 4.7 嵌入圖表（Excel Chart）

```markdown
<!-- dfm:chart @b:c001
type: "embedded_excel"
chart_type: "bar"
data_hash: "sha256:a1b2c3..."
binary_ref: "assets/chart_01.bin"
caption: "圖二：實驗結果分布"
width_cm: 12.0
height_cm: 8.0
-->
📊 *[嵌入圖表：圖二：實驗結果分布]*
*此圖表為嵌入式 Excel 圖表，請用 Word 編輯。*
<!-- /dfm:chart -->
```

- 二進位資料保存於 `assets/`
- DFM 中僅顯示佔位符
- 回寫時原封嵌入

### 4.8 目錄（TOC）

```markdown
<!-- dfm:toc @b:toc001
depth: 3
field_code: 'TOC \\o "1-3" \\h \\z \\u'
style: "TOC Heading"
raw_xml_ref: "parts/toc_block.xml"
-->
🔖 *[目錄 — 自動產生，請勿編輯]*
<!-- /dfm:toc -->
```

### 4.9 頁首 / 頁尾

```markdown
<!-- dfm:header @b:hdr001
type: "default"
xml_ref: "parts/header1.xml"
preview: "研究計畫書 — 第 X 頁"
-->

<!-- dfm:footer @b:ftr001
type: "default"
xml_ref: "parts/footer1.xml"
preview: "國立高雄醫學大學 麻醉科"
-->
```

- 完整 XML 保存於 `parts/`
- DFM 中僅顯示預覽文字

### 4.10 欄位代碼（Field Code）

```markdown
<!-- dfm:field @b:f001
type: "PAGE"
instruction: 'PAGE \\* MERGEFORMAT'
-->

<!-- dfm:field @b:f002
type: "REF"
instruction: 'REF _Ref123456 \\h'
display: "表 1"
-->
```

### 4.11 引用文獻（Bibliography / Citation）

```markdown
<!-- dfm:citation @b:cite001
style: "APA"
entries:
  - key: "Smith2024"
    field_code: 'ADDIN ZOTERO_ITEM CSL_CITATION {...}'
-->
(Smith et al., 2024)
<!-- /dfm:citation -->
```

- Zotero/EndNote 引用欄位的完整 field code 保留
- 顯示文字可編輯

### 4.12 腳註 / 尾註

```markdown
<!-- dfm:footnote @b:fn001
id: 1
-->
[^1]: 這是腳註內容，包含**格式**。
<!-- /dfm:footnote -->
```

在文中引用：`某段文字[^1]`

### 4.13 分頁符 / 分節符

```markdown
<!-- dfm:break @b:br001 type:page -->

<!-- dfm:break @b:br002 type:section next_type:continuous -->

<!-- dfm:break @b:br003 type:section next_type:next_page
page_setup:
  orientation: landscape
  size: A4
-->
```

### 4.14 VBA 巨集

```markdown
<!-- dfm:macro @b:m001
name: "AutoOpen"
binary_ref: "assets/vbaProject.bin"
hash: "sha256:..."
-->
🔧 *[VBA 巨集：AutoOpen — 二進位保護，請用 Word 編輯]*
<!-- /dfm:macro -->
```

### 4.15 OLE 嵌入物件

```markdown
<!-- dfm:ole @b:ole001
prog_id: "Excel.Sheet.12"
binary_ref: "assets/ole_01.bin"
display_name: "嵌入試算表"
width_cm: 10.0
height_cm: 6.0
-->
📎 *[嵌入物件：嵌入試算表 (Excel.Sheet.12)]*
<!-- /dfm:ole -->
```

### 4.16 書籤 (Bookmark)

```markdown
<!-- dfm:bookmark @b:bm001 name:"_Ref123456" -->
```

### 4.17 追蹤修訂 (Track Changes)

```markdown
<!-- dfm:revision @b:rev001
type: "insert"
author: "Dr. Wang"
date: "2026-02-20T14:30:00"
revision_id: "42"
source_tag: "w:ins"
scope: "paragraph"
source_block_id: "p003"
visible_in_current_text: true
-->
~~刪除的文字~~**新增的文字**
<!-- /dfm:revision -->
```

`dfm:revision` 是 Word Track Changes 的唯讀審查區塊，不會在 DFM
回寫時被當成正文編輯。`source_tag` 對應原始 OOXML 修訂節點，例如
`w:ins`、`w:del`、`w:moveFrom`、`w:moveTo`、`w:rPrChange` 或
`w:pPrChange`；`visible_in_current_text` 可協助 agent 區分目前正文可見的
插入/移入文字與已刪除/移出的文字。

## 5. 格式合併策略

### 5.1 文字回寫規則

當使用者在 DFM 中編輯了 `dfm:format` 區塊的 fallback 純文字：

1. **小幅修改（差異 <30%）**：按原始 runs 的字元比例重新分配文字
2. **大幅修改（差異 ≥30%）**：用第一個 run 的格式套用到全部新文字
3. **純 Markdown 段落**：直接使用段落預設樣式

### 5.2 表格回寫規則

1. 解析 md 表格的純文字內容
2. 對應到原始 `merged_cells` 結構
3. 保留 `cell_formats` 中的格式
4. 如果行數/列數改變，警告使用者合併儲存格可能受影響

### 5.3 保護區回寫規則

以下 block type 的內容在回寫時**完全從 `parts/` 或 `assets/` 還原**，DFM 中的佔位符文字不影響：

- `dfm:chart`（嵌入圖表）
- `dfm:toc`（目錄）
- `dfm:header` / `dfm:footer`（頁首/頁尾）
- `dfm:macro`（巨集）
- `dfm:ole`（OLE 物件）
- `dfm:field`（欄位代碼）

## 6. Block ID 規範

| 前綴 | 類型 | 範例 |
|------|------|------|
| `p` | 段落 | `p001`, `p002` |
| `h` | 標題 | `h001`, `h002` |
| `l` | 列表項 | `l001`, `l002` |
| `t` | 表格 | `t001`, `t002` |
| `i` | 圖片 | `i001`, `i002` |
| `c` | 圖表 | `c001`, `c002` |
| `cap` | 標題 (Caption) | `cap001` |
| `toc` | 目錄 | `toc001` |
| `hdr` | 頁首 | `hdr001` |
| `ftr` | 頁尾 | `ftr001` |
| `f` | 欄位代碼 | `f001` |
| `fn` | 腳註 | `fn001` |
| `br` | 分隔符 | `br001` |
| `m` | 巨集 | `m001` |
| `ole` | OLE 物件 | `ole001` |
| `bm` | 書籤 | `bm001` |
| `cite` | 引用 | `cite001` |
| `rev` | 修訂 | `rev001` |

## 7. DDD 架構映射

```
Domain Layer:
  ├── docx_entities.py      # DocxIR, DfmBlock, FormatRun, MergedCell, ...
  ├── docx_value_objects.py  # DfmBlockType, BreakType, AnchorType, ...
  └── docx_edit_state.py     # 內容 revision、3-way merge 規則、區塊租約 (§12)

Infrastructure Layer:
  ├── docx_adapter.py        # DocxAdapter: docx ↔ IR
  ├── dfm_renderer.py        # DfmRenderer: IR → DFM 文字
  ├── dfm_parser.py          # DfmParser: DFM 文字 → IR (回寫)
  └── docx_edit_state_store.py  # SQLite: revision 歷史、租約、跨 process 鎖

Application Layer:
  ├── docx_service.py        # DocxService: 協調 ETL 流程
  ├── docx_concurrency.py    # 受鎖編輯 session、revision 追蹤、3-way merge
  └── docx_block_leases.py   # checkout / commit / release / renew / leases

Presentation Layer:
  └── tools/docx_tools.py    # MCP Tools: ingest_docx, get_dfm, save_docx, docx(op=...)
```

## 8. MCP Tools 規格

### 8.1 `ingest_docx`

```
輸入: file_path (str) — docx 檔案路徑
輸出: doc_id, block 數, asset 數, dfm_path
流程: docx → IR → DFM + parts/ + assets/
```

### 8.2 `get_docx_content`

```
輸入: doc_id (str)
輸出: DFM 文字內容（可直接在 VS Code 編輯）
```

### 8.3 `save_docx`

```
輸入: doc_id (str), dfm_content (str, optional), output_path (str, optional),
      track_changes (bool, optional), revision_base ("original" | "last_save")
輸出: 儲存結果摘要（changed_block_ids = 相對 original.docx 的所有變更區塊，
      edited_block_ids = 本次請求修改的區塊，revision = 新內容版本，
      revision_merge = current | merged | legacy）
流程: 取得文件鎖 → 解析 DFM → 以 front matter `revision` 判斷基準（必要時
      3-way merge 或拒絕，§12）→ 拒絕被他人租用的區塊 → 合併回目前 IR (ir.json)
      → 與 baseline_ir.json 比對取得自 ingest 以來的累積變更 → 以 original.docx
      為底重建 docx → post-save 驗證 → 記錄新 revision 並原子寫入所有 artifacts
```

`force=True` 只覆寫內容大量縮減的 fail-safe、post-save integrity 失敗與來源
checksum 不符；**永遠不會**略過 revision 衝突或 lease。

**累積寫回**：`original.docx` 與 `baseline_ir.json`（ingest 時的 IR 快照）在
ingest 後永不修改。每次儲存都把「目前 IR 與 baseline 的所有差異」寫回
`original.docx` 的副本，因此先前儲存過的編輯不會在後續儲存中遺失；未編輯的
區塊與其他 package parts 保持位元組不變，全部編輯還原時輸出即為
`original.docx` 的位元組複本（可逆）。Post-save integrity check 以
`original.docx` 為基準驗證每個預期的 paragraph/table cell 差異都存在，遺失的
編輯會讓儲存失敗。

缺少 `baseline_ir.json` 的舊版（v1.4.1 以前）文件目錄，會在驗證
`original.docx` SHA-256 等於 IR checksum、且重新解析的 block 結構與 `ir.json`
一致後重建基準；任一驗證失敗即拒絕儲存並要求重新 ingest，不做猜測。

`output_path` 必須位於 `data/{doc_id}/` 內且不可覆寫保留檔；要回寫使用者
來源檔請使用 native 流程（`register` → `update_docx` → `writeback`，具
`expected_revision` / `expected_source_sha256` 與來源 stat 過期檢查）。

`track_changes=True` 為 opt-in 行為；預設仍使用原本的直接文字回寫。啟用後，
`save_docx` 會比較修訂基準 IR 與 edited IR，將文字級差異寫成真正 Word Track
Changes：刪除片段使用 `w:del` + `w:delText`，新增片段使用 `w:ins` + `w:t`，
並在 `word/settings.xml` 補上 `w:trackRevisions`。修訂基準預設為
`revision_base="original"`（ingest baseline：顯示自 ingest 以來的全部編輯）；
`revision_base="last_save"` 會先把先前儲存的編輯以已接受文字寫入，再只把本次
相對上次儲存狀態的差異標為修訂。要求追蹤修訂卻沒有產生任何新的
`w:ins`/`w:del` 時，post-save 檢查會失敗。這讓使用者可在 Word 中逐項
接受/拒絕 AI 於 DFM 中造成的修改，也讓 citation-ready 拆解可以保留「哪一段
原文被哪一段新文取代」的細顆粒審查線索。

同時會寫出 `revisions.jsonl` sidecar。每筆 record 使用
`asset-aware.docx-revisions.v1` schema，包含 `doc_id`、`source_revision_id`、
`revision_id`、`revision_base`、`block_id`、`op`、old/new text hash、char/byte
range、短 context 與 locator 欄位。下游若要建立 Foam/LLM wiki citation anchor，
應以這份 sidecar 銜接 Word 可視修訂與 Asset-Aware 的 block/span locator，而不是
重新猜測 diff。

### 8.4 `list_docx_blocks`

```
輸入: doc_id (str), block_type (str, optional)
輸出: block 列表，含 ID、類型、可編輯性、預覽
```

### 8.5 `docx` facade：區塊租約（多 agent 併發編輯）

```
docx(op="checkout", doc_id, block_ids, holder, ttl_seconds=900)
docx(op="commit",   doc_id, lease_token, edits={block_id: fragment},
     output_path?, track_changes?, revision_author?, revision_base?,
     keep_lease?, force?)
docx(op="release",  doc_id, lease_token)
docx(op="renew",    doc_id, lease_token, ttl_seconds?)
docx(op="leases",   doc_id)
docx(op="break_lease", doc_id, lease_id, force?)
```

詳細語意見 §12。

## 9. 限制與已知約束

1. **複雜排版**：多欄排版 (column layout) 在 md 中無法視覺呈現，但格式資料完整保留
2. **嵌入字型**：如 docx 嵌入了自訂字型，DFM 無法預覽但會保留
3. **巨集安全性**：VBA binary 原封保留，不做任何解析或修改
4. **大檔案**：超過 50MB 的 docx（含大量圖片）可能需要非同步處理
5. **密碼保護**：加密的 docx 不支援（需先解密）

## 10. 依賴

- `python-docx >= 1.1.0`：docx 解析與重建
- `lxml >= 5.0.0`：XML 處理（python-docx 已內含）
- 現有依賴：`pydantic`, `aiofiles`, `Pillow`

## 11. 格式互轉保真度

DFM round-trip (DOCX → DFM → DOCX) 經過 3 次迴圈測試驗證為 **100% 冪等**——所有 6 個維度（Structure, Text, Format, Table, Media, Style）零退化。

跨格式轉換 (DOCX ↔ DOC, DOCX ↔ ODT) 保真度為 **94.5%**，損失來自 LibreOffice 轉換引擎的格式模型差異。

> 完整測試報告見 [`docs/format-conversion-report.md`](format-conversion-report.md)

## 12. 內容版本（revision）、3-way merge 與區塊租約（lease）

多個 agent（例如 Claude Code subagents、Copilot、Cline、Codex）可以同時編輯
**同一份**文件的不同部分，而且可能各自執行獨立的 MCP server process、共用同一個
`DATA_DIR`。本節的機制保證任何一方的已儲存編輯都不會被默默覆蓋。

### 12.1 內容版本（content revision）

- `revision = "rev-" + sha256(canonical JSON {checksum, [(block_id, block_hash)…]})[:32]`，
  其中 `block_hash` 是 `ir.json` 中該 block 記錄的 SHA-256。相同內容一定得到
  相同 revision，因此可隨時從 `ir.json` 重新計算，不需要另存「目前版本」指標。
- Ingest、每次 `save_docx`、每次 lease commit 與 `docx_table_from_context` 都會
  產生新 revision，寫入 `content.dfm` front matter 與 `format.yaml`，並記錄在
  `edit_state.sqlite3`。
- 歷史以「相對 root 的差異」保存：root（通常是 ingest baseline）完整保存每個
  block 一次；之後的 revision 只存與 root 不同的 `block_id → hash`。Block 內容以
  content-addressed、zlib 壓縮 JSON 保存。保留最新 50 個 revision 加 root，
  被淘汰的 revision 不能再作為 3-way merge 基準；不再被引用的 block 內容會被回收。
- `ir.json` 若在追蹤之外被修改（例如舊版工具或 crash 復原），下一次受鎖操作會把
  目前狀態記錄為 `external` revision，因此基於舊 revision 的 DFM 仍能正確 merge。

### 12.2 `save_docx` 的 revision 判斷

| 提交的 DFM | 行為 |
|---|---|
| `revision` = 目前 revision | 正常儲存 |
| `revision` 是較舊、仍保留的 revision | **3-way merge**：base = 該 revision 的區塊內容，ours = 提交的 DFM，theirs = 目前 IR。只套用提交者相對 base 改過的區塊；若其中任何區塊在 base 之後也被別人改過，整個儲存被拒絕並回傳 `conflict_block_ids`（若提交者的結果與目前內容完全相同，例如重試同一個儲存，視為 already applied，不算衝突） |
| `revision` 不在保留歷史中 | 拒絕，要求重新開啟目前 DFM |
| 沒有 `revision`（1.5.0 以前或手寫） | 只有在 ingest 後從未儲存（版本歷史只有 root、內容等於 ingest 狀態、`.backups/` 為空）時接受；或 DFM 內容與目前完全相同（不可能覆蓋任何人）時接受；其他情況拒絕並提示重新開啟或改用 lease |

被拒絕時不會寫入任何檔案。`force=True` 不影響以上判斷。透過
`save_docx` 自動合併的 pending `TableContext` 會保留原 DFM 的 `revision`，不會把
過期的 DFM 誤標成最新。

### 12.3 區塊租約（block checkout / lease）

1. **checkout** — `docx(op="checkout", doc_id, block_ids, holder, ttl_seconds)`
   回傳 `lease_token`（秘密，只存 SHA-256）、公開的 `lease_id`、每個區塊的 DFM
   片段（含 marker 行）與 `base_hash`、文件 `revision`、`expires_at`。
   - 任何區塊已被其他**未過期**租約持有時立即失敗（回報 holder、lease_id、
     到期時間）；不支援阻塞等待（`wait=true` 會被拒絕）。
   - 已過期的租約不會阻擋，其區塊會被新的 checkout 回收（`expired_reclaimed`）。
   - 巢狀表格的文字位於父表格的儲存格內，因此父表格與其所有巢狀表格一起租用
     （`expanded_block_ids`）。
   - 只能租用段落、標題、清單項目、caption、混合格式段落與表格；受保護/結構性
     區塊（圖表、TOC、欄位、圖片、分隔符、頁首頁尾）會被拒絕。
   - TTL 預設 900 秒、上限 3600 秒；每份文件最多 256 個有效租約、每個租約最多
     500 個區塊。
2. **commit** — `docx(op="commit", doc_id, lease_token, edits={block_id: fragment})`
   - 只接受租約內的區塊；每個片段只能含**自己的** marker（或不含 marker 的純文字，
     會依區塊型別自動包裝），不能改變區塊種類，也不能夾帶其他區塊。
   - 以**目前**文件為基礎套用（rebase），其他 holder 已 commit 的區塊保留。
   - 驗證每個區塊仍是 checkout 時的 `base_hash`（租約保證只有 holder 能改；若因
     中斷的前次 commit 已含相同內容，視為 already applied）。
   - 表格只允許儲存格文字修改；列/欄數變更被拒絕並提示改用 Word 或 native
     `update_docx_table_grid`。
   - 走與 `save_docx` 相同的累積寫回與 post-save 驗證，產生新 revision，並預設
     釋放租約（`keep_lease=true` 則保留、更新 base hash 並以原 TTL 續期）。
   - `track_changes=true` 時 `revision_author` 預設為 holder。
3. **release / renew / leases / break_lease**
   - `release` 不編輯直接歸還（過期租約也可釋放）；`renew` 只能延長未過期租約。
   - `leases` 列出 holder、區塊、狀態（live/expired）、到期時間與目前 revision，
     **不會**顯示 token。
   - `break_lease` 是管理操作：預設只能移除已過期租約；移除有效租約需要
     `force=true`，且應先確認 holder 已不存在（其後 commit 會失敗並說明被 break）。
   - 已釋放/已 commit/被 break/被回收的租約留下有上限的事件紀錄，使用舊 token 時
     會得到明確原因。

租約在所有寫入路徑都有效：`save_docx` 會拒絕修改被他人租用的區塊（回傳
`leased_blocks`），`docx_table_from_context` 也一樣；有有效租約時重新
`ingest_docx` 會被拒絕。Agent 不應在閒置期間持有租約：編輯完立即 commit，
放棄時 release，只在實際編輯中 renew。

### 12.4 每個 holder 的 Track Changes 作者

`edit_state.sqlite3` 記錄每個區塊最後由誰修改（`save_docx` 為
`revision_author`，commit 為 holder 或指定作者）。`track_changes=true` 且
`revision_base="original"` 時，輸出中每個區塊的 `w:ins`/`w:del` 使用該區塊的
作者，Word 因此能顯示哪個 agent 改了哪一段；`revisions.jsonl` 每筆紀錄也帶
`revision_author`。同一區塊被多人改過時歸屬最後修改者。`revision_base="last_save"`
只追蹤本次請求的變更（作者為本次作者）。輸出的 tracked/plain 形式由最後一次
儲存/commit 的 `track_changes` 決定，多 agent 工作時請一致使用相同設定。

### 12.5 跨 process 鎖與原子性

- 每個寫入操作（save、checkout、commit、release、renew、break、
  `docx_table_from_context`、re-ingest）都在 `edit_state.sqlite3` 的
  `BEGIN IMMEDIATE` 交易中執行：同一份文件同一時間只有一個寫入者，跨 thread 與
  跨 process 皆然；等待上限 30 秒，逾時回傳「Document is busy」且不做任何變更。
  Process 死亡時 OS 釋放鎖，SQLite journal 會回滾未完成交易。
- 發布順序：先在交易中寫入 revision/租約變更 → 建立備份 → 取代輸出 DOCX →
  寫入 `ir.json`（內容的 commit point）→ 寫入 `content.dfm`/`content.md`/
  `format.yaml` → 交易 commit。`ir.json` 寫入失敗時會還原先前的輸出 DOCX 並回滾
  交易；所有文字 artifacts 以「暫存檔 + fsync + rename」原子寫入。
- 若 process 恰好在 `ir.json` 寫入後、交易 commit 前崩潰：交易回滾（租約仍有效），
  下一次受鎖操作把 `ir.json` 狀態記錄為 `external` revision；holder 重試同一個
  commit 會被辨識為 already applied 並正常釋放租約；仍持有舊 DFM 的 client 會被
  3-way merge 處理，不會遺失內容。崩潰可能留下 `.*.tmp.docx` / `.*.tmp.prev`
  暫存檔，可安全刪除。
- 鎖依賴本機檔案系統的 SQLite 檔案鎖；不建議把 `DATA_DIR` 放在網路磁碟或雲端
  同步資料夾。

### 12.6 Native DOCX 路徑

`document(op="native")` 的 `update_docx` 等 native 操作維持**文件層級**的
`expected_revision`：native revision 是不可變、content-addressed 的檔案，block ID
只在單一 revision 內有效，因此不提供區塊租約。過期時的錯誤訊息會指出目前
revision，並提示需要多 agent 併發編輯時改用上述 DFM lease 流程。
