# Asset-Aware MCP

> 🏗️ **Asset-Aware ETL for AI Agents** - Precise PDF decomposition into structured assets (Tables, Figures, Sections)

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/u9401066.asset-aware-mcp)](https://marketplace.visualstudio.com/items?itemName=u9401066.asset-aware-mcp)
[![PyPI](https://img.shields.io/pypi/v/asset-aware-mcp)](https://pypi.org/project/asset-aware-mcp/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

## 🆕 What's New in v0.2.10

- **Modular Architecture**: Server refactored from 2122 → 31 lines (thin entry point)
- **34 MCP Tools** across 5 modules (Document, Section, Job, Knowledge, Table)
- **12 MCP Resources** across 2 modules (Document, Table)
- **Bug Fixes**: `use_marker` async mode, `list_documents` filtering, image overlap detection

## 🌟 Core Concept: Asset-Aware ETL

This extension provides a sophisticated **ETL (Extract, Transform, Load) Pipeline** for AI Agents. Instead of feeding raw text to an LLM, it decomposes documents into a structured "Map" (Manifest), allowing Agents to precisely retrieve what they need.

### The Workflow:
1.  **📥 Ingest (ETL)**: Agent provides a local PDF path.
2.  **⚙️ Process**: MCP Server reads the file using **PyMuPDF**, separating **Text**, **Tables**, and **Figures** (with page numbers).
3.  **🗺️ Manifest**: Generates a structured JSON "Map" of all assets.
4.  **📤 Fetch**: Agent "looks at the map" and fetches specific objects (e.g., "Table 1" or "Figure 2") as clean Markdown or Base64 images.

## ✨ Features

- **📄 Dual-Engine PDF ETL**: 
  - **PyMuPDF** (default) - Fast extraction (~50MB dependency)
  - **Marker** (optional, `use_marker=True`) - High-precision with `blocks.json` containing bbox coordinates
- **🧭 Section Navigation**: Dynamic hierarchy section tree with 4 tools for browsing, searching, and block extraction
- **🔄 Async Jobs**: Track progress for large document batches with Job IDs.
- **🗺️ Document Manifest**: A structured index that lets Agents "see" document structure before reading.
- **🖼️ Visual Assets**: Extract figures as Base64 images for Vision-capable Agents.
- **📊 A2T (Anything to Table)**: 19 tools for creating, editing, and exporting professional Excel tables
- **🧠 Knowledge Graph**: Cross-document insights powered by LightRAG.
- **🔌 MCP Native**: Seamless integration with VS Code Copilot Chat and Claude.
- **🏠 Local-First**: Optimized for Ollama (local LLM) but supports OpenAI.

## 🚀 Quick Start

### 1. Install Prerequisites

```bash
# Install Ollama (for local LLM)
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5:7b
ollama pull nomic-embed-text
```

### 2. Install Extension

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Asset-Aware MCP"
4. Click Install

### 3. Run Setup Wizard

1. Open Command Palette (Ctrl+Shift+P)
2. Run `Asset-Aware MCP: Setup Wizard`
3. Follow the prompts to configure your `.env` file.

## 📖 Usage (Agent Flow)

### 1. Ingest a Document (ETL)
In Copilot Chat, tell the agent to process a file:
`@workspace Use ingest_documents to process ./papers/study_01.pdf`

### 2. Check Progress
For large files, check the job status:
`@workspace get_job_status("job_id_here")`

### 3. Inspect the Map
The agent will first look at the manifest to see what's inside:
`@workspace What tables are available in doc_study_01?`

### 4. Fetch Specific Assets
The agent retrieves exactly what it needs:
`@workspace Fetch Table 1 from doc_study_01`
`@workspace Show me Figure 2.1 (the study flow diagram)`

## ⚙️ Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `assetAwareMcp.llmBackend` | `ollama` | LLM backend (ollama/openai) |
| `assetAwareMcp.ollamaHost` | `http://localhost:11434` | Ollama URL |
| `assetAwareMcp.dataDir` | `./data` | Storage for processed assets |

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `Setup Wizard` | Initial configuration & dependency check |
| `Open Settings Panel` | Visual editor for `.env` settings |
| `Check Ollama Connection` | Test if local LLM is accessible |
| `Check System Dependencies` | Verify `uv`, `python`, and `pip` are installed |
| `Refresh Status` | Update the Status and Documents tree views |

## 🛠️ Troubleshooting & Debugging

If the extension fails to start or the MCP server doesn't appear:

1.  **Check VS Code Version**: Ensure you are using VS Code **1.96.0** or newer.
2.  **Check Dependencies**: Run `Asset-Aware MCP: Check System Dependencies` from the command palette.
3.  **Inspect Logs**:
    *   Open **Output** panel (`Ctrl+Shift+U`).
    *   Select **Asset-Aware MCP** from the dropdown to see extension logs.
    *   Select **Asset-Aware MCP Dependencies** to see dependency check results.
4.  **Development Mode**:
    *   Clone the repo.
    *   Open `vscode-extension` folder.
    *   Run `npm install`.
    *   Press `F5` to launch the **Extension Development Host**.

## 📚 MCP Tools (34 total)

### Document ETL (5)
| Tool | Description |
|------|-------------|
| `ingest_documents` | Process PDF files into structured assets |
| `list_documents` | List all ingested documents |
| `inspect_document_manifest` | View document structure (Tables/Figures/Sections) |
| `fetch_document_asset` | Get specific Table/Figure/Section content |
| `parse_pdf_structure` | Parse PDF structure without full ingestion |

### Section Navigation (4)
| Tool | Description |
|------|-------------|
| `list_section_tree` | Browse document section hierarchy |
| `get_section_detail` | Get section metadata and stats |
| `get_section_blocks` | Extract blocks from a section |
| `search_sections` | Search sections by keyword |

### Job Management (4)
| Tool | Description |
|------|-------------|
| `get_job_status` | Track progress of ingestion jobs |
| `list_jobs` | List all jobs |
| `cancel_job` | Cancel a running job |
| `search_source_location` | Find source location in documents |

### Knowledge Graph (2)
| Tool | Description |
|------|-------------|
| `consult_knowledge_graph` | Cross-document RAG queries |
| `export_knowledge_graph` | Export knowledge graph data |

### A2T - Anything to Table (19)
| Tool | Description |
|------|-------------|
| `plan_table_schema` | AI-driven schema planning |
| `create_table_draft` | Start a new draft |
| `add_rows_to_draft` | Batch add rows to draft |
| `commit_draft_to_table` | Finalize draft to table |
| `resume_draft` / `resume_table` | Resume work with minimal context |
| `create_table` / `add_rows` / `update_row` / `delete_row` | Direct CRUD |
| `render_table` | Export to Excel with formatting |

## 🔗 Links

- [GitHub Repository](https://github.com/u9401066/asset-aware-mcp)
- [PyPI Package](https://pypi.org/project/asset-aware-mcp/)
- [Technical Specification](https://github.com/u9401066/asset-aware-mcp/blob/main/docs/spec.md)

## 📝 License

Apache-2.0
