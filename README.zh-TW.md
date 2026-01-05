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

- 📄 **資產感知 ETL** - PDF → Markdown，使用 **PyMuPDF** 自動識別表格、章節與圖片。
- 🔄 **非同步任務流水線** - 支援大型文件的非同步處理與進度追蹤。
- 🗺️ **文件清單 (Manifest)** - 為 Agent 提供結構化的文件「地圖」，實現精確數據存取。
- 🧠 **LightRAG 整合** - 知識圖譜 + 向量索引，支援跨文件對比與推理。
- 📊 **A2T (Anything to Table)** - 自動將 Agent 提取的資訊編排為專業 Excel 表格，支援 CRUD、**草稿機制**與**節省 Token 的續作模式**。
- 🔌 **MCP 伺服器** - 透過 FastMCP 向 Copilot/Claude 開放工具與資源。
- 🏥 **醫療研究優化** - 針對醫療文獻優化，支援 Base64 圖片傳輸供 Vision AI 分析。

## 🏗️ 架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP 協定 (工具與資源)
┌─────────────────────▼───────────────────────────────────┐
│                 MCP 伺服器 (server.py)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │   ingest    │ │  inspect    │ │     fetch       │   │
│  │  documents  │ │  manifest   │ │     asset       │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │          A2T (Anything to Table) 工作流         │   │
│  │  [規劃] → [草稿] → [批量新增] → [提交]          │   │
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
│  ├── tables/          # A2T 表格 (JSON/MD/XLSX)         │
│  │   └── drafts/      # 表格草稿 (持久化)               │
│  └── lightrag/        # 知識圖譜資料庫                  │
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

## 🚀 快速開始

```bash
# 安裝依賴 (使用 uv)
uv sync

# 啟動 MCP 伺服器
uv run python -m src.presentation.server

# 或使用 VS Code 擴充套件進行圖形化管理
```

## 🔌 MCP 工具

| 工具 | 用途 |
|------|------|
| `fetch_document_asset` | 精確獲取表格 (MD) / 圖片 (B64) / 章節內容 |
| `consult_knowledge_graph` | 知識圖譜查詢，支援跨文件對比 |
| `plan_table_schema` | AI 驅動的表格結構規劃與腦力激盪 (🆕) |
| `create_table_draft` | 開啟持久化草稿階段 (節省 Token) |
| `add_rows_to_draft` | 批量向草稿新增數據 |
| `commit_draft_to_table` | 將草稿正式轉為表格檔案 |
| `resume_draft` / `resume_table` | 以極小上下文恢復工作 (節省 Token) |
| `update_cell` | 精確的儲存格等級編輯 |
| `render_table` | 渲染為專業 Excel 檔案 (含條件格式) |

## 🔧 技術棧

| 類別 | 技術 |
|----------|------------|
| 語言 | Python 3.10+ |
| ETL | **PyMuPDF** (fitz) |
| RAG | LightRAG (lightrag-hku) |
| MCP | FastMCP |
| 儲存 | 本地檔案系統 (JSON/Markdown/PNG) |

## 📋 相關文件

- [技術規格書](docs/spec.md) - 詳細技術定義
- [系統架構](ARCHITECTURE.md) - 架構設計說明
- [專案憲法](CONSTITUTION.md) - 開發原則與規範

## 📄 授權

[Apache License 2.0](LICENSE)
