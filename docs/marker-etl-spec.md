# Marker ETL 規格書：PDF 結構化拆分

**Version:** 1.0.0  
**Date:** 2026-02-09  
**Status:** Draft  
**Owner:** Asset-Aware MCP Team  

---

## 0. 概述

### 0.1 本規格的目的

定義使用 **Marker** 作為 PDF 結構化拆分引擎的：

1. **輸入/輸出契約** — 明確每個產出物（artifact）的格式與品質要求
2. **驗收標準** — 每項功能的 pass/fail 判定基準
3. **測試策略** — 三層測試架構，從 unit → integration → benchmark

### 0.2 為什麼選 Marker？

| 維度 | PyMuPDF (現有) | Marker (新增) |
|------|---------------|--------------|
| Section 結構 | ❌ 從 markdown `#` 啟發式解析，常誤判 | ✅ AI 模型辨識 SectionHeader，帶 section_hierarchy |
| 表格辨識 | ⚠️ find_tables() 僅限簡單格線 | ✅ 表格結構化, block_type=Table |
| 圖片提取 | ⚠️ 原始 XObject，含小圖標/裝飾 | ✅ Figure block 語意辨識 |
| Figure Caption | ❌ 無 | ✅ 從上下文推斷 |
| 來源追蹤 | ❌ 無 bbox | ✅ polygon + bbox + page |
| 依賴大小 | ~5MB | ~1GB (首次下載模型) |

### 0.3 雙引擎策略

```
ingest_documents(file_paths, use_marker=False)  ← PyMuPDF (預設，快速)
ingest_documents(file_paths, use_marker=True)   ← Marker (精確，較慢)
```

兩者都會產出 `manifest.json`，但 Marker 額外產出 `blocks.json`。

---

## 1. 輸入規格

### 1.1 支援的輸入

| 類型 | 格式 | 限制 |
|------|------|------|
| PDF | `.pdf` | 單檔上限 100MB |
| 語言 | 英文、中文 | Marker 預設支援多語言 |
| 內容 | 學術論文、教科書、技術報告 | 主要對象 |

### 1.2 不支援的輸入

- 影印本 PDF（純圖片，無文字層）— 需 OCR 前處理
- 加密 PDF — 需先解密
- 非 PDF 格式（Word, PowerPoint）— 未來可擴展

---

## 2. 輸出規格（Artifacts）

每個文件的輸出儲存在 `data/{doc_id}/` 目錄下：

```
data/{doc_id}/
├── {doc_id}_full.md          # [A1] 全文 Markdown
├── {doc_id}_manifest.json    # [A2] 文件地圖（Manifest）
├── blocks.json               # [A3] 結構化 Blocks（Marker 專屬）
└── images/                   # [A4] 提取的圖片
    ├── fig_1.png
    ├── fig_2.png
    └── ...
```

### 2.1 [A1] 全文 Markdown — `{doc_id}_full.md`

**格式要求：**

| 項目 | 規格 |
|------|------|
| 編碼 | UTF-8 |
| 標題層級 | `# H1` ~ `###### H6`，反映原文結構 |
| 表格 | Markdown 表格語法 `| col | col |` |
| 列表 | `- ` 或 `1. ` 標準 Markdown |
| 圖片引用 | `![alt](images/fig_N.png)` 或內嵌 |
| 頁面標記 | `<!-- Page N -->` 或 Marker 原生標記 |
| 數學公式 | LaTeX 格式 `$...$` 或 `$$...$$`（如 Marker 支援） |

**品質要求：**

- [ ] **QM-1**: 輸出不為空（`len(markdown) > 0`）
- [ ] **QM-2**: 包含至少一個標題（`# ` 開頭的行）
- [ ] **QM-3**: 表格保留原始結構（行列數一致）
- [ ] **QM-4**: 無亂碼（可讀的 UTF-8 文字）

---

### 2.2 [A2] 文件地圖 — `{doc_id}_manifest.json`

**Schema：**

```json
{
  "doc_id": "string",
  "filename": "string (原始檔名)",
  "title": "string (文件標題)",
  "toc": ["string (章節標題列表)"],
  "assets": {
    "tables": [TableAsset],
    "figures": [FigureAsset],
    "sections": [SectionAsset]
  },
  "lightrag_entities": ["string"],
  "page_count": "int",
  "created_at": "datetime",
  "markdown_path": "string",
  "manifest_path": "string"
}
```

**品質要求：**

- [ ] **QF-1**: 可被 `DocumentManifest.model_validate()` 成功解析
- [ ] **QF-2**: `doc_id` 格式為 `doc_{stem}_{hash}`
- [ ] **QF-3**: `page_count > 0`
- [ ] **QF-4**: `title` 不為空且不含 artifacts（如 arxiv ID、亂碼）
- [ ] **QF-5**: `toc` 列表反映原文真實章節標題

#### 2.2.1 TableAsset Schema

```json
{
  "id": "tab_{N}",
  "page": "int (1-indexed)",
  "caption": "string",
  "preview": "string (前 100 字元)",
  "markdown": "string (完整 Markdown 表格)",
  "row_count": "int (≥ 1)",
  "col_count": "int (≥ 1)",
  "has_header": "bool",
  "source": "marker"
}
```

**品質要求：**

- [ ] **QT-1**: 每個 Table block 都被轉為 TableAsset
- [ ] **QT-2**: `markdown` 欄位可被 Markdown 解析器正確渲染
- [ ] **QT-3**: `row_count` 和 `col_count` 與 markdown 內容一致
- [ ] **QT-4**: `page` 為正確的頁碼（與原 PDF 對照）

#### 2.2.2 FigureAsset Schema

```json
{
  "id": "fig_{N}",
  "page": "int (1-indexed)",
  "path": "string (圖片檔案路徑)",
  "ext": "string (png/jpg/jpeg)",
  "caption": "string (圖說，如有)",
  "width": "int (pixels, ≥ 0)",
  "height": "int (pixels, ≥ 0)",
  "figure_type": "string",
  "source": "marker"
}
```

**品質要求：**

- [ ] **QI-1**: 圖片檔案實際存在於 `images/` 目錄
- [ ] **QI-2**: 過濾小圖標（寬或高 < 50px 的圖片應被排除或標記）
- [ ] **QI-3**: 圖片可被正常開啟（有效的 PNG/JPEG）
- [ ] **QI-4**: `page` 為正確的頁碼
- [ ] **QI-5**: `caption` 不為空（當原文有圖說時）

#### 2.2.3 SectionAsset Schema

```json
{
  "id": "sec_{N}",
  "title": "string (章節標題)",
  "level": "int (1=H1, 2=H2, ...)",
  "page": "int (1-indexed)",
  "start_line": "int",
  "end_line": "int",
  "preview": "string"
}
```

**品質要求：**

- [ ] **QS-1**: Section 標題與原文一致（不含行號、頁碼等 artifacts）
- [ ] **QS-2**: `level` 正確反映章節層級
- [ ] **QS-3**: 章節排列順序與原文一致
- [ ] **QS-4**: 不遺漏主要章節（Abstract, Introduction, Methods, Results, Discussion 等）

---

### 2.3 [A3] 結構化 Blocks — `blocks.json`（Marker 專屬）

**這是 Marker 最核心的差異化產出。**

**Schema：**

```json
[
  {
    "block_id": "blk_0001",
    "block_type": "SectionHeader | Text | Table | Figure | ListItem | Equation | ...",
    "page": 1,
    "text": "string (截斷至 500 字元)",
    "bbox": [x0, y0, x1, y1],
    "polygon": [[x,y], ...],
    "section_hierarchy": {
      "1": "Chapter Title",
      "2": "Section Title",
      "3": "Subsection Title"
    },
    "metadata": {
      "id": "string (Marker 原生 ID)",
      "level": "int (for SectionHeader)"
    }
  }
]
```

**品質要求：**

- [ ] **QB-1**: blocks 不為空（`len(blocks) > 0`）
- [ ] **QB-2**: 每個 block 都有 `block_id`（格式 `blk_NNNN`，唯一）
- [ ] **QB-3**: `block_type` 為已知類型之一
- [ ] **QB-4**: `page` 為 1-indexed 且 `1 ≤ page ≤ page_count`
- [ ] **QB-5**: `bbox` 非空且格式正確 `[x0, y0, x1, y1]` where `x0 < x1, y0 < y1`
- [ ] **QB-6**: `section_hierarchy` key 為數字字串（"1", "2", ...），value 為非空字串
- [ ] **QB-7**: SectionHeader blocks 的 `section_hierarchy` 正確反映層級
- [ ] **QB-8**: blocks 按頁碼和位置排序

---

### 2.4 [A4] 圖片目錄 — `images/`

**品質要求：**

- [ ] **QG-1**: 所有 FigureAsset 引用的圖片都存在
- [ ] **QG-2**: 圖片格式為 PNG 或 JPEG
- [ ] **QG-3**: 無損壞的圖片檔案（可被 PIL/Pillow 開啟）
- [ ] **QG-4**: 有意義的圖片（非空白、非純色塊）

---

## 3. Section Tree 功能規格

### 3.1 從 blocks.json 建構 Section Tree

`SectionService` 從 `blocks.json` 動態建構章節樹，支援任意深度。

**輸入**：`blocks.json`（含 `section_hierarchy`）  
**輸出**：`SectionTree` 物件

**品質要求：**

- [ ] **QST-1**: 樹的根節點標題為文件標題
- [ ] **QST-2**: 樹的 `max_depth` 反映實際最大層級
- [ ] **QST-3**: 所有 blocks 都歸屬於某個 section node
- [ ] **QST-4**: section node 的 `block_count` 為正確的累計值
- [ ] **QST-5**: section node 的 `page_start/page_end` 正確反映頁碼範圍

### 3.2 MCP Tools

| Tool | 輸入 | 輸出 | 用途 |
|------|------|------|------|
| `list_section_tree` | `doc_id`, `max_depth`, `format` | 樹狀結構 | 瀏覽文件章節結構 |
| `get_section_detail` | `doc_id`, `path` | 章節詳情 | 檢視特定章節 |
| `get_section_blocks` | `doc_id`, `path`, `include_children` | block 列表 | 取得章節內容 |
| `search_sections` | `doc_id`, `query` | 匹配結果 | 搜尋章節 |

**品質要求：**

- [ ] **QMT-1**: 無 `blocks.json` 時回傳清晰錯誤提示
- [ ] **QMT-2**: `list_section_tree` 三種格式（tree/flat/json）都正確
- [ ] **QMT-3**: `get_section_blocks` 支援 `include_children` 開關
- [ ] **QMT-4**: `search_sections` 支援模糊搜尋

---

## 4. 錯誤處理規格

### 4.1 Marker 不可用時

```python
# Marker 未安裝或模型載入失敗
if use_marker and self.marker_extractor is None:
    return IngestResult(success=False, error="Marker extractor not available")
```

### 4.2 PDF 解析失敗

```python
# Marker 解析過程中發生錯誤
return IngestResult(
    success=False,
    error=f"Marker parsing failed: {str(e)}\n{traceback.format_exc()}"
)
```

### 4.3 Graceful Degradation

| 狀況 | 行為 |
|------|------|
| Marker 未安裝 | 自動降級為 PyMuPDF |
| 模型下載失敗 | 回傳明確錯誤 |
| 部分 block 解析失敗 | 跳過該 block，繼續處理 |
| 圖片提取失敗 | 記錄警告，繼續處理 |
| LightRAG 不可用 | 跳過知識圖譜索引 |

**品質要求：**

- [ ] **QE-1**: 任何錯誤都不會導致未捕獲例外
- [ ] **QE-2**: 錯誤訊息包含可操作的修復建議
- [ ] **QE-3**: 部分失敗不影響已成功的部分

---

## 5. 測試策略

### 5.1 測試金字塔

```
        ╱  E2E/Benchmark  ╲     ← 少量，需真實 PDF + 人工標註
       ╱    Integration     ╲    ← 中量，需 Marker 模型
      ╱     Unit Tests       ╲   ← 大量，純邏輯，無 I/O
     ╱━━━━━━━━━━━━━━━━━━━━━━━━╲
```

### 5.2 Level 1: Unit Tests（無 PDF、無 Marker）

位置：`tests/unit/test_marker_*.py`

| 測試檔案 | 測試對象 | 測試項目 |
|----------|----------|----------|
| `test_marker_blocks.py` | `MarkerBlock`, `MarkerParseResult` | 資料模型驗證 |
| `test_marker_conversion.py` | `_convert_blocks_to_json`, `_extract_tables_from_blocks` | Block → Asset 轉換 |
| `test_section_tree.py` | `SectionNode`, `SectionTree` | 樹狀結構建構與查詢 |
| `test_section_service.py` | `SectionService` | 服務層邏輯（mock blocks.json） |

#### Unit Test 詳細案例

**test_marker_blocks.py:**
```
✓ MarkerBlock 建立與欄位預設值
✓ MarkerBlock bbox 格式驗證
✓ MarkerBlock section_hierarchy 不可變更共享
✓ MarkerParseResult 所有欄位正確初始化
```

**test_marker_conversion.py:**
```
✓ blocks 轉換截斷長文字（> 500 字元）
✓ Table block 正確轉為 TableAsset
✓ 無 Table block 時回傳空列表
✓ SectionHeader TOC 正確轉為 SectionAsset
✓ Figure block 正確對應 FigureAsset 頁碼
✓ IngestResult.backend 欄位為 "marker"
```

**test_section_tree.py:**
```
✓ 空 blocks 建構空樹
✓ 單層 section hierarchy 正確建構
✓ 多層 section hierarchy 正確建構（3+ 層）
✓ find_section 支援字串路徑 "Ch1/Sec1/Sub1"
✓ find_section 支援列表路徑 ["Ch1", "Sec1"]
✓ search_sections 模糊搜尋正確匹配
✓ get_blocks_for_section 含/不含子節點
✓ block_count 正確累計
✓ page_start/page_end 正確範圍
✓ estimate_tokens 合理估算
```

**test_section_service.py:**
```
✓ blocks.json 不存在時回傳錯誤訊息
✓ 正確載入 blocks.json 並建構樹
✓ list_section_tree 三種格式正確
✓ get_section_detail 找不到時提供建議
✓ get_section_blocks 過濾 block_types
✓ search_sections 回傳排序結果
✓ 快取機制：第二次不重新載入
✓ clear_cache 正確清除
```

---

### 5.3 Level 2: Integration Tests（需要 Marker 模型）

位置：`tests/integration/test_marker_etl.py`

**前置條件：**
- Marker 已安裝（`uv sync --extra marker`，或相容別名 `uv sync --extra pdf`）
- 模型已下載（首次執行時自動下載）
- 測試用 PDF 檔案存在

**測試資料：**
使用 `test_pdfs/` 目錄下的 PDF 檔案。建議準備：

| 測試 PDF | 特性 | 用途 |
|----------|------|------|
| `simple_paper.pdf` | 5 頁，有表格、圖片、章節 | 基本功能驗證 |
| `long_book_chapter.pdf` | 30+ 頁，多層章節 | Section hierarchy 壓力測試 |
| `table_heavy.pdf` | 含 5+ 個複雜表格 | 表格提取驗證 |
| `figure_heavy.pdf` | 含 10+ 個圖片 | 圖片提取與過濾驗證 |

#### Integration Test 案例

```
✓ [IT-01] Marker 成功解析 PDF 並回傳 MarkerParseResult
✓ [IT-02] 產出的 markdown 非空且含標題
✓ [IT-03] blocks.json 成功生成並可被 json.loads 解析
✓ [IT-04] blocks 中 SectionHeader 的 section_hierarchy 正確
✓ [IT-05] blocks 中 Table block 的 text 為有效 Markdown 表格
✓ [IT-06] 圖片成功提取並可被 PIL 開啟
✓ [IT-07] manifest.json 可被 DocumentManifest.model_validate() 解析
✓ [IT-08] IngestResult.backend == "marker"
✓ [IT-09] SectionTree 從 blocks.json 正確建構
✓ [IT-10] use_marker=False 降級為 PyMuPDF（不產生 blocks.json）
✓ [IT-11] Marker 不可用時回傳明確錯誤
```

---

### 5.4 Level 3: Quality Benchmarks（人工標註對照）

位置：`tests/benchmark/test_marker_quality.py`

**對照資料格式：** `test_data/{pdf_name}_ground_truth.json`

```json
{
  "sections": [
    {"title": "Abstract", "level": 1, "page": 1},
    {"title": "Introduction", "level": 1, "page": 1},
    {"title": "Methods", "level": 1, "page": 3},
    {"title": "Data Collection", "level": 2, "page": 3}
  ],
  "tables": [
    {"page": 4, "row_count": 5, "col_count": 3, "caption_contains": "Patient Demographics"}
  ],
  "figures": [
    {"page": 2, "caption_contains": "Figure 1"}
  ],
  "expected_block_count_range": [100, 500],
  "expected_page_count": 10
}
```

#### Benchmark Metrics

| 指標 | 計算方式 | 目標 |
|------|----------|------|
| **Section 召回率** | `正確識別的章節 / 標註章節總數` | ≥ 80% |
| **Section 精確率** | `正確識別的章節 / 識別的章節總數` | ≥ 70% |
| **Table 召回率** | `正確識別的表格 / 標註表格總數` | ≥ 90% |
| **Figure 召回率** | `正確識別的圖片 / 標註圖片總數` | ≥ 80% |
| **Page 準確率** | `頁碼正確的 block / 總 block 數` | ≥ 95% |
| **BBox 有效率** | `bbox 非空的 block / 總 block 數` | ≥ 90% |

---

## 6. 已知限制與未來改善

### 6.1 已知限制

| 限制 | 說明 | 預計改善 | 狀態 |
|------|------|----------|------|
| 模型大小 | 首次使用需下載 ~1GB 模型 | Lazy-load 已實作 | ✅ 已解決 |
| 處理速度 | 比 PyMuPDF 慢 5-10 倍 | 可考慮批次平行 | 🔲 待改善 |
| Figure Caption | 部分圖片的 caption 可能遺漏 | ~~改善 caption 匹配邏輯~~ | ✅ 已修復 (index-based 1:1 匹配) |
| Table row/col | row_count/col_count 固定為 0 | 從 markdown 解析 | ✅ 已修復 (_parse_table_dimensions) |
| 圖片尺寸 | width/height 固定為 0 | 使用 PIL 讀取 | ✅ 已修復 (_get_image_dimensions) |
| OCR PDF | 不支援純圖片 PDF | 未來整合 OCR 前處理 | 🔲 待改善 |
| 小圖過濾 | 目前未過濾小圖標/裝飾 | 加入尺寸閾值 | 🔲 待改善 |

### 6.2 與 PyMuPDF 結果對照

一個重要的品質指標是**兩引擎結果的一致性**：
- `page_count` 應該完全一致
- `table_count` Marker 應 ≥ PyMuPDF
- `section_count` Marker 應更準確
- `figure_count` Marker 應更少但更精確（過濾小圖）

---

## 7. 驗收清單（Definition of Done）

### 7.1 功能驗收

- [ ] `ingest_documents(use_marker=True)` 成功處理至少 3 個不同類型的 PDF
- [ ] 產出 `_full.md`, `manifest.json`, `blocks.json`, `images/` 四項 artifacts
- [ ] `blocks.json` 中所有 block 都有 `block_id`, `block_type`, `page`, `bbox`
- [ ] `SectionTree` 可從 `blocks.json` 正確建構
- [ ] 4 個 Section MCP Tools 都可正常呼叫
- [ ] `use_marker=False` 時行為不變（向後相容）

### 7.2 測試驗收

- [ ] Unit tests 全部通過（`pytest tests/unit/test_marker_*.py tests/unit/test_section_*.py`）
- [ ] Integration tests 通過（`pytest tests/integration/test_marker_etl.py`，需 Marker 已安裝）
- [ ] 無未捕獲例外（所有錯誤路徑都有 try-except）

### 7.3 文件驗收

- [ ] 本規格書已更新至最新狀態
- [ ] `docs/spec.md` 已反映 Marker 整合
- [ ] `memory-bank/` 已同步
- [ ] `CHANGELOG.md` 已更新

---

## 附錄 A：Block Type 對照表

| Marker Block Type | 對應 Asset Type | 說明 |
|-------------------|-----------------|------|
| `SectionHeader` | `SectionAsset` | 章節標題 |
| `Table` | `TableAsset` | 表格 |
| `Figure` | `FigureAsset` | 圖片/圖表 |
| `Text` | — (歸入 section content) | 段落文字 |
| `ListItem` | — (歸入 section content) | 列表項目 |
| `Equation` | — (歸入 section content) | 數學公式 |
| `Caption` | — (關聯到 Table/Figure) | 標題/圖說 |
| `Footnote` | — (歸入 section content) | 腳註 |
| `Page` | — (容器) | 頁面容器 |

## 附錄 B：測試 PDF 建議來源

| PDF | 來源 | 特色 |
|-----|------|------|
| Docling Paper | arXiv 2408.09869 | 已有 PyMuPDF 對照 |
| GPT-4 Technical Report | OpenAI | 大量表格 |
| Nobel Prize Scientific Background | nobelprize.org | 圖文並茂 |
| Miller's Anesthesia Chapter | 教科書 | 深層章節結構 |
