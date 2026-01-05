# asset-aware-mcp

> 🏥 Medical RAG with Asset-Aware MCP - 讓 AI Agent 精準存取 PDF 文獻中的表格、章節與知識圖譜

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [繁體中文](README.zh-TW.md)

## ✨ Features

- 📄 **Asset-Aware ETL** - PDF → Markdown, using **PyMuPDF** to automatically identify tables, sections, and images
- 🔄 **Async Job Pipeline** - Supports asynchronous task processing, tracking progress for large documents
- 🗺️ **Document Manifest** - Structured list, allowing Agents to "see the map" before precisely accessing data
- 🧠 **LightRAG Integration** - Knowledge Graph + Vector Index, supporting cross-document comparison and reasoning
- 🔌 **MCP Server** - Exposes tools and resources to Copilot/Claude via FastMCP
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
│  │          consult_knowledge_graph                │   │
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
│  ├── doc_{id}/                                          │
│  │   ├── full.md          # Markdown Content            │
│  │   ├── manifest.json    # Asset Map                   │
│  │   └── images/          # Extracted Figures           │
│  └── lightrag/            # Knowledge Graph             │
└─────────────────────────────────────────────────────────┘
```

## 📁 Project Structure (DDD)

```
asset-aware-mcp/
├── src/
│   ├── domain/              # 🔵 Domain: Entities, Value Objects, Interfaces
│   ├── application/         # 🟢 Application: Doc Service, Job Service, Asset Service
│   ├── infrastructure/      # 🟠 Infrastructure: PyMuPDF, LightRAG, File Storage
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
| `ingest_documents` | 匯入 PDF，觸發 ETL pipeline (支援 async) |
| `get_job_status` | 檢查 ETL 任務進度 |
| `list_documents` | 列出所有已處理的文件 |
| `inspect_document_manifest` | 查看文件結構地圖 (表格/圖片/章節) |
| `fetch_document_asset` | 精準取得表格 (MD) / 圖片 (B64) / 章節 |
| `consult_knowledge_graph` | 知識圖譜查詢，跨文獻比較 |

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
