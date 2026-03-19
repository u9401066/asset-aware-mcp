# Agent 資產完整覆蓋 — Gap 分析與實現路線圖

> 📅 2026-03-19 | 核心目標：所有可作為 agent 資產的文件，都能良好轉換並被 agent 理解

---

## 1. 核心框架：Agent 理解文件的四個層次

```
Layer 4: 🧠 語義理解    — 知識圖譜、跨文件推理、自動摘要
Layer 3: 🗂️ 結構導航    — 章節樹、讀取順序、交叉引用
Layer 2: 📦 資產拆解    — 圖片、表格、公式、圖表 → 獨立可查詢
Layer 1: 📄 格式轉換    — 任何輸入 → 統一中間格式 (Markdown/DFM)
```

**原則**：每一層都建立在前一層之上。格式轉換是地基。

---

## 2. 現況能力矩陣

### 2.1 格式轉換 (Layer 1) — 現有覆蓋

| 格式 | 輸入 | 中間格式 | 輸出 | 保真度 |
|------|:----:|----------|:----:|--------|
| **PDF** | ✅ | Manifest + Markdown + blocks | — | 高（雙引擎） |
| **DOCX** | ✅ | DFM (Markdown + format.yaml) | ✅ | 100% round-trip |
| **DOC** (Word 97) | ✅ | → DOCX → DFM | ✅ | 94.5% |
| **ODT** | ✅ | → DOCX → DFM | ✅ | 94.5% |
| **ODS** | ✅ | → DOCX → DFM | — | 有損（表格→文字） |
| **RTF** | ⚠️ | LO 可轉但未加入白名單 | — | 未測試 |

### 2.2 資產拆解 (Layer 2) — 現有覆蓋

| 資產類型 | PDF | DOCX | 對 Agent 的呈現方式 |
|---------|:---:|:----:|---------------------|
| **嵌入圖片** | ✅ | ✅ | Base64 + 智能壓縮 (1024px) |
| **向量圖形** | ✅ | — | 光柵化 → Base64 |
| **表格** | ✅ | ✅ | Markdown table + metadata |
| **圖表 (Chart)** | ⚠️ 僅圖片 | ✅ 數據提取 | DOCX: 結構化數據 / PDF: 僅圖片 |
| **公式** | ⚠️ 僅圖片 | ⚠️ 僅圖片 | 無 LaTeX/MathML 語義 |
| **腳註** | ⚠️ 行內 | ✅ | DOCX: 完整 / PDF: 合併入文字 |
| **程式碼區塊** | — | — | 無特殊處理 |

### 2.3 結構導航 (Layer 3) — 現有覆蓋

| 功能 | PDF | DOCX | 狀態 |
|------|:---:|:----:|------|
| **章節樹** | ✅ | — | PDF: 動態建立 / DOCX: 無 |
| **讀取順序** | ✅ | — | PDF: ReadingOrderPolicy / DOCX: 無 |
| **Segmentation** | ✅ | — | PDF: 統一 schema / DOCX: 無 |
| **行號索引** | ✅ | — | PDF: MarkdownLineSpanIndex / DOCX: 無 |
| **搜尋** | ✅ | ✅ | 兩者皆有全文搜尋 |

### 2.4 語義理解 (Layer 4) — 現有覆蓋

| 功能 | 狀態 | 說明 |
|------|:----:|------|
| **知識圖譜** | ✅ | LightRAG: hybrid/local/global 查詢 |
| **跨文件推理** | ✅ | compare_documents, get_related_concepts |
| **實體提取** | ✅ | 自動提取 top-5 實體 |
| **圖譜匯出** | ✅ | JSON / Mermaid / Summary |
| **自動摘要** | ❌ | 無內建 |
| **圖片自動描述** | ❌ | Base64 給 agent 但無預生成 caption |
| **文件分類** | ❌ | 無自動類型辨識 |

---

## 3. Gap 分析

### 🔴 P0 — 核心缺失（嚴重影響 agent 可用性）

#### Gap 1: 常見格式未覆蓋

| 缺失格式 | 常見場景 | 實作難度 | 建議方案 |
|----------|---------|:--------:|---------|
| **XLSX/XLS** | 數據表、報告附件 | 🟡 中 | 直接解析 (openpyxl) → 結構化表格 → A2T |
| **CSV/TSV** | 結構化數據 | 🟢 低 | pandas/csv → A2T TableContext |
| **HTML/MHTML** | 網頁存檔、Email 附件 | 🟡 中 | beautifulsoup4 → Markdown (turndown) |
| **純文字 (.txt/.md)** | 筆記、README、程式文件 | 🟢 低 | 直接作為 Markdown ingest |
| **RTF** | 舊型文件 | 🟢 低 | 加入白名單即可 (LO 已驗證) |

**影響**：Agent 遇到這些格式只能放棄，無法處理。約佔企業文件 30-40%。

#### Gap 2: XLSX 作為表格資產的語義損失

當前 ODS/XLSX 透過 LibreOffice 轉 DOCX，表格結構嚴重降級：
- 多工作表 → 單一扁平文件
- 公式 → 靜態值
- 圖表 → 遺失
- 資料類型 → 純文字

**建議**：原生 XLSX 解析器，保留工作表結構、公式、數據類型。

#### Gap 3: 圖片無語義描述

Agent 收到 base64 圖片但缺乏：
- 自動 caption 生成
- 圖片內容分類 (figure/chart/photo/diagram/screenshot)
- OCR 文字提取 (圖片中的文字)

**建議**：Vision AI 自動描述管線 (可用 Claude Vision / GPT-4V / local VLM)。

---

### 🟡 P1 — 重要缺失（限制 agent 深度理解）

#### Gap 4: DOCX 缺少結構導航

PDF 有完整的 5-tool section navigation，但 DOCX/DFM 完全沒有：
- 無章節樹
- 無 segmentation
- 無讀取順序
- 無行號索引

**建議**：從 DFM heading structure 建立 SectionTree，複用現有 section_tools。

#### Gap 5: 公式語義提取

數學公式目前僅作為圖片捕獲，agent 無法：
- 搜尋公式
- 理解公式含義
- 比較不同文件的公式

**建議**：
- PDF: Marker 已可提取 `$...$` LaTeX → 需完善
- DOCX: OMML (Office MathML) → LaTeX 轉換
- 輸出: 統一為 LaTeX 表示

#### Gap 6: PDF 圖表數據提取

DOCX 圖表可提取結構化數據 (docx_chart_data)，但 PDF 圖表僅為圖片。

**建議**：
- 短期: Vision AI 辨識圖表並提取數據
- 中期: ChartOCR / DePlot 專用模型

#### Gap 7: 自動文件摘要

Agent 處理大量文件時缺乏快速概覽能力。

**建議**：
- LLM-based summarization (可配合 KG entities)
- 分級摘要: 一句話 / 段落 / 詳細

---

### 🟢 P2 — 進階增強（提升 agent 效率）

#### Gap 8: 簡報格式 (PPTX/PPT/ODP)

| 挑戰 | 說明 |
|------|------|
| 系統依賴 | 需安裝 `libreoffice-impress-nogui` |
| 文件模型差異 | Slide-based vs Flow-based (根本不同) |
| 保真度 | PPTX→DOCX 必然有大量結構損失 |

**建議**：獨立的 "PFM" (Presentation-Flavored Markdown) 管線：
```
PPTX → Slide[] → per-slide Markdown + 圖片資產 + speaker notes
```

#### Gap 9: Email 格式 (.eml/.msg)

| 需提取 | 方式 |
|--------|------|
| 郵件正文 | HTML/Plain → Markdown |
| 附件 | 遞迴 ingest 各格式 |
| Metadata | From/To/Date/Subject |

**建議**：`email` stdlib + `extract-msg` 庫。

#### Gap 10: 圖片直接作為文件

獨立圖片 (JPG/PNG/TIFF) 應可直接 OCR + 理解：
- 掃描文件的單頁
- 截圖
- 白板照片

**建議**：擴展 OCR 管線支援圖片輸入 (img2pdf → ocrmypdf 或直接 Tesseract)。

#### Gap 11: EPUB/電子書

學術電子書、技術文件常以 EPUB 分發。

**建議**：EPUB 本質是 XHTML + 資源包，可用 ebooklib → Markdown。

#### Gap 12: LaTeX 源碼

學術論文原始 .tex 檔案。

**建議**：Pandoc LaTeX → Markdown，保留公式語義。

---

## 4. 實現路線圖

### Phase 1: 格式地基擴展 (Priority: 🔴 P0)

**目標**：覆蓋 90%+ 常見企業/學術文件格式

```
Sprint 1 (2-3 天): 低成本格式
├── ✅ RTF 加入白名單 (1 小時)
├── ✅ TXT/MD 直接 ingest (0.5 天)
├── ✅ CSV/TSV → A2T TableContext (0.5 天)
└── ✅ HTML → Markdown ingest (1 天)

Sprint 2 (3-5 天): XLSX 原生支援
├── openpyxl 原生解析器 (2 天)
├── 多工作表 → 結構化表示 (1 天)
├── 公式保留/值快照 (0.5 天)
└── 圖表提取 → Base64 (0.5 天)

Sprint 3 (2-3 天): 圖片語義
├── Vision AI auto-caption pipeline (1.5 天)
├── 圖片分類 (figure/chart/photo/diagram) (0.5 天)
└── 圖片內 OCR 文字提取 (1 天)
```

**預估 Phase 1 工作量**: 7-11 天

### Phase 2: 理解層深化 (Priority: 🟡 P1)

**目標**：Agent 對每個文件的理解深度達到「專家級」

```
Sprint 4 (3-4 天): DOCX 結構導航
├── DFM → SectionTree 建立 (1 天)
├── 複用 section_tools 給 DOCX (1 天)
├── DOCX segmentation export (1 天)
└── 統一 get_section_content for both PDF/DOCX (0.5 天)

Sprint 5 (2-3 天): 公式語義化
├── OMML → LaTeX 轉換 (DOCX) (1 天)
├── Marker LaTeX 提取完善 (PDF) (1 天)
└── 公式搜尋/比較 API (0.5 天)

Sprint 6 (2-3 天): 自動摘要 + 分類
├── LLM summarization tool (1 天)
├── 文件類型自動分類 (0.5 天)
├── KG-enhanced summary (entity-aware) (1 天)
└── 分級摘要 (one-line / paragraph / detailed) (0.5 天)
```

**預估 Phase 2 工作量**: 7-10 天

### Phase 3: 進階格式 (Priority: 🟢 P2)

**目標**：覆蓋剩餘 10% 特殊格式

```
Sprint 7 (3-5 天): PPTX 簡報
├── 安裝 libreoffice-impress-nogui (0.5 天)
├── python-pptx 原生解析 (2 天)
├── Slide → Markdown + 圖片資產 (1 天)
└── Speaker notes 提取 (0.5 天)

Sprint 8 (2-3 天): 其他格式
├── EPUB → Markdown (ebooklib) (1 天)
├── Email .eml/.msg 解析 (1 天)
├── 獨立圖片 OCR ingest (0.5 天)
└── LaTeX .tex → Markdown (Pandoc) (0.5 天)
```

**預估 Phase 3 工作量**: 5-8 天

---

## 5. 建議發布切法

不建議把這一輪 gap 修補一次打包成單一大版本。比較穩的方式是按「可獨立驗證的能力面」拆成 4 次發布。

### Release A — 格式入口補齊

**目標**：先把最便宜、最常見、最容易驗證的輸入格式補上。

- RTF 納入 ingest 白名單
- TXT / MD 直接 ingest
- CSV / TSV → A2T TableContext
- HTML / MHTML → Markdown ingest

**建議版本型態**：minor release

**原因**：
- 會擴大支援格式矩陣
- 幾乎不碰核心 ETL 邏輯
- 回歸風險低，適合先發

### Release B — 表格原生化

**目標**：把 spreadsheet 從「轉成 DOCX 的權宜方案」升級成真正的原生資產。

- XLSX / XLS 原生解析
- 多工作表保留
- 公式 / 資料型別保留
- 圖表資產抽取（至少先以圖片或 metadata 形式保存）

**建議版本型態**：minor release

**原因**：
- 這是目前最大語義損失來源之一
- 與 A2T 有直接乘數效益
- 驗證面主要集中在表格與資產，不會干擾 PDF / DOCX 主線

### Release C — Agent 理解增強

**目標**：讓 agent 不只拿到檔案，而是真的更懂內容。

- 圖片自動 caption
- 圖片 OCR / 文字提取
- DOCX section tree / segmentation / get_section_content 對齊 PDF
- 自動摘要 / 文件分類

**建議版本型態**：minor release

**原因**：
- 屬於能力提升，不是單純格式支援
- 最適合單獨發布，方便觀察 agent 行為品質是否改善

### Release D — 高成本格式擴展

**目標**：處理非 flow-based 或特殊文件。

- PPTX / PPT / ODP
- EPUB
- EML / MSG
- JPG / PNG / TIFF 直接 OCR ingest
- LaTeX .tex

**建議版本型態**：minor 或 preview release

**原因**：
- 格式模型差異最大
- 依賴額外系統元件或第三方 parser
- 最容易拉高維護成本，不適合跟核心格式混發

### 發布原則

- 每一段發布都必須有獨立的測試與成功指標，不要共用一個總驗收
- 每一段只新增一種能力面，不同風險類型不要混在同一版
- 先發「入口擴展」與「表格原生化」，再發「理解增強」
- PPTX 這類非同模型格式，建議當成平行產品線，不要硬塞進 DOCX/DFM 釋出節奏

**建議順序**：Release A → Release B → Release C → Release D

---

## 6. 架構建議

### 5.1 統一 Ingest 入口

```python
# 目標：一個 ingest 入口搞定所有格式
async def ingest_any(file_path: str, options: IngestOptions) -> Document:
    """
    自動偵測格式 → 選擇最佳管線 → 統一輸出
    
    支援: PDF, DOCX, DOC, ODT, ODS, XLSX, XLS, CSV, 
          HTML, EPUB, RTF, TXT, MD, PPTX, EML, MSG,
          JPG, PNG, TIFF (OCR)
    """
    format = detect_format(file_path)
    pipeline = PIPELINE_REGISTRY[format]
    return await pipeline.process(file_path, options)
```

### 5.2 管線註冊表

```python
PIPELINE_REGISTRY = {
    # 文字文件 (flow-based) → DFM 中間格式
    FormatGroup.WORD:        DocxPipeline,      # .docx, .doc, .odt, .rtf
    FormatGroup.SPREADSHEET: SpreadsheetPipeline,  # .xlsx, .xls, .ods, .csv
    FormatGroup.PDF:         PdfPipeline,       # .pdf
    FormatGroup.PLAINTEXT:   PlaintextPipeline, # .txt, .md
    FormatGroup.HTML:        HtmlPipeline,      # .html, .mhtml
    FormatGroup.EBOOK:       EbookPipeline,     # .epub
    FormatGroup.LATEX:       LatexPipeline,     # .tex
    
    # 非文字文件 → 專用管線
    FormatGroup.PRESENTATION: PresentationPipeline,  # .pptx, .ppt, .odp
    FormatGroup.EMAIL:        EmailPipeline,    # .eml, .msg
    FormatGroup.IMAGE:        ImageOcrPipeline, # .jpg, .png, .tiff
}
```

### 5.3 統一輸出 Schema

```python
@dataclass
class IngestResult:
    """所有管線的統一輸出"""
    doc_id: str
    format_group: FormatGroup
    
    # Layer 1: 轉換產物
    markdown: str                    # 統一 Markdown 表示
    manifest: DocumentManifest       # 結構化 metadata
    
    # Layer 2: 資產清單
    images: list[ImageAsset]         # base64 + caption + type
    tables: list[TableAsset]         # structured data + metadata
    equations: list[EquationAsset]   # LaTeX representation
    
    # Layer 3: 結構
    section_tree: SectionTree        # 章節導航
    segmentation: DocumentSegmentation  # 讀取順序
    
    # Layer 4: 語義 (可選，需 LLM)
    summary: str | None              # 自動摘要
    doc_type: str | None             # 文件類型分類
    entities: list[Entity] | None    # 提取的實體
```

---

## 7. 距離目標的量化評估

### 格式覆蓋率

| 分類 | 常見格式數 | 已支援 | 覆蓋率 |
|------|:---------:|:------:|:------:|
| 文字文件 | 6 (PDF, DOCX, DOC, ODT, RTF, TXT) | 4 | 67% |
| 表格數據 | 4 (XLSX, XLS, ODS, CSV) | 1* | 25% |
| 簡報 | 3 (PPTX, PPT, ODP) | 0 | 0% |
| 網頁/電子書 | 3 (HTML, EPUB, MHTML) | 0 | 0% |
| 其他 | 4 (EML, MSG, LaTeX, Image) | 0 | 0% |
| **合計** | **20** | **5** | **25%** |

> *ODS 透過 DOCX 轉換，表格語義嚴重損失

### 理解深度評估

| 理解層次 | PDF | DOCX | 其他格式 | 目標 |
|----------|:---:|:----:|:--------:|:----:|
| L1 格式轉換 | ⬛⬛⬛⬛⬛ 95% | ⬛⬛⬛⬛⬛ 100% | ⬜⬜⬜⬜⬜ 0% | 90%+ |
| L2 資產拆解 | ⬛⬛⬛⬛⬜ 80% | ⬛⬛⬛⬜⬜ 60% | ⬜⬜⬜⬜⬜ 0% | 80%+ |
| L3 結構導航 | ⬛⬛⬛⬛⬛ 95% | ⬛⬜⬜⬜⬜ 20% | ⬜⬜⬜⬜⬜ 0% | 80%+ |
| L4 語義理解 | ⬛⬛⬛⬜⬜ 60% | ⬛⬛⬜⬜⬜ 40% | ⬜⬜⬜⬜⬜ 0% | 70%+ |

### 綜合差距

```
目前整體完成度: ~35%
├── 格式覆蓋: 25% (5/20 格式)
├── PDF 管線成熟度: 83% (L1-L4 平均)
├── DOCX 管線成熟度: 55% (L1-L4 平均)
└── 其他格式: 0%

Phase 1 後預估: ~65%
├── 格式覆蓋: 65% (13/20)
├── 圖片語義: +20%
└── XLSX 原生: +15%

Phase 2 後預估: ~82%
├── DOCX 結構導航: +8%
├── 公式語義: +5%
├── 自動摘要: +4%

Phase 3 後預估: ~93%
├── PPTX: +5%
├── EPUB/Email/圖片: +6%
```

---

## 8. 最高 ROI 行動排序

按 **影響面 × 實作容易度** 排序：

| 排名 | 行動 | 影響面 | 難度 | ROI |
|:----:|------|:------:|:----:|:---:|
| 1 | TXT/MD/RTF 直接 ingest | 高 (常見) | 🟢 極低 | ⭐⭐⭐⭐⭐ |
| 2 | CSV → A2T 直接導入 | 高 (數據) | 🟢 低 | ⭐⭐⭐⭐⭐ |
| 3 | HTML → Markdown 轉換 | 高 (網頁) | 🟡 中 | ⭐⭐⭐⭐ |
| 4 | XLSX 原生解析 | 高 (企業) | 🟡 中 | ⭐⭐⭐⭐ |
| 5 | Vision AI 圖片描述 | 高 (理解) | 🟡 中 | ⭐⭐⭐⭐ |
| 6 | DOCX 章節導航 | 中 (深度) | 🟢 低 | ⭐⭐⭐⭐ |
| 7 | 自動摘要 | 中 (效率) | 🟡 中 | ⭐⭐⭐ |
| 8 | 公式提取 | 中 (學術) | 🟡 中 | ⭐⭐⭐ |
| 9 | PPTX 支援 | 中 (企業) | 🔴 高 | ⭐⭐ |
| 10 | EPUB 支援 | 低 (學術) | 🟢 低 | ⭐⭐ |
| 11 | Email 解析 | 低 (特化) | 🟡 中 | ⭐⭐ |
| 12 | 圖片 OCR ingest | 低 (特化) | 🟢 低 | ⭐⭐ |

---

## 9. 與競品的差距比較

| 能力 | 本系統 | Docling (IBM) | Marker | Pandoc | Apache Tika |
|------|:------:|:-------------:|:------:|:------:|:-----------:|
| PDF 提取 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| DOCX 雙向編輯 | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ⭐⭐ | ❌ |
| 格式覆蓋 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 知識圖譜 | ⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| A2T 表格 | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| MCP 整合 | ⭐⭐⭐⭐⭐ | ❌ | ❌ | ❌ | ❌ |
| 圖片理解 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ❌ | ⭐ |
| XLSX 原生 | ❌ | ⭐⭐⭐ | ❌ | ❌ | ⭐⭐⭐ |
| PPTX 原生 | ❌ | ⭐⭐⭐ | ❌ | ⭐⭐ | ⭐⭐⭐ |

**差異化優勢**：DOCX 雙向編輯 + A2T 表格 + 知識圖譜 + MCP 整合 → 這是其他工具沒有的組合

**最大劣勢**：格式覆蓋率 (5/20 vs Tika 的 1000+)

---

## 10. 建議實施策略

### 策略 A: 「深度優先」(推薦)

```
重點做好 PDF + DOCX + XLSX + HTML + TXT 五大格式
每個格式都達到 L4（語義理解）
其他格式用 Tika/Pandoc 做 fallback 轉換
```

**優點**：每個支援的格式都是「最佳體驗」  
**缺點**：格式覆蓋較窄  
**適合**：Agent 主要處理知識密集型文件

### 策略 B: 「廣度優先」

```
先用 Pandoc + Tika 做通用 fallback (支援 100+ 格式)
核心格式 (PDF, DOCX) 維持深度管線
逐步把高頻格式從 fallback 提升為原生
```

**優點**：快速達到格式全覆蓋  
**缺點**：非核心格式的理解深度較淺  
**適合**：Agent 需要處理各種混合文件

### 建議: 混合策略 A+B

```
Phase 1: 核心格式深化 + fallback 層建立
  ├── TXT/MD/RTF/CSV/HTML → 原生支援 (快速)
  ├── XLSX → 原生解析 (重要)
  ├── Vision AI → 圖片描述 (關鍵)
  └── Pandoc fallback → 其餘格式基本支援
  
Phase 2: 理解層全面提升
  ├── DOCX 章節導航
  ├── 公式語義化
  ├── 自動摘要
  └── 文件分類
  
Phase 3: 按需擴展
  ├── PPTX (如有需求)
  ├── EPUB (如有需求)
  └── 提升 fallback 格式至原生
```
