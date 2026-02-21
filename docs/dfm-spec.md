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
├── ir.json                  ← 完整 IR（中間表示），含所有 block 格式元資料
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
checksum: "sha256:..."     # 原始 docx 的 hash，用於偵測外部修改
---
```

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
-->
~~刪除的文字~~**新增的文字**
<!-- /dfm:revision -->
```

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
  └── docx_value_objects.py  # DfmBlockType, BreakType, AnchorType, ...

Infrastructure Layer:
  ├── docx_adapter.py        # DocxAdapter: docx ↔ IR
  ├── dfm_renderer.py        # DfmRenderer: IR → DFM 文字
  └── dfm_parser.py          # DfmParser: DFM 文字 → IR (回寫)

Application Layer:
  └── docx_service.py        # DocxService: 協調 ETL 流程

Presentation Layer:
  └── tools/docx_tools.py    # MCP Tools: ingest_docx, get_dfm, save_docx
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
輸入: doc_id (str), output_path (str, optional)
輸出: 儲存結果摘要
流程: 讀取 content.dfm → 解析 → 合併回 IR → 重建 docx
```

### 8.4 `list_docx_blocks`

```
輸入: doc_id (str), block_type (str, optional)
輸出: block 列表，含 ID、類型、可編輯性、預覽
```

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
