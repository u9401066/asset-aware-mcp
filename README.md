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

- 📄 **Asset-Aware ETL** - PDF → Markdown with **dual-engine** PDF parsing:
  - **PyMuPDF** (default) - Fast extraction (~50MB)
  - **Marker** (optional, `use_marker=True`) - High-precision structured parsing with `blocks.json` (bbox/coordinates)
- 🧭 **Section Navigation** - Dynamic hierarchy section tree with 5 tools: browse, search, detail, content reading, and block extraction for any depth of headings.
- 🔄 **Async Job Pipeline** - Supports asynchronous task processing and progress tracking for large documents.
- 🗺️ **Document Manifest** - Provides a structured "map" of the document for precise data access by Agents.
- 🧠 **LightRAG Integration** - Knowledge Graph + Vector Index, supporting cross-document comparison and reasoning.
- � **Docx Editing (DFM)** - Edit .docx files in Markdown via **Docx-Flavored Markdown** format. 8 tools: ingest, edit, save, validate round-trip fidelity (6-dimension scoring), and bridge to A2T tables.
- �📊 **A2T (Anything to Table)** - 7 operation-based tools for building professional tables from **any source** (PDF assets, Knowledge Graph, URLs, user input). Features: **Citations** (AssetRef), **Audit Trail**, **Schema Evolution**, **Templates**, **Drafting**, and **Token-efficient resumption**.
- 🖥️ **VS Code Management Extension** - Graphical interface for monitoring server status, ingested documents, and **A2T tables/drafts** with one-click Excel export.
- 🔌 **MCP Server** - Exposes tools and resources to Copilot/Claude via FastMCP.
- 🏥 **Medical Research Focus** - Optimized for medical literature, supporting Base64 image transmission for Vision AI analysis.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP Protocol (Tools & Resources)
┌─────────────────────▼───────────────────────────────────┐
│            MCP Server (Modular Presentation)            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ tools/: 36 tools in 7 modules                   │   │
│  │   document (6) │ docx (8)   │ section (5)       │   │
│  │   job (3) │ knowledge (2) │ table (7) │ profile (5) │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ resources/: 12 resources in 2 modules           │   │
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
│  ├── docx_{id}/       # Docx IR + DFM + Assets          │
│  ├── tables/          # A2T Tables (JSON/MD/XLSX)       │
│  │   └── drafts/      # Table Drafts (Persistence)      │
│  └── lightrag_db/     # Knowledge Graph                 │
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

### Document & Asset Tools

| Tool | Purpose |
|------|---------|
| `ingest_documents` | Process PDF files with optional Marker backend (`use_marker=True` for blocks.json) |
| `fetch_document_asset` | Precisely retrieve tables (MD) / figures (B64) / sections |
| `consult_knowledge_graph` | Knowledge graph query, cross-document comparison |

### Section Navigation Tools (Dynamic Hierarchy)

| Tool | Purpose |
|------|---------|
| `list_section_tree` | Display complete section hierarchy tree (supports any depth) |
| `get_section_detail` | Get detailed info for a specific section |
| `get_section_blocks` | Extract all blocks from a section with page + bbox |
| `search_sections` | Search section titles |
| `get_section_content` | Read section content via asset service |

### Docx Editing Tools (DFM — Docx-Flavored Markdown)

> Edit .docx files as Markdown. Preserves formatting, tables, media on round-trip.

| Tool | Purpose |
|------|---------|
| `ingest_docx` | Import .docx and decompose into DFM blocks |
| `get_docx_content` | Read DFM content of specific blocks |
| `save_docx` | Write DFM edits back to .docx |
| `list_docx_blocks` | List document block structure |
| `docx_validate_roundtrip` | 6-dimension round-trip fidelity validation |
| `docx_table_to_context` | Bridge: Docx table → A2T context |
| `docx_table_from_context` | Bridge: A2T table → Docx table |
| `docx_chart_data` | Extract chart data from Docx |

### A2T (Anything to Table) Tools — 7 Operation-Based Tools

> Agent-friendly design: each tool handles multiple operations via `operation` parameter.
> Tables accept **any source** — PDF assets, KG entities, external URLs, or user input.

| Tool | Operations | Purpose |
|------|-----------|----------|
| `plan_table` | `schema` / `templates` / `from_template` | Schema planning, browse 4 built-in templates, create from template |
| `table_manage` | `create` / `delete` / `list` / `preview` / `resume` / `render` / `add_column` / `remove_column` / `rename_column` | Table lifecycle + Schema evolution |
| `table_data` | `add_rows` / `get_row` / `update_row` / `delete_row` / `get_cell` / `update_cell` / `clear_cell` | Row & cell CRUD |
| `table_cite` | `add` / `get` / `remove` / `cell_history` | Citation management with AssetRef (7 source types) |
| `table_history` | `changes` / `tokens` | Audit trail & token estimation |
| `table_draft` | `create` / `update` / `add_rows` / `resume` / `commit` / `list` / `delete` | Draft workflow with persistence |
| `discover_sources` | — | Cross-document source discovery (sections, tables, figures, KG) |

### ETL Profile Tools

Different journals/formats need different extraction settings. Use these tools to switch profiles.

| Tool | Purpose |
|------|---------|
| `list_etl_profiles` | List all available profiles (default, arxiv, nature, ieee, elsevier) |
| `get_etl_profile` | Get detailed configuration of a specific profile |
| `get_current_etl_profile` | Show currently active profile |
| `set_etl_profile` | Switch profile for subsequent document ingestion |
| `load_etl_profile_from_json` | Load custom profile from JSON file |

## 🔧 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.10+ |
| ETL | **PyMuPDF** (fitz) + **Marker** (optional, high-precision) |
| RAG | LightRAG (lightrag-hku) |
| MCP | FastMCP |
| Storage | Local filesystem (JSON/Markdown/PNG) |

## 📋 Documentation

- [Technical Spec](docs/spec.md) - Detailed technical specification
- [Architecture](ARCHITECTURE.md) - System architecture
- [Constitution](CONSTITUTION.md) - Project principles

## 📄 License

[Apache License 2.0](LICENSE)
