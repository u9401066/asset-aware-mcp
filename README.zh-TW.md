# asset-aware-mcp

> 給 AI Agent 使用的 citation-ready 文件基礎設施：把 PDF、DOCX、表格、
> 圖片與 evidence span 轉成可重用資產，並組成 Foam／LightRAG wiki。

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [English](README.md) · [文件網站](https://u9401066.github.io/asset-aware-mcp/#/overview-zh) · [GitHub Wiki](https://github.com/u9401066/asset-aware-mcp/wiki)

## v1.0.1 可靠性翻新

- 大型 PDF 文字、表格與圖片結果改用 private、atomic、具大小上限的
  MessagePack 檔案交接，不再透過 multiprocessing pipe，也不反序列化可執行的
  pickle。多 MB raster 不會再因 pipe backpressure 卡死；partial、oversized、
  malformed 或 worker crash 一律 fail closed。
  Worker timeout 環境值必須是有限數；`NaN`／無限值會回退到安全預設值。
  有限的 `<=0` 值僅保留為歷史 direct mode 相容開關，managed production
  launcher 不應使用。
- Codex managed MCP 設定現在用真實 TOML parser 驗證，會保留 custom 與 unrelated
  tables，設定 180／900 秒啟動與工具 timeout，且不把 credential value 寫入檔案。
  隔離的 working directory 加上 `ASSET_AWARE_DISABLE_DOTENV=true`，也避免 server
  在啟動後又偷偷讀取無關 workspace 的 `.env`。
- Codex／Cline／Copilot 的全域設定寫入現在受 workspace trust 保護，且只使用
  extension 精確版本與隔離的 global storage；偽造同名 repository 不能把本地
  Python 或 `.env` 值持久化進全域 agent launcher。
- MCP SDK 2 operational log 固定走 stderr；空白或空 ingest request 會在建立 job
  前拒絕。true-stdio 回歸則實際驗證大型圖片、表格、citation-ready evidence、
  完整 bundle hash、Foam notes、deterministic re-export，以及來源 PDF 完全不變。
- GitHub Pages 已換成雙語 responsive Evidence Rail、精確 30-tool explorer、安裝／
  開發注意事項、生成式文件 reader 與 GitHub／Release／Issue 入口，不再公開過時的
  raster 架構截圖。

## 🎯 為什麼需要資產感知 MCP？

**只有 server-local 圖片路徑，並不是可攜式的 multimodal payload。** Agent 能否解析該路徑，
取決於 client、sandbox 與檔案權限，不能假設兩端共用同一個檔案系統。

| 方法 | AI 能分析圖片內容嗎？ | 說明 |
|------|:-------------------:|------|
| ⚠️ 只提供 PNG 路徑 | 視 client 而定 | client 可能在遠端或 sandbox 內，不能安全假設 server 路徑存在於本地 |
| ✅ **資產感知 MCP** | **相容 multimodal client 可用** | 透過 MCP 擷取具大小上限的實際圖片 bytes，再交給 vision model |

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

- 📄 **資產感知 ETL** - PDF → Markdown，採可插拔多引擎解析架構（`ETL_ENGINE`）：
  - **PyMuPDF**（預設）- 快速提取（~50MB），免模型
  - **PyMuPDF4LLM**（`[pdf-plus]`）- 同生態 drop-in 升級，具版面感知，免 GPU
  - **Docling**（`[docling]`）- MIT 授權，layout+table+formula+chart 引擎；主環境無法直接安裝時會透過獨立 `.venv-docling` 直譯器橋接（見 [docs/docling-setup.md](docs/docling-setup.md)）
  - **MinerU** - adapter 保留；因上游仍鎖住有漏洞的 `transformers<5` 鏈，套件 extra 暫停安裝
  - **Marker** - adapter 僅保留供評估；upstream `marker-pdf` 與 patched Pillow 安全底線衝突期間，production selection 一律 fail closed。歷史參數 `use_marker` 現在只代表「偏好目前設定的 structured extractor」，不能繞過 security hold。
- 🧩 **統一 Segmentation 匯出** - 產生正規化 `segmentation.json`，整合 manifest、blocks、reading order 與持久化 line span。
- 🩺 **安全 PDF Preflight Router** - `document(op="preflight")` 逐頁分類 native、sparse、image、scanned、hybrid，輸出 1-based/top-left locator、來源 SHA-256、OCR 理由與引擎建議；檢查在具 timeout／資源上限的隔離 process 執行。
- 📦 **可重用 Agent Asset Bundle** - `document(op="export_assets")` 產生 deterministic `manifest.json`、`assets.jsonl`、媒體副本，以及可攜式 Foam `index.md`／`notes/**` 子樹，完整保留 stable ID、hash、locator 與 citation ref。
- 🛡️ **PDF 安全、結構與覆蓋率稽核** - 受 OpenDataloader 啟發的 artifact-only 報告：`ai_safety_report.json`、`native_structure.json`、`segmentation_coverage.json`，透過既有 `document` facade 提供，不增加公開工具數；`document(op="prepare_ai")` 與 `document(op="auto")` 會回傳 agent-ready 狀態與下一步。
- 🖼️ **版面 Overlay 偵錯** - 可從 `original.pdf` 產生 page overlay，直接檢查 bbox、區塊類型與 reading order。
- 🔤 **按需 OCR 前處理** - 針對掃描型 PDF 提供可選 `ocrmypdf` 前處理流程，再進行 ETL。
- 🧭 **章節導航** - 透過 `section` facade 提供動態層級章節樹：瀏覽、搜尋、詳情、內容讀取、區塊提取，支援任意深度的標題層級。
- 🔄 **非同步任務流水線** - 支援大型 PDF ingest、目前設定的 structured parse、OCR 與 conversion 的非同步處理與進度追蹤。
- 🔀 **混合格式批次攝入** - `document(op="auto", file_paths=[...])` 會自動偵測 PDF 與 DOCX/DOC/ODT/ODS 混合的批次，於單一 background job 內以各自正確的引擎攝入每個檔案，隔離單檔失敗不中斷其餘檔案，並回報逐檔進度——不需新增公開工具。
- 🗺️ **文件清單 (Manifest)** - 為 Agent 提供結構化的文件「地圖」，實現精確數據存取。
- 🧠 **LightRAG 整合** - 知識圖譜 + 向量索引，支援跨文件對比與推理。
- 🧾 **Verified Citation Bundles** - `citation_bundle`、Foam evidence pack、citation health check、table/figure evidence notes 與 claim promotion 可輸出含 locator、quote/hash、context、CRAAP scaffold 與 verification 的 evidence bundle。
- 📝 **Docx 即時編輯 (DFM)** - 以 Markdown 格式編輯 .docx 檔案，透過 **Docx-Flavored Markdown** 格式。支援 `.docx` / `.docm`，也支援 `.doc`、`.odt`、`.ods` 經 LibreOffice 自動轉換後攝入。balanced surface 保留 6 個 DOCX/DFM 公開入口，涵蓋匯入、讀取、儲存、驗證、轉換、表格結構編輯計畫，以及 Docx ↔ A2T 表格橋接。
- 📊 **A2T (Anything to Table)** - 7 個 operation-based 工具，從**任意來源**（PDF 資產、知識圖譜、URL、使用者輸入）建立專業表格。支援：穩定 row ID、row search/filter/paging、citation coverage、artifact-only 大表輸出、跳過大型表格時的可操作 UX、**引用管理** (AssetRef)、**變更審計**、**Schema 演進**、**模板**、**草稿機制**與**節省 Token 的續作模式**。
- 🖥️ **VS Code 管理擴充功能** - 提供圖形化介面監控伺服器狀態、已匯入文件、document artifacts、citation spans，以及 **A2T 表格與草稿**，支援一鍵開啟 Excel。
- 🔌 **MCP SDK 2 伺服器** - 使用官方 Python SDK `MCPServer`、runtime context injection 與 v2 client；刻意不支援 MCP SDK v1。
- 🔬 **研究級、領域中立資產** - 可處理學術、技術、政策與營運文件；具大小上限的圖片 bytes 能讓相容的 multimodal client 分析圖像，而不是依賴 server-local 路徑。

## 🏗️ 架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP 協定 (工具與資源)
┌─────────────────────▼───────────────────────────────────┐
│            MCP 伺服器 (模組化 Presentation 層)          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ tools/: 30 個公開工具（balanced surface）       │   │
│  │   17 個 facade tools + 13 個高頻 shortcuts      │   │
│  │   compact=17 │ legacy/direct 相容模式=63        │   │
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
│  ├── {doc_id}/        # PDF 文件 artifacts             │
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
│   └── presentation/        # 🔴 展現層：MCP SDK 2 MCPServer
├── data/                    # 文件與資產儲存目錄
├── docs/
│   └── spec.md              # 技術規格書
├── tests/                   # 單元測試與整合測試
├── vscode-extension/        # VS Code 管理擴充套件
└── pyproject.toml           # uv 專案配置
```

## 📐 架構與流程

持續維護且會跟實作一起驗證的入口是[文件網站](https://u9401066.github.io/asset-aware-mcp/)、
[架構說明](docs/wiki/Architecture.md)、[PDF 流程](docs/wiki/PDF-Document-Workflow.md)、
[MCP 工具目錄](docs/wiki/MCP-Tools.md)與[發布檢核](docs/wiki/Release-And-Testing.md)。
這些文字與網站資料會由 gate 檢查，避免工具數、引擎 security hold 或發布流程藏在已過時的截圖裡。

## 🚀 快速開始

```bash
# 安裝依賴 (使用 uv) — 預設維持快速 PyMuPDF backend
uv sync

# 可選高精度 PDF→資產引擎：
# uv sync --extra pdf-plus   # PyMuPDF4LLM：同生態 drop-in 版面感知升級
# uv sync --extra docling    # Docling：MIT 授權 layout+table+formula+chart
# MinerU 與 Marker packaged extras 目前皆為安全暫停。
# 安裝後設定 ETL_ENGINE=pymupdf4llm|docling。

# 啟動 MCP 伺服器
uv run python -m src.presentation.server

# 或使用 VS Code 擴充套件進行圖形化管理
```

Runtime 說明：
VS Code 擴充套件在透過 version-pinned `uv tool run` 啟動 MCP server 時，會優先使用受管理的 Python 3.11 runtime，並在舊機器上 fallback 到 Python 3.10。這可避免終端使用者機器上發生原生套件編譯，特別是未安裝 Xcode Command Line Tools 的 macOS；但專案本身仍保留對較新 Python 版本的相容性。

安裝範圍說明：
- VSIX 以使用者範圍安裝。trusted workspace 中的 VS Code 原生 MCP provider 可使用
  workspace-scoped `DATA_DIR`、cache、settings 與 `.env`；local source 只在 extension
  Development/Test mode（或未來明示 opt-in）使用。
- Codex 與 Cline 的全域 entry 永遠從 extension global storage 啟動
  `asset-aware-mcp==<extension-version>`，不繼承 workspace local source、workspace
  setting 或 repository `.env`。Restricted Mode 完全跳過 external config 寫入與
  assistant asset sync。

引擎選擇說明：
`ETL_ENGINE` 選擇拆解後端（預設 `pymupdf`）。目前 packaged structured engines 是 `pymupdf4llm` 與 `docling`，皆採懶加載，extra 未安裝時安全降級至 PyMuPDF。Marker 因 `marker-pdf` 仍要求 `Pillow<11` 而暫停；MinerU 3.4.4 又鎖定 `transformers<5`，但安全修補需要 `transformers>=5.5`，因此兩者 adapter 留在程式庫中、packaged extra 則不安裝已知有漏洞的 dependency chain。攝入前可先用 `document(op="preflight", pdf_path="...")` 決定走原生快速抽取、OCR 或 Docling。

Agent asset／Foam handoff：

```text
document(op="preflight", pdf_path="/papers/source.pdf")
document(op="auto", file_paths=["/papers/source.pdf"])
document(op="export_assets", doc_id="doc_...", output_dir="agent-assets")
```

匯出目錄是 deterministic 且可攜的：`manifest.json` 是 bundle contract，
`assets.jsonl` 是 agent-readable inventory，`index.md` 與 `notes/**` 可直接掛入或複製到 Foam workspace。

## 🔌 MCP 工具

預設 runtime surface 是 **balanced**：30 個公開工具，保留完整文件工作流，但避免 agent 一開始就面對過多 direct tools。它由 17 個 operation-based facade tools 加上 13 個高頻 shortcuts 組成。若需要更嚴格 allow-list，可設定 `ASSET_AWARE_MCP_TOOL_SURFACE=compact` 只公開 17 個 facade；若舊 client 仍依賴 direct tool 名稱，可設定 `ASSET_AWARE_MCP_TOOL_SURFACE=legacy` 或 `ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS=true` 開啟 63-tool 相容庫存。

| 範圍 | Balanced 公開工具 |
|------|-------------------|
| 文件、資產、證據、轉換 | `document`, `document_asset`, `evidence`, `convert_document`, `ingest_documents`, `list_documents`, `parse_pdf_structure`, `fetch_document_asset`, `find_evidence_spans`, `verify_citation_ref`, `citation_bundle` |
| DOCX / DFM | `docx`, `docx_table`, `ingest_docx`, `get_docx_content`, `save_docx`, `docx_table_edit_plan` |
| 章節、工作、KG、ETL Profile | `section`, `job`, `get_job_status`, `list_jobs`, `knowledge`, `etl_profile` |
| A2T 表格 | `plan_table`, `table_manage`, `table_data`, `table_cite`, `table_history`, `table_draft`, `discover_sources` |

完整 operation、shortcut rationale 與 legacy direct-tool mapping 請見 [MCP Tools](docs/wiki/MCP-Tools.md) 與 [Tool Consolidation](docs/wiki/MCP-Tool-Consolidation.md)。

Agent 接力建議：
新 PDF 用 `document(op="auto", file_paths=[...])`，既有文件用 `document(op="auto", doc_id="...")` 或 `document(op="prepare_ai", doc_id="...")`。`document(op="prepare_ai", output_format="json")` 會回傳 v2 readiness contract：`status`、`blockers`、`warnings`、`capabilities`、`artifacts`、`missing_audits`、`invalid_audits`、`audit_artifacts`、`next_actions`。`document(op="audit", doc_id="...")` 只會在現有稽核 artifacts 存在且有效時重用；需要全部重建時傳 `refresh=true`。readiness 與 job status 的 artifact discovery 是 read-only，不會因查狀態建立新的文件資料夾。

PDF 稽核注意：
這些報告是受 OpenDataloader 類 artifact 工作流啟發，但不是 sanitizer、PDF/UA 認證，也不是 OpenDataloader 相容層；它們會保留來源 artifact，並以保守診斷供人工或 agent 後續檢查。

## 🔧 技術棧

| 類別 | 技術 |
|----------|------------|
| 語言 | Python 3.10+ |
| ETL | **PyMuPDF**（預設）+ 安全可選 **PyMuPDF4LLM**／**Docling**；MinerU、Marker adapter 暫時 dependency security hold |
| RAG | LightRAG (lightrag-hku) |
| MCP | 官方 Python MCP SDK 2（`MCPServer`）；不支援 SDK v1 |
| 儲存 | 本地檔案系統 (JSON/Markdown/PNG) |

## 📋 相關文件

安裝建議：
- 預設安裝：`uv sync`
- OpenRouter optional preset（v0.6.35 起）：在 VS Code extension Settings 選 `openrouter`，填入 `OPENROUTER_API_KEY`；預設 `OPENROUTER_MODEL=liquid/lfm-2.5-1.2b-instruct:free`，適合低成本快速摘要與 RAG 草稿查詢。
- 高精度 PDF 引擎：`uv sync --extra pdf-plus`（PyMuPDF4LLM）或 `uv sync --extra docling`（Docling），再設定對應 `ETL_ENGINE`。Docling 附跨平台隔離安裝腳本，見 [docs/docling-setup.md](docs/docling-setup.md)。
- MinerU／Marker：adapter 保留供追蹤上游；packaged extras 暫為空，直到 dependency cap 可解析到已修補的 transformers／Pillow。
- VS Code extension：`assetAwareMcp.enableMarkerBackend` 設定仍保留，但 security hold 期間 launcher 不會安裝 `marker-pdf`。

- [技術規格書](docs/spec.md) - 詳細技術定義
- [系統架構](ARCHITECTURE.md) - 架構設計說明
- [專案憲法](CONSTITUTION.md) - 開發原則與規範

## 📄 授權

[Apache License 2.0](LICENSE)
