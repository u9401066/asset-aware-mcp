# asset-aware-mcp

> 🏥 Medical RAG with Asset-Aware MCP - 讓 AI Agent 精準存取 PDF 文獻中的表格、章節與知識圖譜

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [English](README.md)

## 🎯 為什麼需要 Asset-Aware MCP？

**AI 無法直接讀取你電腦裡的圖片檔案。** 這是一個常見的誤解。

| 方式 | AI 能分析圖片內容？ | 說明 |
|------|:-------------------:|------|
| ❌ 給 PNG 路徑 | 否 | AI 無法存取本地檔案系統 |
| ✅ **Asset-Aware MCP** | **是** | 透過 MCP 取得 Base64，AI 視覺能力可直接理解 |

### 實際效果

```
# 透過 MCP 取得圖片後，AI 可以直接分析：

User: 這張圖在講什麼？

AI: 這是 Scaled Dot-Product Attention 的架構圖：
    1. 輸入 Q (Query)、K (Key)、V (Value)
    2. Q 和 K 做 MatMul（矩陣乘法）
    3. 經過 Scale（縮放 1/√dₖ）
    4. 可選的 Mask（用於 decoder）
    5. SoftMax 歸一化
    6. 與 V 做最後一次 MatMul 得到輸出
```

**這就是 Asset-Aware MCP 的價值** - 讓 AI Agent 真正「看懂」你的 PDF 文獻中的圖表。

---

## ✨ 特色

- 📄 **Asset-Aware ETL** - PDF → Markdown，使用 **PyMuPDF** 自動識別表格、章節、圖片
- 🔄 **Async Job Pipeline** - 支援非同步任務處理，追蹤大型文件的處理進度
- 🗺️ **Document Manifest** - 結構化清單，Agent 可先「看地圖」再精準取用資料
- 🧠 **LightRAG 整合** - 知識圖譜 + 向量索引，支援跨文獻比較與推理
- 📊 **A2T (Anything to Table)** - 將 Agent 提取的資訊自動編排為專業 Excel 表格，支援 CRUD、**草稿持久化 (Drafting)** 與 **Token 節省續作**。
- �🔌 **MCP Server** - 透過 FastMCP 暴露工具與資源給 Copilot/Claude
- 🏥 **醫學研究導向** - 針對醫學文獻優化，支援 Base64 圖片傳輸供 Vision AI 分析

## 🏗️ 架構

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP Protocol (Tools & Resources)
┌─────────────────────▼───────────────────────────────────┐
│                 MCP Server (server.py)                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐   │
│  │   ingest    │ │  inspect    │ │     fetch       │   │
│  │  documents  │ │  manifest   │ │     asset       │   │
│  └─────────────┘ └─────────────┘ └─────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │          A2T (Anything to Table) 工作流         │   │
│  │  [規劃] → [草稿] → [批次寫入] → [提交]          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                  ETL Pipeline (DDD)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ PyMuPDF  │  │  Asset   │  │ LightRAG │              │
│  │ Adapter  │→ │  Parser  │→ │  Index   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│                   本地儲存 (Local Storage)              │
│  ./data/                                                │
│  ├── doc_{id}/        # 文件資產                        │
│  ├── tables/          # A2T 表格 (JSON/MD/XLSX)         │
│  │   └── drafts/      # 表格草稿 (持久化)               │
│  └── lightrag/        # 知識圖譜                        │
└─────────────────────────────────────────────────────────┘
```

## 📁 專案結構 (DDD)

```
asset-aware-mcp/
├── src/
│   ├── domain/              # 🔵 領域層：實體、值物件、介面定義
│   ├── application/         # 🟢 應用層：文件服務、表格服務 (A2T)、資產檢索
│   ├── infrastructure/      # 🟠 基礎設施層：PyMuPDF, LightRAG, Excel 渲染器
│   └── presentation/        # 🔴 表現層：MCP Server (FastMCP)
├── data/                    # 文件與資產儲存空間
├── docs/
│   └── spec.md              # 技術規格文件
├── tests/                   # 單元測試與整合測試
├── vscode-extension/        # VS Code 管理擴充功能
└── pyproject.toml           # uv 專案配置
```

## 🚀 快速開始

```bash
# 安裝依賴 (使用 uv)
uv sync

# 啟動 MCP Server
uv run python -m src.presentation.server

# 或透過 VS Code MCP 擴充功能使用
```

## 🔌 MCP 工具

| 工具 | 用途 |
|------|---------|
| `fetch_document_asset` | 精準取得表格 (MD) / 圖片 (B64) / 章節 |
| `consult_knowledge_graph` | 知識圖譜查詢，跨文獻比較 |
| `plan_table_schema` | AI 驅動的表格規劃與發想 (🆕) |
| `create_table_draft` | 開啟持久化草稿會話 (節省 Token) |
| `add_rows_to_draft` | 批次新增資料至草稿 |
| `commit_draft_to_table` | 將草稿正式提交為表格 |
| `resume_draft` / `resume_table` | 以極小上下文恢復工作 (節省 Token) |
| `update_cell` | 精準單元格編輯 |
| `render_table` | 渲染為專業 Excel 檔案 (含條件格式) |

## 🔧 技術棧

| 類別 | 技術 |
|----------|------------|
| 語言 | Python 3.10+ |
| ETL | **PyMuPDF** (fitz) |
| RAG | LightRAG (lightrag-hku) |
| MCP | FastMCP |
| 儲存 | 本地檔案系統 (JSON/Markdown/PNG) |

## 📋 文檔

- [技術規格](docs/spec.md) - 詳細技術規格
- [架構說明](ARCHITECTURE.md) - 系統架構
- [專案憲法](CONSTITUTION.md) - 專案原則

## 📄 授權

[Apache License 2.0](LICENSE)
