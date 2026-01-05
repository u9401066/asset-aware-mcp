# asset-aware-mcp

> 🏥 Medical RAG with Asset-Aware MCP - 讓 AI Agent 精準存取 PDF 文獻中的表格、章節與知識圖譜

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [繁體中文](README.zh-TW.md)

## 🎯 Why Asset-Aware MCP?

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

## ✨ Features

- 📄 **Asset-Aware ETL** - PDF → Markdown, using **PyMuPDF** to automatically identify tables, sections, and images
- 🔄 **Async Job Pipeline** - Supports asynchronous task processing, tracking progress for large documents
- 🗺️ **Document Manifest** - Structured list, allowing Agents to "see the map" before precisely accessing data
- 🧠 **LightRAG Integration** - Knowledge Graph + Vector Index, supporting cross-document comparison and reasoning
- 📊 **A2T (Anything to Table)** - Automatically orchestrate information extracted by Agents into professional Excel tables, supporting CRUD, **Drafting**, and **Token-efficient resumption**.
- �🔌 **MCP Server** - Exposes tools and resources to Copilot/Claude via FastMCP
- 🏥 **Medical Research Focus** - Optimized for medical literature, supporting Base64 image transmission for Vision AI analysis

## 🏗️ Architecture

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
│  │          A2T (Anything to Table) Workflow       │   │
│  │  [Plan] → [Draft] → [Batch Add] → [Commit]      │   │
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
│                   Local Storage                         │
│  ./data/                                                │
│  ├── doc_{id}/        # Document Assets                 │
│  ├── tables/          # A2T Tables (JSON/MD/XLSX)       │
│  │   └── drafts/      # Table Drafts (Persistence)      │
│  └── lightrag/        # Knowledge Graph                 │
└─────────────────────────────────────────────────────────┘
```

## 📁 Project Structure (DDD)

```
asset-aware-mcp/
├── src/
│   ├── domain/              # 🔵 Domain: Entities, Value Objects, Interfaces
│   ├── application/         # 🟢 Application: Doc Service, Table Service (A2T), Asset Service
│   ├── infrastructure/      # 🟠 Infrastructure: PyMuPDF, LightRAG, Excel Renderer
│   └── presentation/        # 🔴 Presentation: MCP Server (FastMCP)
├── data/                    # Document and Asset Storage
├── docs/
│   └── spec.md              # Technical Specification
├── tests/                   # Unit and Integration Tests
├── vscode-extension/        # VS Code Management Extension
└── pyproject.toml           # uv Project Config
```

## 🚀 Quick Start

```bash
# Install dependencies (using uv)
uv sync

# Run MCP Server
uv run python -m src.presentation.server

# Or use the VS Code extension for graphical management
```

## 🔌 MCP Tools

| Tool | Purpose |
|------|---------|
| `fetch_document_asset` | Precisely retrieve tables (MD) / figures (B64) / sections |
| `consult_knowledge_graph` | Knowledge graph query, cross-document comparison |
| `plan_table_schema` | AI-driven schema planning & brainstorming (🆕) |
| `create_table_draft` | Start a persistent draft session (Token-efficient) |
| `add_rows_to_draft` | Batch add data to draft |
| `commit_draft_to_table` | Finalize draft into a formal table |
| `resume_draft` / `resume_table` | Resume work with minimal context (Save tokens) |
| `update_cell` | Precise cell-level editing |
| `render_table` | Render to professional Excel file (with conditional formatting) |

## 🔧 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.10+ |
| ETL | **PyMuPDF** (fitz) |
| RAG | LightRAG (lightrag-hku) |
| MCP | FastMCP |
| Storage | Local filesystem (JSON/Markdown/PNG) |

## 📋 Documentation

- [Technical Spec](docs/spec.md) - 詳細技術規格
- [Architecture](ARCHITECTURE.md) - 系統架構
- [Constitution](CONSTITUTION.md) - 專案原則

## 📄 License

[Apache License 2.0](LICENSE)
