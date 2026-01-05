# asset-aware-mcp

> 🏥 Medical RAG with Asset-Aware MCP - Precise PDF asset retrieval (tables, figures, sections) and Knowledge Graph for AI Agents.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [繁體中文](README.zh-TW.md)

## 🎯 Why Asset-Aware MCP?

**AI cannot directly read image files on your computer.** This is a common misconception.

| Method | Can AI analyze image content? | Description |
|------|:-------------------:|------|
| ❌ Provide PNG path | No | AI cannot access the local file system |
| ✅ **Asset-Aware MCP** | **Yes** | Retrieves Base64 via MCP, allowing AI vision to understand directly |

### Real-world Effect

```
# After retrieving the image via MCP, the AI can analyze it directly:

User: What is this figure about?

AI: This is the architecture diagram for Scaled Dot-Product Attention:
    1. Inputs: Q (Query), K (Key), V (Value)
    2. MatMul of Q and K
    3. Scale (1/√dₖ)
    4. Optional Mask (for decoder)
    5. SoftMax normalization
    6. Final MatMul with V to get the output
```

**This is the value of Asset-Aware MCP** - enabling AI Agents to truly "see" and understand charts and tables in your PDF literature.

---

## ✨ Features

- 📄 **Asset-Aware ETL** - PDF → Markdown, using **PyMuPDF** to automatically identify tables, sections, and images.
- 🔄 **Async Job Pipeline** - Supports asynchronous task processing and progress tracking for large documents.
- 🗺️ **Document Manifest** - Provides a structured "map" of the document for precise data access by Agents.
- 🧠 **LightRAG Integration** - Knowledge Graph + Vector Index, supporting cross-document comparison and reasoning.
- 📊 **A2T (Anything to Table)** - Automatically orchestrate information extracted by Agents into professional Excel tables, supporting CRUD, **Drafting**, and **Token-efficient resumption**.
- �️ **VS Code Management Extension** - Graphical interface for monitoring server status, ingested documents, and **A2T tables/drafts** with one-click Excel export.
- �🔌 **MCP Server** - Exposes tools and resources to Copilot/Claude via FastMCP.
- 🏥 **Medical Research Focus** - Optimized for medical literature, supporting Base64 image transmission for Vision AI analysis.

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

- [Technical Spec](docs/spec.md) - Detailed technical specification
- [Architecture](ARCHITECTURE.md) - System architecture
- [Constitution](CONSTITUTION.md) - Project principles

## 📄 License

[Apache License 2.0](LICENSE)
