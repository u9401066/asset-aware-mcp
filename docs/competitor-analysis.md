# MCP + DOCX 生態系競爭分析報告

> **更新日期**: 2026-06-22
> **範疇**: Model Context Protocol (MCP) 生態系中所有與 DOCX / Word 文件操作相關的開源專案

---

## 摘要

MCP + DOCX 生態系目前處於 **快速成長期**，GitHub 上可搜尋到 100+ 個相關 repo。然而，絕大多數 (**>90%**) 落入「Create-only」或「Read-only」類型——僅做文件生成或文字擷取，**無法進行既有文件的格式保留編輯 (round-trip editing)**。

**asset-aware-mcp** 透過 **Docx-Flavored Markdown (DFM)** 實現 `docx → markdown → edit → docx` 完整迴路，配合 **6 維度保真度驗證 (6-Dimension Fidelity Validation)** 與 **DFM Integrity Checker**，在生態系中佔據獨特定位。

---

## 1. 競爭者總覽

### 1.1 星數排名 (截至 2026-06)

| # | 專案 | ⭐ Stars | 語言 | 類型 | 簡介 |
|---|------|---------|------|------|------|
| 1 | [GongRzhe/Office-Word-MCP-Server](https://github.com/GongRzhe/Office-Word-MCP-Server) | 1,610 | Python | Create + Read + Write | 功能最全面的 python-docx 包裝，支援段落/表格/圖片/樣式/保護/PDF 轉換 |
| 2 | [WildDataX/suppr-mcp](https://github.com/WildDataX/suppr-mcp) | 247 | — | Translation | AI 文件翻譯 (PDF/DOCX/PPTX，11 語言) |
| 3 | [MeterLong/MCP-Doc](https://github.com/MeterLong/MCP-Doc) | 170 | Python | Create + Edit | FastMCP Word 處理服務，支援段落/表格/格式/區段編輯 |
| 4 | [Baronco/GenFilesMCP](https://github.com/Baronco/GenFilesMCP) | 66 | — | Generate | 從聊天生成 PPTX/XLSX/DOCX/MD |
| 5 | [gmickel/gno](https://github.com/gmickel/gno) | 45 | — | Search + Edit | 本地 AI 文件搜尋 + 編輯，混合檢索 |
| 6 | [alejandroBallesterosC/document-edit-mcp](https://github.com/alejandroBallesterosC/document-edit-mcp) | 44 | — | Lightweight Edit | 輕量 PDF/Word/Excel/CSV 編輯 |
| 7 | [dealfluence/adeu](https://github.com/dealfluence/adeu) | 43 | Python | Redline / Track Changes | **法律科技導向**：原生 Track Changes (w:ins/w:del) + CriticMarkup |
| 8 | [rockcj/Docx_MCP_cj](https://github.com/rockcj/Docx_MCP_cj) | 42 | — | Unknown | 無簡介 |
| 9 | [aaronsb/texflow-mcp](https://github.com/aaronsb/texflow-mcp) | 19 | — | LaTeX/MD | LaTeX/Markdown 排版 + 列印 |
| 10 | [cablate/mcp-doc-forge](https://github.com/cablate/mcp-doc-forge) | 17 | — | Generate | 生成 HTML/PDF/CSV |
| 11 | [hongkongkiwi/docx-mcp](https://github.com/hongkongkiwi/docx-mcp) | 15 | Rust | Full-featured | 純 Rust DOCX 操作，零外部依賴、內建 PDF/圖片生成 |
| 12 | [xt765/mcp_documents_reader](https://github.com/xt765/mcp_documents_reader) | 14 | — | Read-only | 讀取 DOCX/PDF/Excel/TXT |
| 13 | [dvejsada/mcp-ms-office-documents](https://github.com/dvejsada/mcp-ms-office-documents) | 13 | — | Create | 建立 PPTX/DOCX/EML/XLSX |
| 14 | [Rookie0x80/docx-mcp](https://github.com/Rookie0x80/docx-mcp) | 4 | Python | Basic | python-docx 基本包裝 |
| 15 | [bthompson-dev/LibreOfficeAI](https://github.com/bthompson-dev/LibreOfficeAI) | 3 | — | LibreOffice | AI + LibreOffice Writer/Impress |
| 16 | [chyinan/MCP-Word-Commander](https://github.com/chyinan/MCP-Word-Commander) | 1 | — | Text Processing | 輕量 Word 文字處理 |

---

## 2. 功能比較矩陣

### 2.1 核心能力

| 能力 | asset-aware-mcp | Office-Word-MCP (⭐1.6k) | MCP-Doc (⭐170) | adeu (⭐43) | hongkongkiwi/docx-mcp (⭐15) |
|------|:---:|:---:|:---:|:---:|:---:|
| **建立文件** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **讀取文件** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Markdown 編輯** | ✅ DFM | ❌ | ❌ | ❌ (CriticMarkup) | ❌ |
| **原生 XML 編輯** | ❌ | ✅ python-docx | ✅ python-docx | ✅ w:ins/w:del | ✅ Rust docx-rs |
| **Round-trip 保真** | ✅ 6 維度驗證 | ❌ | ❌ | ⚠️ Format Safety | ❌ |
| **Track Changes** | ❌ | ❌ | ❌ | ✅ 核心功能 | ❌ |
| **表格操作** | ✅ A2T (7 工具) | ✅ 格式化 | ✅ 合併/分割 | ❌ | ✅ |
| **圖片/圖表** | ✅ Base64 擷取 | ✅ 插入 | ✅ 插入 | ❌ (保留不動) | ✅ |
| **PDF 解析** | ✅ 雙引擎 (PyMuPDF + Marker) | ❌ | ❌ | ❌ | ✅ PDF 生成 |
| **知識圖譜** | ✅ LightRAG | ❌ | ❌ | ❌ | ❌ |
| **引用追蹤** | ✅ AssetRef (7 源) | ❌ | ❌ | ❌ | ❌ |
| **審計軌跡** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **VS Code 擴充** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **DDD 架構** | ✅ | ❌ | ❌ 單檔案 | ✅ 模組化 | ✅ |
| **測試覆蓋** | 430+ tests | 有 tests/ | 無 | 有 tests/ | 有 tests/ + bench |

### 2.2 DOCX 編輯範式比較

| 範式 | 代表專案 | 運作方式 | 優點 | 限制 |
|------|---------|---------|------|------|
| **python-docx 直接操作** | Office-Word-MCP, MCP-Doc | 透過 python-docx API 逐元素新增/修改段落、表格 | 精細控制、功能全面 | AI 需理解 Word 物件模型；不適合整段文字編輯 |
| **CriticMarkup + XML Patching** | adeu | 萃取文字 → AI 用 CriticMarkup 標記 → 反向注入 w:ins/w:del | 原生 Track Changes；法律場景最佳 | 僅支援文字替換，不支援結構變更 (新增表格/圖片) |
| **DFM (Docx-Flavored Markdown)** | **asset-aware-mcp** | docx → DocxIR → DFM markdown → AI 編輯 → DFM parse → docx | AI 直覺操作 Markdown；完整格式保留；6 維度保真度驗證 | 目前不支援 Track Changes |
| **Rust 原生解析** | hongkongkiwi/docx-mcp | Rust docx-rs 直接操作 OOXML | 高效能、零依賴 | 生態系小，功能發展慢 |

---

## 3. 深度競爭者分析

### 3.1 🥇 Office-Word-MCP-Server (⭐1,610)

**定位**: 生態系中星數最高、功能最全面的 Word MCP Server。

| 維度 | 評估 |
|------|------|
| **核心技術** | python-docx 包裝層，FastMCP 協定 |
| **工具數量** | ~30+ (建立/開啟/儲存/段落/表格/圖片/樣式/保護/PDF/合併) |
| **表格能力** | 完整：建立、格式化、合併儲存格、交替行色、欄寬管理 |
| **進階功能** | 密碼保護、數位簽章、註解擷取、找尋取代、自訂樣式 |
| **架構品質** | 基本模組化 (word_document_server/, tools/, utils/)，17 位貢獻者 |
| **發布** | PyPI (office-word-mcp-server)，uvx 安裝，Smithery 支援 |
| **限制** | ❌ 無 round-trip 編輯（是「建構」模式而非「編輯」模式）<br>❌ 無 PDF 解析/RAG/知識圖譜<br>❌ 無引用/審計功能 |

**vs asset-aware-mcp**: Office-Word-MCP 擅長從零建立文件，但無法對既有複雜文件做 Markdown 編輯再寫回。asset-aware-mcp 的 DFM pipeline 解決的是「已有一份複雜 .docx，AI 想修改其中幾段文字或表格」的場景。

### 3.2 🥈 adeu — Agentic DOCX Redlining Engine (⭐43)

**定位**: 法律科技 (Legal-Tech) 導向的 Track Changes 引擎。

| 維度 | 評估 |
|------|------|
| **核心技術** | 自研 RedlineEngine：文字萃取 → CriticMarkup diff → XML `w:ins`/`w:del` 注入 |
| **獨特能力** | **原生 Track Changes** — 在 Word 中顯示為紅線修訂 |
| **Format Safety** | 圖片/編號/標題保留（因為只修改目標文字 run） |
| **Run Coalescing** | 處理 Word 拆分 run 的問題（如 "Con" + "tract" → "Contract"） |
| **Fuzzy Matching** | 處理 LLM 記憶與實際文件的空白差異 |
| **CriticMarkup** | `{--old--}{++new++}{>>comment<<}` 中間表示 |
| **MCP 工具** | `read_docx`, `apply_edits_as_markdown`, `apply_structured_edits`, `manage_review_actions` |
| **限制** | ❌ 僅支援文字替換（不能新增表格/圖片/結構）<br>❌ 無 PDF/RAG/知識圖譜<br>❌ 無表格操作工具 |

**vs asset-aware-mcp**: adeu 專注「文字層級精準修訂 + Track Changes 可視化」，是法律合約審閱的最佳選擇。asset-aware-mcp 則覆蓋更廣（PDF 解析 + RAG + 表格 + 結構編輯），適合研究文件全生命週期管理。兩者有互補性。

### 3.3 🥉 MCP-Doc (⭐170)

**定位**: 輕量級 Cursor 友善的 Word 處理服務。

| 維度 | 評估 |
|------|------|
| **核心技術** | 單檔案 server.py，python-docx + FastMCP |
| **特色** | 區段編輯 (`replace_section`, `edit_section_by_keyword`) 可保留格式 |
| **限制** | ❌ 單檔案架構，無測試<br>❌ 無 PDF/RAG<br>❌ 功能覆蓋有限 |

**vs asset-aware-mcp**: MCP-Doc 適合快速原型，但缺乏生產級品質保證。

### 3.4 hongkongkiwi/docx-mcp (⭐15)

**定位**: 純 Rust 實作，追求零外部依賴的獨立部署。

| 維度 | 評估 |
|------|------|
| **核心技術** | Rust docx-rs，內建字型，內建 PDF/圖片生成 |
| **安全功能** | Readonly 模式、沙箱模式、白名單/黑名單 CLI、資源限制 |
| **企業功能** | 文件保護、專業範本 (信件/履歷/報告/發票/合約) |
| **限制** | ❌ 生態系小 (2 貢獻者)<br>❌ 無 last release<br>❌ 無 round-trip/RAG |

**vs asset-aware-mcp**: Rust 實作的效能優勢在 MCP 場景下不顯著（瓶頸在 LLM 而非文件處理）。其安全功能 (readonly/sandbox) 可作為參考。

---

## 4. 生態系分類

```
┌──────────────────────────────────────────────────────────┐
│                 MCP + DOCX 生態系光譜                     │
├──────────┬───────────┬───────────┬───────────┬───────────┤
│ Read-only│ Create    │ Edit      │ Redline   │ Full-Stack│
│          │ (Build)   │ (Modify)  │ (Track Δ) │ (ETL+Edit)│
│          │           │           │           │  +RAG)    │
├──────────┼───────────┼───────────┼───────────┼───────────┤
│mcp_docs_ │Office-Word│ MCP-Doc   │  adeu     │ asset-    │
│reader    │-MCP-Server│           │           │ aware-mcp │
│          │GenFilesMCP│           │           │           │
│          │docx-mcp   │           │           │           │
│          │(Rust)     │           │           │           │
├──────────┼───────────┼───────────┼───────────┼───────────┤
│ 14⭐     │ 1,610⭐   │ 170⭐     │ 43⭐      │ N/A       │
│          │ 66⭐      │           │           │ (本專案)   │
│          │ 15⭐      │           │           │           │
└──────────┴───────────┴───────────┴───────────┴───────────┘
```

---

## 5. asset-aware-mcp 的獨特價值

### 5.1 無人涉足的功能

以下功能在所有競爭者中 **均未實作**：

| 獨有功能 | 描述 | 競爭者狀態 |
|---------|------|-----------|
| **DFM Round-trip Editing** | docx → markdown → edit → docx，保留格式 | 0/16 競爭者 |
| **6 維度保真度驗證** | 結構/內容/格式/媒體/表格/合規 — 每次存檔自動驗證 | 0/16 競爭者 |
| **DFM Integrity Checker** | Post-ingest / Pre-save / Post-save 三階段自動修復 | 0/16 競爭者 |
| **A2T (Anything to Table)** | 7 個操作型工具，接受任何來源 (PDF/KG/URL/使用者輸入) | 0/16 競爭者 |
| **AssetRef 引用系統** | 7 種源類型，引用追蹤 + cell_history | 0/16 競爭者 |
| **PDF 雙引擎 + DOCX 編輯** | 同一 MCP 伺服器內整合 PDF 解析與 DOCX 編輯 | 0/16 競爭者 |
| **知識圖譜 + 文件編輯** | LightRAG 跨文件推理 + DFM 編輯 | 0/16 競爭者 |
| **VS Code 管理擴充** | 圖形化監控 + 一鍵 Excel 匯出 | 0/16 競爭者 |

### 5.2 技術護城河

```
                        ┌─────────────────┐
                        │  AI Agent       │
                        │  (Copilot)      │
                        └────────┬────────┘
                                 │
                    ┌────────────▼───────────────┐
                    │    36 MCP Tools             │
                    │   ┌─────┐ ┌─────┐ ┌─────┐ │
  競爭者止步於此 ──→  │   │ DOC │ │ DOCX│ │ A2T │ │
                    │   └──┬──┘ └──┬──┘ └──┬──┘ │
                    └──────┼───────┼───────┼─────┘
                           │       │       │
              ┌────────────▼──┐  ┌─▼────┐ ┌▼────────────────┐
              │ PDF ETL       │  │ DFM  │ │ Table Pipeline  │
              │ (PyMuPDF +    │  │ Round│ │ (Plan → Draft   │
              │  Marker)      │  │ Trip │ │  → Cite → Audit)│
              └───────┬───────┘  └──┬───┘ └────────┬────────┘
                      │             │              │
              ┌───────▼─────────────▼──────────────▼────────┐
              │           Knowledge Graph (LightRAG)         │
              │     跨文件推理 + 向量索引 + 圖譜查詢          │
              └──────────────────────────────────────────────┘
```

---

## 6. 潛在威脅

| 威脅 | 可能性 | 影響 | 因應策略 |
|------|:------:|:----:|---------|
| Office-Word-MCP 新增 round-trip 功能 | 低 | 高 | 其 python-docx 直接操作範式與 DFM 路線本質不同；持續深化 DFM 優勢 |
| adeu 擴展到結構編輯 | 中 | 中 | adeu 專注法律領域，擴展到通用場景需要大量重構 |
| Microsoft 官方推出 Word MCP Server | 中 | 高 | 差異化：醫學 RAG + A2T + 引用系統是 Microsoft 不會做的垂直場景 |
| LLM 原生支援 DOCX 格式 | 低 | 高 | 即便 LLM 可直接處理 DOCX，PDF 解析 + 知識圖譜 + A2T 仍有價值 |

---

## 7. 結論

asset-aware-mcp 在 MCP + DOCX 生態系中佔據一個 **獨特且難以複製的定位**：

1. **唯一** 提供 DFM round-trip 編輯 + 保真度驗證的 MCP Server
2. **唯一** 在同一伺服器整合 PDF ETL + DOCX 編輯 + 知識圖譜 + 表格工具鏈
3. **唯一** 擁有 VS Code 管理擴充的 DOCX MCP Server
4. **唯一** 具備引用追蹤 (AssetRef) 與審計軌跡的表格系統

競爭者多為「單一維度」解決方案 (建立 OR 讀取 OR 翻譯 OR 追蹤變更)，而 asset-aware-mcp 是 **全棧式研究文件處理平台**。

---

*本分析基於 2026-06 GitHub 公開資料。星數與功能可能隨時變動。*
