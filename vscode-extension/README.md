# Asset-Aware MCP

> 🏗️ **Asset-Aware ETL for AI Agents** - Precise PDF decomposition into structured assets (Tables, Figures, Sections)

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/u9401066.asset-aware-mcp)](https://marketplace.visualstudio.com/items?itemName=u9401066.asset-aware-mcp)
[![PyPI](https://img.shields.io/pypi/v/asset-aware-mcp)](https://pypi.org/project/asset-aware-mcp/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

![Asset-Aware MCP marketplace banner](resources/banner.png)

## 🆕 What's New in v0.6.9

- **DFM messy-document hardening**: literal Markdown symbols, marker-looking comments, multi-line list items, hyperlink runs, and literal table pipes now survive round-trip more reliably
- **Fail-closed table safety**: row/column structural table edits are rejected until full XML row/column mutation is implemented, preventing false-success truncation
- **Safer DFM save flow**: MCP fenced JSON/English labels parse correctly, source DOCX disk conflicts are detected before overwrite, and save failures include diagnostics
- **48 tools** across 7 modules

## 🧪 Current Main Branch

- **Structured LightRAG MCP Output**: `consult_knowledge_graph` now supports `structured`, `data`, and `text` response modes for citation-aware agent workflows
- **LightRAG Deletion Sync**: deleting an ingested PDF now also attempts to remove its LightRAG document index
- **Extension Env Alignment**: generated `.env` now writes `LIGHTRAG_WORKING_DIR` and still falls back from legacy `LIGHTRAG_DIR`

### v0.6.1

- **OpenDocument Support**: Added `.odt` / `.ods` ingest via LibreOffice auto-conversion and a new `convert_docx_to_odt` tool
- **3-Cycle Fidelity Testing**: Added repeatable round-trip validation script and formal format-conversion report

### v0.6.0

- **Unified Segmentation Export**: New `segmentation.json` contract combines manifest, blocks, reading order, and persisted markdown line ranges
- **Layout Overlay Debugging**: Render bbox / type / reading-order overlays directly from `original.pdf`
- **On-Demand OCR Preprocessing**: Clean scanned PDFs before ETL with `ocr_pdf_document` or OCR-enabled ingest
- **Line-Aware Asset Fetching**: `fetch_document_asset` now returns line ranges, section context, and source block IDs directly
- **46 tools** across 7 modules

### v0.5.2

- **Stable Python Runtime**: Extension launch now prefers Python 3.11 to avoid macOS native build failures on newer interpreters
- **Optional Marker Backend**: Marker and torch are no longer installed by default; enable them only when you need structured parsing
- **Safer Torch Resolution**: Added configurable `torchBackend`, defaulting to `cpu` to reduce wheel/CUDA mismatch issues

### v0.5.1

- **Markdown Export**: New `export_markdown` tool — export Markdown text to `.docx`, `.pdf`, or `.doc`
- **Multiline Cell Protection**: Table cells with `\n` are now safely escaped as `<br>` in DFM pipe-tables, preventing silent data loss
- **Post-Write Validation**: `docx_table_from_context` validates non-empty cell counts after write — rejects if >50% cells lost
- **Save Fail-Safe**: `save_docx` rejects output if content shrinks >50% (use `force=true` to override)
- **Content Volume Metrics**: `docx_validate_roundtrip` now reports `total_chars`, `table_nonempty_cells`, `table_cell_chars`
- **Ollama API Fix**: Compatible with Ollama v0.5+ (`/api/embed`) with legacy fallback

### v0.4.2

- **Release Validation Parity**: `scripts/release.sh` now checks the full repository with the same Ruff scope as GitHub Actions, preventing tag-only CI surprises

### v0.4.1

- **Release Workflow Hardening**: Fixed test lint issues that only surfaced under GitHub Actions `ruff check .`, ensuring the tagged release passes CI cleanly

### v0.4.0

- **Document CRUD + Conversion**: Added `delete_document`, `delete_docx`, `list_docx_documents`, `convert_docx_to_pdf`, `convert_docx_to_doc`, and `convert_pdf_to_docx`
- **Strict Round-Trip Validation**: `docx_validate_roundtrip(..., strict=true)` now supports fail-closed validation for structure/text/format/table/media/style regressions
- **Write-Back Safety Guard**: `save_docx` now aborts if unedited blocks mutate during write-back
- **`.doc` Auto-Conversion**: `ingest_docx` now accepts legacy `.doc` files — auto-converts via LibreOffice headless
- **Markdown Escaping Fix**: `_escape_md()` / `_unescape_md()` prevents text content (e.g. `※**`) from being misinterpreted as bold/italic markers
- **Run Merging**: Adjacent runs with identical formatting are merged before Markdown generation, eliminating `**A****B**` artifacts
- **Production Hardening**: Dockerfile, PDF magic byte validation, concurrent job limits, structured logging
- **43 tools** across 7 modules
- **Proposal real-file verification**: battle-tested on a real Proposal DOCX for DOCX→DFM→DOCX, DOCX→PDF, and DOCX→DOC

### v0.3.3
- **Production Hardening**: Dockerfile, PDF magic byte validation, concurrent job limits, structured logging
- **`.doc` Auto-Conversion**: `ingest_docx` now accepts legacy `.doc` files — auto-converts via LibreOffice headless
- **Markdown Escaping Fix**: `_escape_md()` / `_unescape_md()` prevents text content (e.g. `※**`) from being misinterpreted as bold/italic markers
- **Run Merging**: Adjacent runs with identical formatting are merged before Markdown generation, eliminating `**A****B**` artifacts

### v0.3.2
- **DFM Integrity Checker**: Automatic validation + auto-repair at every pipeline stage (ingest/save)
- **File-Level Comparison**: SHA-256 hash + file size + ZIP entry diff for binary-level round-trip verification
- **CI/CD Migrated to uv**: All pip/setup-python references removed across workflows

### v0.3.1
- **Split Format**: `content.md` + `format.yaml` — 78% less clutter for human editing
- **DFM CLI**: Interactive menu for ingest/edit/save/validate

### v0.3.0
- **Docx Editing (DFM)**: 8 new tools for editing .docx files as Markdown with full round-trip fidelity
- **DocxValidator**: 6-dimension comparison with weighted scoring
- **DfmTableBridge**: Seamless Docx table ↔ A2T table conversion
- **Total at release time**: 36 tools in 7 modules

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
- **🧩 Unified Segmentation**: Export normalized `segmentation.json` with reading order and markdown line ranges
- **🖼️ Layout Overlay**: Visual bbox/type/reading-order inspection from the original PDF
- **🔤 OCR Preprocessing**: Optional scanned-PDF cleanup before ETL
- **🧭 Section Navigation**: Dynamic hierarchy section tree with 5 tools for browsing, searching, content reading, and block extraction
- **🔄 Async Jobs**: Track progress for large document batches with Job IDs.
- **🗺️ Document Manifest**: A structured index that lets Agents "see" document structure before reading.
- **🖼️ Visual Assets**: Extract figures as Base64 images for Vision-capable Agents.
- **📊 A2T (Anything to Table)**: 7 operation-based tools for creating tables from any source with citations, audit trail, and Excel export
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
| `.env: LIGHTRAG_WORKING_DIR` | `./data/lightrag_db` | LightRAG working directory written by the setup wizard / settings panel |
| `assetAwareMcp.enableMarkerBackend` | `false` | Install optional Marker backend for structured parsing; pulls torch-related ML dependencies |
| `assetAwareMcp.torchBackend` | `cpu` | Torch backend used when Marker backend is enabled; `cpu` is the safest default |

Runtime note:
The extension prefers a managed Python 3.11 runtime when launching the MCP server via `uv`/`uvx`. This avoids package builds on machines without native toolchains, especially macOS systems missing Xcode Command Line Tools, while keeping the project itself compatible with newer Python versions.

Marker note:
The extension does not install Marker or torch by default. If you need `use_marker=True` workflows, enable `assetAwareMcp.enableMarkerBackend`. Keeping `assetAwareMcp.torchBackend=cpu` avoids most cross-platform wheel and CUDA mismatch issues.

Installation scope & storage:
- The VSIX installs as a user/global extension (standard VS Code behavior), so you do not need a separate install per workspace.
- The MCP server is launched via `uvx asset-aware-mcp` and reused from your user-level uv cache; upgrades reuse the same cache.
- Runtime data stays in the workspace: `.env` and `assetAwareMcp.dataDir` default to `./data` beside your repo, keeping ingested assets scoped per project.

## 🔧 Commands

| Command | Description |
|---------|-------------|
| `Setup Wizard` | Initial configuration & dependency check |
| `Open Settings Panel` | Visual editor for `.env` settings |
| `Check Ollama Connection` | Test if local LLM is accessible |
| `Check System Dependencies` | Verify `uv` is available and the MCP launcher can start |
| `Refresh Status` | Update the Status and Documents tree views |

## 🛠️ Troubleshooting & Debugging

If the extension fails to start or the MCP server doesn't appear:

1.  **Check VS Code Version**: Ensure you are using VS Code **1.96.0** or newer.
2.  **Check Dependencies**: Run `Asset-Aware MCP: Check System Dependencies` from the command palette.
  The dependency checker will also show the preferred Python runtime used by the MCP launcher.
  If Marker backend is enabled, it will also show the selected torch backend.
3.  **Inspect Logs**:
    *   Open **Output** panel (`Ctrl+Shift+U`).
    *   Select **Asset-Aware MCP** from the dropdown to see extension logs.
    *   Select **Asset-Aware MCP Dependencies** to see dependency check results.
4.  **Development Mode**:
    *   Clone the repo.
    *   Open `vscode-extension` folder.
    *   Run `npm install`.
    *   Press `F5` to launch the **Extension Development Host**.

## 📚 MCP Tools (47 total)

### Document ETL (11)
| Tool | Description |
|------|-------------|
| `ingest_documents` | Process PDF files into structured assets |
| `list_documents` | List all ingested documents |
| `delete_document` | Delete an ingested PDF and its local artifacts |
| `convert_pdf_to_docx` | Reconstruct a readable DOCX from extracted PDF content |
| `inspect_document_manifest` | View document structure (Tables/Figures/Sections) |
| `fetch_document_asset` | Get specific Table/Figure/Section content |
| `parse_pdf_structure` | Parse PDF structure without full ingestion |
| `search_source_location` | Search exact source locations with page numbers and bbox |
| `export_document_segmentation` | Export normalized segmentation with reading order and line spans |
| `visualize_document_layout` | Render page overlay images for layout debugging |
| `ocr_pdf_document` | Run OCR preprocessing and output a cleaned PDF |

### Section Navigation (5)
| Tool | Description |
|------|-------------|
| `list_section_tree` | Browse document section hierarchy |
| `get_section_detail` | Get section metadata and stats |
| `get_section_blocks` | Extract blocks from a section |
| `search_sections` | Search sections by keyword |
| `get_section_content` | Read section content via asset service |

### Job Management (3)
| Tool | Description |
|------|-------------|
| `get_job_status` | Track progress of ingestion jobs |
| `list_jobs` | List all jobs |
| `cancel_job` | Cancel a running job |

### Knowledge Graph (2)
| Tool | Description |
|------|-------------|
| `consult_knowledge_graph` | Cross-document RAG queries with `structured`, `data`, and `text` response modes |
| `export_knowledge_graph` | Export knowledge graph data |

### Docx Editing — DFM (14)
| Tool | Description |
|------|-------------|
| `ingest_docx` | Import .docx and decompose into DFM blocks |
| `get_docx_content` | Read DFM content of specific blocks |
| `save_docx` | Write DFM edits back to .docx |
| `list_docx_blocks` | List document block structure |
| `list_docx_documents` | List all ingested DOCX/DFM documents |
| `delete_docx` | Delete an ingested DOCX/DFM document and its local artifacts |
| `convert_docx_to_pdf` | Export the current DOCX/DFM state to PDF in fidelity mode |
| `convert_docx_to_doc` | Export the current DOCX/DFM state to DOC in fidelity mode |
| `docx_validate_roundtrip` | 6-dimension round-trip fidelity + file-level SHA-256/ZIP comparison with optional strict fail-closed mode |
| `docx_table_to_context` | Bridge: Docx table → A2T context |
| `docx_table_from_context` | Bridge: A2T table → Docx table |
| `docx_chart_data` | Extract chart data from Docx |
| `export_markdown` | Export Markdown to .docx/.pdf/.doc |
| `convert_docx_to_odt` | Export the current DOCX/DFM state to ODT |

### A2T — Anything to Table (7 operation-based)
| Tool | Operations | Description |
|------|-----------|-------------|
| `plan_table` | `schema` / `templates` / `from_template` | Schema planning & template management |
| `table_manage` | `create` / `delete` / `list` / `preview` / `resume` / `render` / `add_column` / `remove_column` / `rename_column` | Table lifecycle + schema evolution |
| `table_data` | `add_rows` / `get_row` / `update_row` / `delete_row` / `get_cell` / `update_cell` / `clear_cell` | Row & cell CRUD |
| `table_cite` | `add` / `get` / `remove` / `cell_history` | Citation management (AssetRef, 7 source types) |
| `table_history` | `changes` / `tokens` | Audit trail & token estimation |
| `table_draft` | `create` / `update` / `add_rows` / `resume` / `commit` / `list` / `delete` | Draft workflow with persistence |
| `discover_sources` | — | Cross-document source discovery |

### ETL Profile (5)
| Tool | Description |
|------|-------------|
| `list_etl_profiles` | List available profiles |
| `get_etl_profile` | Get profile configuration |
| `get_current_etl_profile` | Show active profile |
| `set_etl_profile` | Switch profile |
| `load_etl_profile_from_json` | Load custom profile |

## 🔗 Links

- [GitHub Repository](https://github.com/u9401066/asset-aware-mcp)
- [PyPI Package](https://pypi.org/project/asset-aware-mcp/)
- [Technical Specification](https://github.com/u9401066/asset-aware-mcp/blob/main/docs/spec.md)

## 📝 License

Apache-2.0
