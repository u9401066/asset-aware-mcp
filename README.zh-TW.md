# asset-aware-mcp

> 🏥 具備資產感知能力的醫療 RAG MCP - 為 AI Agent 提供精確的 PDF 資產提取（表格、圖片、章節）與知識圖譜。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [English](README.md)

## 🎯 為什麼需要資產感知 MCP？

**AI 無法直接讀取你電腦裡的圖片檔案。** 這是一個常見的誤解。

| 方法 | AI 能分析圖片內容嗎？ | 說明 |
|------|:-------------------:|------|
| ❌ 提供 PNG 路徑 | 否 | AI 無法存取本地檔案系統 |
| ✅ **資產感知 MCP** | **是** | 透過 MCP 傳輸 Base64，讓 AI 視覺模型直接理解 |

### 實際效果

```
# 透過 MCP 獲取圖片後，AI 可以直接分析：

使用者：這張圖在講什麼？

AI：這是 Scaled Dot-Product Attention 的架構圖：
    1. 輸入：Q (Query), K (Key), V (Value)
    2. Q 與 K 的矩陣乘法 (MatMul)
    3. 縮放 (Scale, 1/√dₖ)
    4. 選用遮罩 (Mask)
    5. SoftMax 正規化
    6. 最後與 V 進行矩陣乘法得到輸出
```

**這就是資產感知 MCP 的價值** —— 讓 AI Agent 真正「看見」並理解你 PDF 文獻中的圖表。

---

## ✨ 特色

- 📄 **資產感知 ETL** - PDF → Markdown，**雙引擎** PDF 解析：
  - **PyMuPDF**（預設）- 快速提取（~50MB）
  - **Marker**（可選，`use_marker=True`）- 高精度結構化解析，產出含 bbox 座標的 `blocks.json`
- 🧩 **統一 Segmentation 匯出** - 產生正規化 `segmentation.json`，整合 manifest、blocks、reading order 與持久化 line span。
- 🖼️ **版面 Overlay 偵錯** - 可從 `original.pdf` 產生 page overlay，直接檢查 bbox、區塊類型與 reading order。
- 🔤 **按需 OCR 前處理** - 針對掃描型 PDF 提供可選 `ocrmypdf` 前處理流程，再進行 ETL。
- 🧭 **章節導航** - 動態層級章節樹，提供 5 個工具：瀏覽、搜尋、詳情、內容讀取、區塊提取，支援任意深度的標題層級。
- 🔄 **非同步任務流水線** - 支援大型文件的非同步處理與進度追蹤。
- 🗺️ **文件清單 (Manifest)** - 為 Agent 提供結構化的文件「地圖」，實現精確數據存取。
- 🧠 **LightRAG 整合** - 知識圖譜 + 向量索引，支援跨文件對比與推理。
- 🧾 **Citation-Aware KG 輸出** - `consult_knowledge_graph` 現在可直接回傳結構化 answer/reference payload，方便後續 agent workflow 直接做 citation-aware 處理。
- 📝 **Docx 即時編輯 (DFM)** - 以 Markdown 格式編輯 .docx 檔案，透過 **Docx-Flavored Markdown** 格式。支援 `.doc`、`.odt`、`.ods` 經 LibreOffice 自動轉換後攝入。提供 14 個工具：匯入、讀取、儲存、列出、刪除、匯出、strict 往返保真驗證、DOCX→PDF、DOCX→DOC、DOCX→ODT，以及 Docx ↔ A2T 表格橋接。
- 📊 **A2T (Anything to Table)** - 7 個 operation-based 工具，從**任意來源**（PDF 資產、知識圖譜、URL、使用者輸入）建立專業表格。支援：**引用管理** (AssetRef)、**變更審計**、**Schema 演進**、**模板**、**草稿機制**與**節省 Token 的續作模式**。
- 🖥️ **VS Code 管理擴充功能** - 提供圖形化介面監控伺服器狀態、已匯入文件，以及 **A2T 表格與草稿**，支援一鍵開啟 Excel。
- 🔌 **MCP 伺服器** - 透過 FastMCP 向 Copilot/Claude 開放工具與資源。
- 🏥 **醫療研究優化** - 針對醫療文獻優化，支援 Base64 圖片傳輸供 Vision AI 分析。

## 🏗️ 架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP 協定 (工具與資源)
┌─────────────────────▼───────────────────────────────────┐
│            MCP 伺服器 (模組化 Presentation 層)          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ tools/: 47 工具，7 個模組                       │   │
│  │   document (11) │ docx (14) │ section (5)       │   │
│  │   job (3) │ knowledge (2) │ table (7) │ profile (5) │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ resources/: 13 資源，2 個模組                   │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  ETL 流水線 (DDD)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ PyMuPDF  │  │  資產    │  │ LightRAG │              │
│  │ 轉接器   │→ │  解析器  │→ │  索引    │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                      本地儲存                           │
│  ./data/                                                │
│  ├── doc_{id}/        # 文件資產 (Markdown/圖片)        │
│  ├── docx_{id}/       # Docx IR + DFM + 資產            │
│  ├── tables/          # A2T 表格 (JSON/MD/XLSX)         │
│  │   └── drafts/      # 表格草稿 (持久化)               │
│  └── lightrag_db/     # 知識圖譜資料庫                  │
└─────────────────────────────────────────────────────────┘
```

## 📁 專案結構 (DDD)

```
asset-aware-mcp/
├── src/
│   ├── domain/              # 🔵 領域層：實體、數值物件、介面定義
│   ├── application/         # 🟢 應用層：文件服務、表格服務 (A2T)、資產服務
│   ├── infrastructure/      # 🟠 基礎設施層：PyMuPDF、LightRAG、Excel 渲染器
│   └── presentation/        # 🔴 展現層：MCP 伺服器 (FastMCP)
├── data/                    # 文件與資產儲存目錄
├── docs/
│   └── spec.md              # 技術規格書
├── tests/                   # 單元測試與整合測試
├── vscode-extension/        # VS Code 管理擴充套件
└── pyproject.toml           # uv 專案配置
```

## 📐 架構圖

專案視覺圖表。所有圖片套用一致的 GitHub README 風格。

| 圖表 | 說明 |
|-----|------|
| [01 — 系統架構](docs/diagrams/01-system-architecture.jpg) | 完整架構：Telegram → Gateway → MCP Adapter → Ollama |
| [02 — 資料結構](docs/diagrams/02-data-layout.jpg) | 48 工具分 7 大類 + 資料樹狀圖 |
| [03 — PDF 解讀流程](docs/diagrams/03-pdf-ingestion-pipeline.jpg) | 7 階段流程：PDF 上傳 → 知識圖譜 |
| [04 — DOCX 雙向編輯](docs/diagrams/04-docx-edit-pipeline.jpg) | DOCX 吃入 → TableContext 編輯 → 往返存檔 |
| [05 — 知識圖譜搜尋](docs/diagrams/05-knowledge-graph-search.jpg) | 跨文件搜尋的三條平行路徑 |
| [06 — 安裝步驟](docs/diagrams/06-installation-steps.jpg) | 7 步驟從 clone 到驗證 |
| [07 — PDF ETL 流程](docs/diagrams/07-pdf-etl-pipeline.jpg) | 雙引擎解析：PyMuPDF + Marker |
| [08 — KG 架構](docs/diagrams/08-knowledge-graph-architecture.jpg) | lightrag-hku 三層知識圖譜架構 |
| [08 — KG 架構](docs/diagrams/08-knowledge-graph-architecture.jpg) | lightrag-hku 三層知識圖譜架構 |

> 💡 所有生成 prompt 保存在 [docs/diagrams/prompts/README.md](docs/diagrams/prompts/README.md)，方便再生成時維持風格一致。

## 🚀 快速開始

```bash
# 安裝依賴 (使用 uv) — 預設不安裝 Marker/torch
uv sync

# 如需高精度結構化解析，再額外安裝 Marker backend
uv sync --extra marker

# 啟動 MCP 伺服器
uv run python -m src.presentation.server

# 或使用 VS Code 擴充套件進行圖形化管理
```

Runtime 說明：
VS Code 擴充套件在透過 `uv` / `uvx` 啟動 MCP server 時，會優先使用受管理的 Python 3.11 runtime。這可避免終端使用者機器上發生原生套件編譯，特別是未安裝 Xcode Command Line Tools 的 macOS；但專案本身仍保留對較新 Python 版本的相容性。

Marker 說明：
`marker-pdf` 現在是可選依賴，因為它可能拉入 `torch`、`surya` 與平台相關的 ML wheels。預設安裝只使用 PyMuPDF 後端；只有在你真的需要 `use_marker=True` 或 `parse_pdf_structure` 時才建議額外安裝。

## 🔌 MCP 工具

### 文件與資產工具

| 工具 | 用途 |
|------|------|
| `ingest_documents` | 處理 PDF 檔案，可選用 Marker 後端 (`use_marker=True` 產出 blocks.json) |
| `list_documents` | 列出所有已攝入文件與資產統計 |
| `delete_document` | 刪除已攝入 PDF、本地 artifacts，以及啟用時對應的 LightRAG 索引 |
| `convert_pdf_to_docx` | 將 PDF 內容層重建為可讀 DOCX |
| `convert_pdf_to_pptx` | 依據 PDF Markdown 與圖像重建可編輯的 PPTX 投影片 |
| `inspect_document_manifest` | 在抓取資產前先檢視文件結構 |
| `fetch_document_asset` | 精確獲取表格 (MD) / 圖片 (B64) / 章節內容 |
| `parse_pdf_structure` | 使用 Marker 進行高精度結構化 PDF 解析 |
| `search_source_location` | 搜尋精確來源位置（頁碼 + bbox） |
| `export_document_segmentation` | 匯出含 reading order 與 line range 的統一 `segmentation.json` |
| `visualize_document_layout` | 產生 page overlay，檢查 bbox / 類型 / reading order |
| `ocr_pdf_document` | 執行 OCR 前處理，產生後續 ETL 可用的 PDF |

### 工作管理工具

| 工具 | 用途 |
|------|------|
| `get_job_status` | 取得非同步 ETL 工作進度與結果 |
| `list_jobs` | 列出目前或歷史工作 |
| `cancel_job` | 取消執行中的 ETL 工作 |

### 知識圖譜工具

| 工具 | 用途 |
|------|------|
| `consult_knowledge_graph` | 支援 `structured`、`data`、`text` 三種回傳模式的 citation-aware 知識圖譜查詢 |
| `export_knowledge_graph` | 匯出圖譜摘要 / JSON / Mermaid 視圖 |

知識圖譜補充：
- `consult_knowledge_graph` 預設使用 `response_mode="structured"`，可回傳 `answer`、`references`、`metadata`、`retrieval`、`counts`。
- 若只需要 retrieval payload、不想讓 LLM 合成最終答案，可使用 `response_mode="data"`；若要保留舊版純文字行為，使用 `response_mode="text"`。

### 章節導航工具（動態層級）

| 工具 | 用途 |
|------|------|
| `list_section_tree` | 顯示完整章節樹狀結構（支援任意深度） |
| `get_section_detail` | 取得特定章節的詳細資訊 |
| `get_section_blocks` | 提取章節內所有區塊（含頁碼 + bbox） |
| `search_sections` | 搜尋章節標題 |
| `get_section_content` | 讀取章節內容 |

### Docx 編輯工具 (DFM — Docx-Flavored Markdown)

> 以 Markdown 語法編輯 .docx/.doc 檔案，往返保留格式、表格、媒體。支援舊版 `.doc` 自動轉換。

| 工具 | 用途 |
|------|------|
| `ingest_docx` | 匯入 .docx/.doc 並拆解為 DFM 區塊 |
| `get_docx_content` | 讀取指定區塊的 DFM 內容 |
| `save_docx` | 將 DFM 編輯寫回 .docx |
| `list_docx_blocks` | 列出文件區塊結構 |
| `list_docx_documents` | 列出所有已攝入的 DOCX/DFM 文件 |
| `delete_docx` | 刪除已攝入的 DOCX/DFM 文件及其本地 artifacts |
| `convert_docx_to_pdf` | 以保真模式輸出 PDF |
| `convert_docx_to_doc` | 以保真模式輸出 DOC |
| `docx_validate_roundtrip` | 6 維度往返保真驗證，支援 strict fail-closed 模式 |
| `docx_table_to_context` | 橋接：Docx 表格 → A2T 上下文 |
| `docx_table_from_context` | 橋接：A2T 表格 → Docx 表格 |
| `docx_chart_data` | 提取 Docx 圖表數據 |
| `export_markdown` | 匯出 Markdown 為 .docx/.pdf/.doc |

### A2T (Anything to Table) 工具 — 7 個 Operation-Based 工具

> Agent-friendly 設計：每個工具透過 `operation` 參數處理多種操作。
> 表格接受**任意來源** — PDF 資產、KG 實體、外部 URL 或使用者輸入。

| 工具 | 操作 | 用途 |
|------|------|------|
| `plan_table` | `schema` / `templates` / `from_template` | 規劃表格結構、瀏覽 4 個內建模板、從模板建表 |
| `table_manage` | `create` / `delete` / `list` / `preview` / `resume` / `render` / `add_column` / `remove_column` / `rename_column` | 表格生命週期 + Schema 演進 |
| `table_data` | `add_rows` / `get_row` / `update_row` / `delete_row` / `get_cell` / `update_cell` / `clear_cell` | 資料列與儲存格 CRUD |
| `table_cite` | `add` / `get` / `remove` / `cell_history` | 引用管理（AssetRef 7 種來源類型） |
| `table_history` | `changes` / `tokens` | 變更審計軌跡 + Token 估算 |
| `table_draft` | `create` / `update` / `add_rows` / `resume` / `commit` / `list` / `delete` | 草稿工作流（持久化、斷點續傳） |
| `discover_sources` | — | 跨文件資料來源探索（sections、tables、figures、KG） |

### ETL Profile 工具

不同期刊/文件格式需要不同的提取設定，使用這些工具切換 Profile。

| 工具 | 用途 |
|------|------|
| `list_etl_profiles` | 列出所有可用的 Profile（default, arxiv, nature, ieee, elsevier）|
| `get_etl_profile` | 取得特定 Profile 的詳細配置 |
| `get_current_etl_profile` | 顯示目前使用的 Profile |
| `set_etl_profile` | 切換後續文件處理使用的 Profile |
| `load_etl_profile_from_json` | 從 JSON 檔案載入自訂 Profile |

## 🔧 技術棧

| 類別 | 技術 |
|----------|------------|
| 語言 | Python 3.10+ |
| ETL | **PyMuPDF** (fitz) + **Marker** (可選，高精度) |
| RAG | LightRAG (lightrag-hku) |
| MCP | FastMCP |
| 儲存 | 本地檔案系統 (JSON/Markdown/PNG) |

## 📋 相關文件

安裝建議：
- 預設安裝：`uv sync`
- 需要 Marker 時再安裝：`uv sync --extra marker`
- VS Code extension 要啟用 Marker 時，建議先用 `torchBackend=cpu`，除非你明確需要 GPU wheels

- [技術規格書](docs/spec.md) - 詳細技術定義
- [系統架構](ARCHITECTURE.md) - 架構設計說明
- [專案憲法](CONSTITUTION.md) - 開發原則與規範

## 📄 授權

[Apache License 2.0](LICENSE)
