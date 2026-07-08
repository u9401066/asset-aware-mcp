# PDF 拆解引擎評估報告：改善圖文拆解錯誤

**日期**: 2026-07-08
**撰寫**: GitHub Copilot（自主研究）
**觸發需求**: 大量尋找 PDF 拆解的 GitHub 套件／專案，評估能否改善目前圖文拆解的錯誤
**Repo 狀態**: 已更新至 `v0.7.0`

---

## 0. 執行摘要（TL;DR）

- **根因**：高精度引擎 **Marker 目前被停用**（`pyproject.toml` 的 `marker = []`），因 `marker-pdf 1.10.2` 釘死 `Pillow<11`，與安全 runtime 要求的 `Pillow>=12.2.0` 衝突。圖文拆解因此**只剩 PyMuPDF**，其向量圖 figure 邊界、figure–caption 對應、表格結構、reading order 都靠啟發式，這是圖文錯誤的來源。
- **決定性發現**：用 `uv pip compile` 實測，**Docling / MinerU / PyMuPDF4LLM 三者都能與 `Pillow>=12.2.0` 共存**（皆解析出 `pillow==12.3.0`）。**Marker 停用 ≠ 沒有高精度替代**。
- **建議（分層）**：
  - **Tier 1（低風險 drop-in）**：`pymupdf4llm` — 同 PyMuPDF 生態、零 Pillow 衝突、無 GPU，立即改善 reading order／表格 markdown。
  - **Tier 2（取代 Marker 的主力）**：`docling` — **MIT 授權**、內建 layout+reading order+table+formula+**chart 理解**、附 **MCP server**，且 VLM 用 **GraniteDocling 258M**（與本專案 granite 後端一致）。
  - **Tier 3（追求最高精度）**：`mineru` — OmniDocBench 分數最高、公式→LaTeX、表格→HTML、跨頁表格合併，可純 CPU 但吃資源。
  - **模組化補強**：`Surya` / `gmft` 針對表格與 layout 單點強化。

---

## 1. 問題根因分析

### 1.1 Marker 為何停用
`pyproject.toml`：
```toml
# marker-pdf 1.10.2 pins Pillow<11 while the secure runtime requires
# Pillow>=12.2.0. Re-populate when upstream marker-pdf supports a
# patched Pillow range.
marker = []
```
安全基線 `Pillow>=12.2.0`（CVE 修補）與 marker-pdf 的 `Pillow<11` 互斥，因此高精度路徑被關閉。

### 1.2 目前 PyMuPDF 路徑的弱點
來源：`src/infrastructure/pdf_extractor.py` 的 `PyMuPDFExtractor._extract_images_direct`（3 個啟發式策略）。

| 弱點 | 成因 |
|------|------|
| 向量圖 figure 漏抓／裁錯邊界 | 靠 `PYMUPDF_ENABLE_VECTOR_IMAGES` 區域偵測啟發式，非語意 layout |
| figure ↔ caption 對位錯誤 | `_extract_figure_captions_worker` 靠位置鄰近度猜測 |
| 表格結構跑掉（合併儲存格／跨頁斷裂） | 依賴 PyMuPDF `find_tables()` 幾何啟發式 |
| 多欄 reading order 錯亂 | 依 text block 幾何順序，缺少閱讀序模型 |
| 公式／特殊符號遺失 | 無數學辨識模型 |
| 掃描 PDF 品質差 | OCR 為後掛，非整合式 layout-aware |

> 這些都是「非語意 layout」的通病——要改善必須引入具備 **layout 理解模型** 的引擎。

---

## 2. 決定性驗證：Pillow 不再是障礙

實測指令（本機 `uv`，網路解析）：
```bash
printf "Pillow>=12.2.0\n<pkg>\n" | uv pip compile -
```

| 候選 | 解析結果 | 判定 |
|------|----------|------|
| `pymupdf4llm` | `pillow==12.3.0` | ✅ 相容 |
| `docling` | `pillow==12.3.0` | ✅ 相容 |
| `mineru` | `pillow==12.3.0` | ✅ 相容 |

**結論**：三個主力全部通過完整依賴解析，與 `Pillow>=12.2.0` 無衝突。可直接以 optional extra 形式加入，不影響安全基線。

---

## 3. 候選套件全景（大量清單）

### A. 全流程文件理解引擎（可整段取代 Marker）
| 專案 | Stars | 授權 | 精度/能力 | 資源 | 備註 |
|------|-------|------|-----------|------|------|
| **Docling** (IBM) | 62.8k | **MIT** | layout+reading order+table+formula+**chart 理解**、圖片分類 | 輕量 layout model；VLM=GraniteDocling 258M | **內建 MCP server**、LangChain/LlamaIndex、air-gapped、Py3.10–3.14 |
| **MinerU** (OpenDataLab) | 73.8k | Apache-2.0 衍生 | **最高**（OmniDocBench 86–95）、公式→LaTeX、表格→HTML、跨頁表格合併、表內圖/公式 | **純 CPU 可跑**（pipeline backend），RAM 16GB+ | pipeline/VLM/hybrid 三後端、Py3.10–3.13 |
| Marker (datalab) | 30k+ | GPL/商用 | 高精度、以 Surya 為底 | GPU 佳 | **停用中**（Pillow<11 衝突）|
| unstructured | 12k+ | Apache-2.0 | 通用文件切塊 | 中 | 本專案曾遇 Py3.12 相容問題 |
| PDF-Extract-Kit (OpenDataLab) | 12k+ | AGPL | MinerU 底層工具包 | GPU 佳 | 需自組 pipeline |

### B. 同 PyMuPDF 生態（最低整合成本）
| 專案 | Stars | 授權 | 能力 | 備註 |
|------|-------|------|------|------|
| **PyMuPDF4LLM** | 1.9k | AGPL/商用 | 多欄 reading order、table→markdown、image/vector 引用、hybrid OCR、`to_json`(bbox) | 新增 `pymupdf-layout`（layout-aware）、無 GPU、一行呼叫 |

### C. 模組化引擎（單點強化 layout／表格／OCR）
| 專案 | Stars | 授權 | 能力 | 備註 |
|------|-------|------|------|------|
| **Surya** (datalab) | 21.1k | Apache-2.0（模型 Rail-M，<$5M 免費） | layout+reading order+table_rec+OCR（90+ 語言）、公式`<math>` | Surya 2 為單一 VLM 650M，**需 vllm(GPU)/llama.cpp(CPU) server** |
| gmft | 1k+ | MIT | 專注表格結構（基於 TATR） | 輕量、GPU 友善 |
| Table-Transformer (TATR, MS) | 2k+ | MIT | 表格結構偵測/識別 | 學術基準模型 |
| pdfplumber | 6k+ | MIT | 幾何式表格/文字/線條 | 純 Python、適合數位 PDF |
| Camelot | 3k+ | MIT | lattice/stream 表格 | 對有框線表格佳 |

### D. VLM / OCR 導向（掃描件、複雜版面、公式）
| 專案 | 授權 | 能力 | 備註 |
|------|------|------|------|
| olmOCR (AllenAI) | Apache-2.0 | VLM 全頁 OCR、benchmark 標竿 | 需 GPU 較實用 |
| Chandra (datalab) | 開源+模型授權 | 高精度 OCR（olmOCR-bench 85.9） | 5.3B，較重 |
| Nougat (Meta) | MIT | 學術 PDF→markdown、公式強 | 2023 後維護趨緩 |
| GROBID | Apache-2.0 | 學術文獻結構化（TEI/XML） | Java 服務、參考文獻/metadata 強 |

> 精度標註：A、B 區與 Surya 的關鍵數據已於本次研究即時驗證；C（gmft/TATR/pdfplumber/Camelot）、D 區為既有領域知識，整合前建議再實測版本與授權。

---

## 4. PyMuPDF 弱點 → 改善對應矩陣

| 目前弱點 | 最佳解 | 次選 |
|----------|--------|------|
| 向量圖 figure 漏抓/裁錯 | Docling（layout 分類 Picture/Figure/Diagram） | MinerU、Surya layout |
| figure ↔ caption 對位 | Docling / MinerU（語意標 Caption 並綁定） | Surya（Caption label） |
| 表格結構（合併/跨頁） | MinerU（跨頁合併+表格→HTML） | Surya `table_rec` full HTML、gmft |
| 多欄 reading order | Docling / MinerU（閱讀序模型） | PyMuPDF4LLM（layout mode） |
| 公式/數學符號 | MinerU（→LaTeX）、Surya（`<math>`） | Nougat |
| 掃描/OCR 品質 | MinerU（109 語言）、Surya（90+） | PyMuPDF4LLM hybrid OCR |
| 低風險快速改善 | **PyMuPDF4LLM** | — |

---

## 5. 三大主力深度評估

### 5.1 Docling（★ 建議取代 Marker 的主力）
- **優**：MIT 最乾淨可商用；layout+reading order+table+formula+**chart→table** 一站式；統一 `DoclingDocument`（可無損 JSON）；**內建 MCP server**；VLM 用 **GraniteDocling 258M**，與本專案預設 granite 後端天然契合；air-gapped 本地執行；Production/Stable、社群極活躍。
- **缺**：VLM pipeline 首次需下載模型；預設 layout 模型仍需一定 CPU/記憶體（但遠低於 Marker 的 surya OOM 等級）。
- **契合度**：本專案 `data/` 已存在 `doc_docling_paper_*`，方向相符。

### 5.2 MinerU（★ 追求最高精度）
- **優**：OmniDocBench 分數最高；公式→LaTeX、表格→HTML、跨頁表格合併、表內圖/公式辨識；pipeline backend **可純 CPU**；授權已從 AGPL 放寬為 Apache-2.0 衍生。
- **缺**：完整依賴含 torch/onnxruntime，體積大；RAM 建議 16–32GB；**OOM 風險是主要顧慮**（呼應 issue-report 20260429 的 Marker OOM 痛點）。
- **策略**：若採用，務必走 `pipeline`（`-b pipeline`）並沿用現有 subprocess+timeout 隔離機制。

### 5.3 PyMuPDF4LLM（★ 低風險 drop-in）
- **優**：同 PyMuPDF 生態、**零 Pillow 衝突**、無 GPU、`to_json` 提供 bbox/layout、page chunking 附 tables/images/graphics；改動面最小。
- **缺**：仍為啟發式為主（雖加 `pymupdf-layout`），精度提升幅度不如 Docling/MinerU；AGPL 需注意商用授權。
- **策略**：作為 PyMuPDF 的漸進升級，風險最低、可立即上線。

---

## 6. 建議的整合路徑（符合 DDD 架構）

現有設計：`PyMuPDFExtractor(PDFExtractorInterface)` 位於 `src/infrastructure/pdf_extractor.py`，由 Composition Root 注入。**新引擎應實作同一介面，作為可插拔的 high-fidelity 選項，保留 PyMuPDF 為 fast fallback。**

```
src/infrastructure/
  pdf_extractor.py        # PyMuPDFExtractor (fast, 現況/fallback)
  marker_adapter.py       # 停用中（Pillow<11）
  docling_adapter.py      # ← 新增：DoclingExtractor(PDFExtractorInterface)  ★建議
```

`pyproject.toml`（新增 optional extra，取代空的 marker slot 作為新的高精度路徑）：
```toml
[project.optional-dependencies]
# 高精度 layout 引擎（與 Pillow>=12.2.0 相容，已實測）
docling = ["docling>=2.110.0"]
# 或漸進升級路徑
pdf-plus = ["pymupdf4llm>=0.3.4"]
```

分階段落地：
1. **Phase 0（低風險）**：加入 `pymupdf4llm` extra，於 `document_service` 增加一個 `engine="pymupdf4llm"` 選項，A/B 比對輸出品質。
2. **Phase 1（主力）**：實作 `DoclingExtractor`，映射 Docling 的 layout labels（Picture/Table/Caption/Formula/SectionHeader…）到本專案的 segmentation schema 與 asset 實體；沿用既有 subprocess timeout/OOM 隔離。
3. **Phase 2（選配）**：對高難度文件提供 `mineru -b pipeline` 後端；或以 `Surya table_rec` / `gmft` 單獨強化表格。
4. **驗證**：以 `data/` 既有樣本（docling paper、attention、bert、resnet 等）跑回歸，比對 figure/caption/table 對位與 reading order。

---

## 7. 風險與注意事項

- **OOM**：MinerU/Surya/Marker 這類重模型是主要風險（見 `docs/asset-aware-mcp-issue-report-20260429.md`）。Docling 預設 layout 模型較輕，建議優先；重後端一律走 subprocess + timeout。
- **授權**：Docling=MIT、MinerU=Apache-2.0 衍生、Surya code=Apache-2.0（模型 Rail-M）；PyMuPDF4LLM=AGPL（商用需授權）。本專案為 Apache-2.0，**Docling 授權最相容**。
- **模型下載**：VLM/layout 模型首次需下載，air-gapped 環境需預先快取。
- **不建議**：直接大改 `pdf_extractor.py` 核心；應以新 adapter 並存、可切換。

---

## 8. 下一步（待使用者確認）

1. 選定路徑：**Tier 1 快速（pymupdf4llm）** 或 **Tier 2 主力（docling）**？
2. 確認後即可實作 POC：`DoclingExtractor` adapter + optional extra + 回歸比對腳本。
3. 保留現有 `stash@{0}`（本次更新前暫存的 llm-wiki harness 變更），需要時 `git stash pop` 還原。

---

## 附錄：本次研究已驗證事實

- Repo：`v0.6.29 → v0.7.0`（fast-forward）。
- `uv pip compile` 實測：`docling` / `mineru` / `pymupdf4llm` 皆與 `Pillow>=12.2.0` 相容（`pillow==12.3.0`）。
- Docling：MIT、Py3.10–3.14、Production/Stable、內建 MCP、GraniteDocling 258M VLM。
- MinerU：`pillow>=11.0.0`（無上限）、pipeline 可純 CPU、Apache-2.0 衍生授權。
- Surya：Apache-2.0（code）、VLM 650M、需 vllm/llama.cpp 推論後端。
