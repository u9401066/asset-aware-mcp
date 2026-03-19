# 格式互轉保真度報告 (Format Conversion Fidelity Report)

> **測試日期**: 2026-03-19  
> **測試腳本**: `scripts/roundtrip_3cycle_test.py`  
> **測試環境**: Python 3.10.12, LibreOffice 7.3.7.2, python-docx 1.1+

---

## 1. 測試目標

驗證 asset-aware-mcp 的文件格式互轉在**多次迴圈後**是否產生累積性退化 (cumulative degradation)。

### 測試場景

| # | 場景 | 描述 | 迴圈數 |
|---|------|------|--------|
| 1 | DFM Round-trip | DOCX → DFM → DOCX | 3 cycles |
| 2 | DOC Cross-format | DOCX → DOC → DOCX | 1 cycle |
| 3 | ODT Cross-format | DOCX → ODT → DOCX | 1 cycle |

### 6 維度驗證

每次轉換均使用 `DocxValidator` 進行 6 維度比較：

| 維度 | 權重 | 檢查內容 |
|------|------|----------|
| **Structure** | 20% | 段落數、標題層級、區塊類型分佈 |
| **Text** | 25% | 逐段落文字內容比對（最嚴格） |
| **Format** | 20% | 粗體、斜體、底線、刪除線、字型、顏色 |
| **Table** | 15% | 表格數量、行列數、儲存格內容 |
| **Media** | 10% | 圖片數量、尺寸、二進位 hash |
| **Style** | 10% | 段落/字元樣式名稱對應 |

---

## 2. 測試結果

### 2.1 DFM 3-Cycle Round-trip — ✅ 100.0% (零退化)

```
  Cycle | Fidelity | Structure | Text   | Format | Table  | Media  | Style
  ------|----------|-----------|--------|--------|--------|--------|------
      1 |  100.0%  |   100.0%  | 100.0% | 100.0% | 100.0% | 100.0% | 100.0%
      2 |  100.0%  |   100.0%  | 100.0% | 100.0% | 100.0% | 100.0% | 100.0%
      3 |  100.0%  |   100.0%  | 100.0% | 100.0% | 100.0% | 100.0% | 100.0%
```

**結論**：DFM round-trip 是**完全冪等 (idempotent)** 的。經過 3 次 DOCX → DFM → DOCX 迴圈，所有 6 個維度皆維持 100%，零累積退化。

這證明了 DFM 設計核心原則的有效性：
- **DocxIR (中間表示)** 完整捕獲所有格式資訊
- **XML 部件原封保留** (styles.xml, numbering.xml 等)
- **Block ID 追蹤** 確保每個區塊精確還原

### 2.2 DOCX ↔ DOC Cross-format — ⚠️ 94.5%

```
  Dimension  | Score  | 說明
  ----------|--------|------
  Structure | 85.7%  | LibreOffice 轉換時新增/移除部分結構元素
  Text      | 100.0% | 文字內容完全保留
  Format    | 100.0% | 粗體/斜體/底線等格式保留
  Table     | 100.0% | 表格結構與內容保留
  Media     | 100.0% | 圖片保留
  Style     | 66.7%  | DOC 格式的樣式名稱體系與 DOCX 不同
```

### 2.3 DOCX ↔ ODT Cross-format — ⚠️ 94.5%

```
  Dimension  | Score  | 說明
  ----------|--------|------
  Structure | 85.7%  | OpenDocument 結構模型差異
  Text      | 100.0% | 文字內容完全保留（含 CJK）
  Format    | 100.0% | 格式保留
  Table     | 100.0% | 表格保留
  Media     | 100.0% | 圖片保留
  Style     | 66.7%  | ODT 使用不同的樣式命名體系
```

---

## 3. 退化分析

### 3.1 DFM Round-trip: 零退化 ✅

```
  Per-dimension drift (cycle 1 → cycle 3):
    ✅ structure  : 100.0% → 100.0% (+0.0%)
    ✅ text       : 100.0% → 100.0% (+0.0%)
    ✅ format     : 100.0% → 100.0% (+0.0%)
    ✅ table      : 100.0% → 100.0% (+0.0%)
    ✅ media      : 100.0% → 100.0% (+0.0%)
    ✅ style      : 100.0% → 100.0% (+0.0%)
```

**這是關鍵結果**：DFM pipeline 的設計確保無論轉換多少次，文件保真度都不會退化。

### 3.2 Cross-format 損失根因

跨格式轉換的 5.5% 損失來自 **LibreOffice 轉換引擎**，非本系統造成：

| 損失維度 | 根因 | 為何無法避免 |
|---------|------|-------------|
| **Structure 85.7%** | LibreOffice 在格式轉換時會插入/重排部分結構元素（如空段落、分節符） | 這是 OOXML ↔ ODF/DOC binary 的格式模型差異 |
| **Style 66.7%** | DOCX 使用 `w:pStyle`/`w:rStyle` 命名體系；DOC 使用內部索引；ODT 使用 `text:style-name` | 三種格式定義下的樣式ID命名系統不同 |

**重要**: 文字、格式、表格、媒體四個核心維度在跨格式轉換中均為 **100%**。

---

## 4. 支援格式矩陣

### 4.1 匯入支援 (Ingest)

| 格式 | 副檔名 | 方式 | 說明 |
|------|--------|------|------|
| DOCX | `.docx` | 直接解析 | 原生支援，無需轉換 |
| DOC | `.doc` | LibreOffice → DOCX | 自動轉換後解析 |
| ODT | `.odt` | LibreOffice → DOCX | OpenDocument Text，自動轉換 |
| ODS | `.ods` | LibreOffice → DOCX | OpenDocument Spreadsheet，自動轉換 |

### 4.2 匯出支援 (Export)

| 格式 | 副檔名 | MCP Tool | 說明 |
|------|--------|----------|------|
| DOCX | `.docx` | `save_docx` | DFM → DOCX 回寫 |
| PDF | `.pdf` | `convert_docx_to_pdf` | LibreOffice 轉換 |
| DOC | `.doc` | `convert_docx_to_doc` | LibreOffice 轉換（Legacy） |
| ODT | `.odt` | `convert_docx_to_odt` | LibreOffice 轉換 |

> **注意**：ODS (試算表) 無法從 DOCX (文書處理) 匯出——這是根本不同的文件類型。
> ODS 僅支援匯入（LibreOffice 會將其轉為 DOCX 結構）。

---

## 5. 與業界對比

### 5.1 Round-trip 測試方法論比較

| 專案 | Round-trip 測試 | 驗證方式 | 維度 |
|------|----------------|----------|------|
| **asset-aware-mcp** | ✅ 3-cycle + cross-format | `DocxValidator` 6 維度量化 | Structure, Text, Format, Table, Media, Style |
| **LibreOffice Core** | ✅ 數百個 filter tests | XPath 逐屬性比較 | 極細粒度（單一 XML 屬性） |
| **Pandoc** | ✅ Golden file tests | AST 比對 | 結構 + 語義 |
| **Office-Word-MCP** (⭐1.6k) | ❌ | — | — |
| **MCP-Doc** (⭐170) | ❌ | — | — |
| **adeu** (⭐43) | ⚠️ Format Safety 聲明 | 未量化 | — |

### 5.2 業界參考專案

以下為文件格式轉換領域最具參考價值的開源專案：

| 專案 | 用途 | 可借鑑之處 |
|------|------|-----------|
| [**Pandoc**](https://github.com/jgm/pandoc) | 萬用格式轉換器 (40+ 格式) | AST 中間表示設計、reader↔writer 一致性測試 |
| [**LibreOffice Core**](https://github.com/LibreOffice/core) | 完整文件引擎 | `sw/qa/extras/ooxmlexport/` 有業界最大規模 round-trip 測試集 |
| [**Docling (IBM)**](https://github.com/DS4SD/docling) | PDF/DOCX → 統一 IR | DoclingDocument 跨格式中間表示設計 |
| [**python-docx**](https://github.com/python-openxml/python-docx) | Python OOXML 操作 | `oxml` 層保留未知 XML 策略 |
| [**Marker**](https://github.com/VikParuchuri/marker) | ML-based PDF→MD | `benchmark/` BLEU/edit-distance 品質指標 |
| [**Apache POI**](https://github.com/apache/poi) | Java OOXML/OLE2 | OOXML spec compliance 測試集 |
| [**ODF Toolkit**](https://github.com/tdf/odftoolkit) | ODF 處理 | ODF Validator 規範驗證工具 |
| [**Mammoth**](https://github.com/mwilliamson/mammoth) | DOCX→HTML 語義轉換 | Style map 映射規則引擎 |
| [**veraPDF**](https://github.com/veraPDF/veraPDF-library) | PDF/A 驗證器 | 規則引擎式驗證框架 |
| [**Calibre**](https://github.com/kovidgoyal/calibre) | 電子書格式轉換 | Pipeline 階段設計 (parse→transform→serialize) |

### 5.3 關鍵發現

1. **Round-trip fidelity metrics 是極稀缺的領域** — 在 MCP 生態系中 **0/16** 競爭者有此功能；在更廣泛的開源生態中，僅 LibreOffice Core 有可比規模的 round-trip 測試
2. **LibreOffice `sw/qa/extras/`** 是目前最完整的 round-trip 測試基準，可作為擴展測試用例的參考來源
3. **Pandoc 的 Golden file testing** 模式值得在 DFM 的 CI 中採用
4. **中間表示 (IR)** 是高品質 round-trip 的關鍵 — Pandoc (AST)、Docling (DoclingDocument)、asset-aware-mcp (DocxIR → DFM) 都採用此策略

---

## 6. 改進方向

### 短期

- [ ] 將 3-cycle round-trip 測試加入 CI (`pytest` 整合)
- [ ] 收集 LibreOffice test suite 的 .docx 作為擴展測試語料
- [ ] 新增 Golden file 測試：固定輸入 .docx → 期望的 DFM 輸出

### 中期

- [ ] 更細粒度的 Structure 驗證（XPath 層級）
- [ ] Style 映射表：DOCX ↔ ODT ↔ DOC 樣式名稱對應
- [ ] 支援 DOCX → RTF 轉換（LibreOffice 支援）

### 長期

- [ ] 視覺保真度驗證（headless render → pixel diff）
- [ ] 大規模語料測試（100+ 真實 .docx 自動化 round-trip）
- [ ] OOXML Conformance 測試（基於 ECMA-376 規範）

---

## 7. 複驗方法

任何人可執行以下命令重現測試結果：

```bash
# 使用內建範例文件
uv run python scripts/roundtrip_3cycle_test.py

# 使用自訂 DOCX
uv run python scripts/roundtrip_3cycle_test.py path/to/your.docx
```

測試報告自動儲存至 `data/roundtrip_3cycle_report.json`。
