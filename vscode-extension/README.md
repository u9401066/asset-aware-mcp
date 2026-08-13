# Asset-Aware MCP

> 🏗️ **Asset-Aware ETL for AI Agents** - Precise PDF decomposition into structured assets (Tables, Figures, Sections)

[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/u9401066.asset-aware-mcp)](https://marketplace.visualstudio.com/items?itemName=u9401066.asset-aware-mcp)
[![PyPI](https://img.shields.io/pypi/v/asset-aware-mcp)](https://pypi.org/project/asset-aware-mcp/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

![Asset-Aware MCP marketplace banner](https://raw.githubusercontent.com/u9401066/asset-aware-mcp/v1.0.0/resources/banner.png)

## What's New in v1.0.0

- **MCP SDK 2 runtime**: the server now requires the official Python SDK `>=2,<3` and uses `MCPServer`; SDK v1 is intentionally unsupported. Runtime context is injected by the SDK and no longer leaks into public tool schemas.
- **PDF preflight and safe routing**: `document(op="preflight", pdf_path="...")` classifies native, sparse, image, scanned, or hybrid PDFs per page in an isolated subprocess and recommends native, OCR, or Docling extraction before ingest.
- **Reusable agent asset bundles**: `document(op="export_assets", doc_id="...")` writes deterministic manifests, JSONL records, media, stable hashes/locators/citations, and a portable Foam wiki without overwriting unrelated output.
- **Security and release refresh**: Python and extension locks were upgraded, dependency audits are release gates, and automated uv/npm/Actions updates are configured. MinerU and Marker remain adapter-only holds until their upstream caps admit patched dependencies.
- **Balanced surface retained**: mixed-format batch ingestion, engine provenance, structural retrieval, DOCX/DFM and citation workflows remain available through 30 public tools and 13 resources.

## What's New in v0.8.0

- **Historical v0.8 engine work**: this release introduced the MinerU adapter, but MinerU is now on a dependency security hold alongside Marker. The maintained install paths are `pymupdf` (default), `pymupdf4llm`, and `docling`.
- **Zero-configuration Docling install**: a cross-platform installer (`scripts/setup_docling.py` / `.sh` / `.ps1`) provisions an isolated `.venv-docling` interpreter and bridges it via subprocess, so the main runtime never needs a direct, version-sensitive Docling install.
- **Engine-agnostic structured parsing**: Marker, Docling, and MinerU now share a `StructuredPDFExtractor` protocol and emit Marker-compatible results, reusing the existing ingestion pipeline with no service-layer changes.

## What's New in v0.7.0

- **Balanced MCP tool surface**: default runtime now exposes 30 agent-friendly public tools, with compact 17-tool and legacy 63-tool compatibility modes available.
- **Structural pointer workflows**: `document(op="pointer_index")`, `document(op="structural_retrieve")`, and `document(op="compare")` add section-level retrieval and comparison with locator/hash provenance without increasing the public tool count.
- **A2T large-table hardening**: stable row IDs, row search/filter/paging, citation coverage, artifact-only Markdown/HTML render, and actionable skipped-large-table UX make big tables safer for Cline/Codex/Copilot.
- **Accessibility readiness**: PDF audit/readiness now includes `accessibility_report.json` alongside safety, native structure, and segmentation coverage artifacts.
- **Runtime prepare portability**: managed runtime preparation uses version-pinned `uv tool run`, handles Windows paths with spaces, and falls back across Python 3.11 / 3.10 for older machines.
- **Better diagnostics**: dependency checks now report preferred Python, platform tags, and native import status for Pillow, lxml, pydantic-core, and the MCP SDK.
- **A2T table hardening**: row/cell validation, citation cleanup, duplicate-column protection, draft timestamp loading, and table-history shortcut ergonomics are tightened.
- **PDF audit artifacts**: the existing `document` facade can write AI safety, native structure, segmentation coverage, accessibility readiness, and structural pointer artifacts for ingested PDFs without adding public tools.
- **Docs refresh**: README, GitHub Pages, wiki source, VSIX reference, and bundled assistant assets are aligned with the balanced surface.
- **30 public tools** across 7 modules, plus 13 MCP resources

## 🧪 Current Main Branch

- **Structured LightRAG MCP Output**: `consult_knowledge_graph` supports `structured`, `data`, and `text` response modes, with optional verified evidence bundles
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
- **Historical Marker option (now held)**: the old setting remains for compatibility, but current releases never install or enable Marker; use PyMuPDF4LLM or Docling for structured parsing
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

- **📄 PDF ETL**:
  - **PyMuPDF** (default) - Fast extraction (~50MB dependency), no models required
  - **PyMuPDF4LLM** / **Docling** - Secure optional higher-fidelity engines selected via `ETL_ENGINE`; Docling ships a cross-platform installer for an isolated interpreter
  - **MinerU** / **Marker** - Adapters remain for upstream evaluation, but packaged extras are empty security holds until patched dependency chains resolve
- **🩺 PDF Preflight**: Per-page OCR reasons, source hash, resource limits, and a native/OCR/Docling route before ingest
- **📦 Agent Asset Export**: Deterministic text/table/figure records, citation-ready provenance, and Foam notes from one document facade operation
- **🧩 Unified Segmentation**: Export normalized `segmentation.json` with reading order and markdown line ranges
- **🖼️ Layout Overlay**: Visual bbox/type/reading-order inspection from the original PDF
- **🔤 OCR Preprocessing**: Optional scanned-PDF cleanup before ETL
- **🧭 Section Navigation**: Dynamic hierarchy section tree with 5 tools for browsing, searching, content reading, and block extraction
- **🔄 Async Jobs**: Track progress for large document batches, OCR, configured structured parsing, and conversions with Job IDs.
- **🗺️ Document Manifest**: A structured index that lets Agents "see" document structure before reading.
- **🖼️ Visual Assets**: Extract figures as Base64 images for Vision-capable Agents.
- **📊 A2T (Anything to Table)**: 7 operation-based tools for creating tables from any source with stable row IDs, search/filter/paging, citation coverage, audit trail, artifact-only render, and Excel export
- **🧠 Knowledge Graph**: Cross-document insights powered by LightRAG, with optional verified evidence bundles.
- **🧾 Artifact / Citation Viewer**: Open generated artifacts and EvidenceSpan summaries from the Documents tree.
- **🔌 MCP Native**: Seamless integration with VS Code Copilot Chat and Claude.
- **🏠 Local-First**: Optimized for Ollama (local LLM) but supports OpenAI.

## 🚀 Quick Start

### 1. Install Prerequisites

```bash
# Install Ollama (for local LLM)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the CPU-friendly default model
ollama pull granite4.1:3b

# GPU installs can opt into the larger default
ollama pull granite4.1:8b

# Optional: only needed when LightRAG/KG is enabled
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

### 4. (Optional) Install LightRAG Backend

Since v0.6.34 the LightRAG / Knowledge Graph dependency stack ships as an
**optional extra** so default installs stay slim. Enable it before turning
`assetAwareMcp.enableLightRag` on:

1. Command Palette → `Asset-Aware MCP: Install LightRAG Backend`
2. Confirm the modal. The extension auto-detects whether you are running the
   published wheel (`uv tool install --upgrade 'asset-aware-mcp[lightrag]'`) or
   a local source checkout (`uv sync --extra lightrag`) and emits the matching
   install command in a terminal.

`Asset-Aware MCP: Marker Backend Status (Security Hold)` keeps the historical
command ID for compatibility but only shows the hold status; it never installs
or enables Marker (`marker-pdf` pins `Pillow<11`).

## 📖 Usage (Agent Flow)

### 1. Ingest a Document (ETL)
In Copilot Chat, tell the agent to process a file:
`@workspace Use document(op="auto", file_paths=["./papers/study_01.pdf"])`

### 2. Check Progress
For large files, check the job status:
`@workspace job(op="get", job_id="job_id_here")`

### 3. Inspect the Map
The agent can ask for AI-ready state and the next facade operation:
`@workspace document(op="prepare_ai", doc_id="doc_study_01")`

### 4. Fetch Specific Assets
The agent retrieves exactly what it needs:
`@workspace Fetch Table 1 from doc_study_01`
`@workspace Show me Figure 2.1 (the study flow diagram)`

## ⚙️ Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `assetAwareMcp.llmBackend` | `ollama` | LLM backend (`ollama`, `openai`, or `openrouter`) |
| `assetAwareMcp.ollamaHost` | `http://localhost:11434` | Ollama URL |
| `assetAwareMcp.ollamaModel` | `granite4.1:3b` | CPU-friendly local RAG/text-generation default; set `ASSET_AWARE_HAS_GPU=true` or choose `granite4.1:8b` for GPU installs |
| `assetAwareMcp.openrouterApiKey` | empty | OpenRouter API key for the optional fast/free preset |
| `assetAwareMcp.openrouterModel` | `liquid/lfm-2.5-1.2b-instruct:free` | Fast low-cost model for summaries and draft RAG answers |
| `assetAwareMcp.enableLightRag` | `false` | Optional KG indexing/querying; keep off for CPU-only or document-only workflows |
| `assetAwareMcp.dataDir` | `./data` | Storage for processed assets |
| `.env: LIGHTRAG_WORKING_DIR` | `./data/lightrag_db` | LightRAG working directory written by the setup wizard / settings panel |
| `assetAwareMcp.enableMarkerBackend` | `false` | Reserved for Marker; temporarily disabled because `marker-pdf` pins vulnerable `Pillow<11` |
| `assetAwareMcp.torchBackend` | `cpu` | Reserved torch backend setting for Marker after its Pillow dependency supports the secure runtime |

Runtime note:
The extension prefers a managed Python 3.11 runtime when launching the MCP server via `uv tool run`, with Python 3.10 fallback for older machines. This avoids package builds on machines without native toolchains, especially macOS systems missing Xcode Command Line Tools, while keeping the project itself compatible with newer Python versions.

Structured backend note:
The current packaged extras cannot install MinerU, Marker, or their torch stack. MinerU 3.4.4 pins `transformers<5` while current fixes require `transformers>=5.5`; Marker still requires `Pillow<11` while this runtime requires `Pillow>=12.2.0`. Both extras stay empty and fail closed. Use `ETL_ENGINE=pymupdf4llm` or `docling` for a maintained high-fidelity alternative.

Installation scope & storage:
- The VSIX installs as a user/global extension (standard VS Code behavior), so you do not need a separate install per workspace.
- The MCP server is launched via version-pinned `uv tool run asset-aware-mcp`; upgrades reuse the same user-level uv cache.
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
  If the legacy Marker setting is requested, it shows `effective: false` and the active security hold instead of installing `marker-pdf`.
3.  **Inspect Logs**:
    *   Open **Output** panel (`Ctrl+Shift+U`).
    *   Select **Asset-Aware MCP** from the dropdown to see extension logs.
    *   Select **Asset-Aware MCP Dependencies** to see dependency check results.
4.  **Development Mode**:
    *   Clone the repo.
    *   Open `vscode-extension` folder.
    *   Run `npm install`.
    *   Press `F5` to launch the **Extension Development Host**.

## 📚 MCP Tools (30 public tools)

The default surface is `balanced`: 17 operation-based facade tools plus 13 common shortcuts. Use `ASSET_AWARE_MCP_TOOL_SURFACE=compact` for facade-only mode, or `ASSET_AWARE_MCP_TOOL_SURFACE=legacy` for the full direct-tool compatibility inventory.

| Area | Public tools |
|------|--------------|
| Documents, assets, evidence, conversion | `document`, `document_asset`, `evidence`, `convert_document`, `ingest_documents`, `list_documents`, `parse_pdf_structure`, `fetch_document_asset`, `find_evidence_spans`, `verify_citation_ref`, `citation_bundle` |
| DOCX / DFM | `docx`, `docx_table`, `ingest_docx`, `get_docx_content`, `save_docx`, `docx_table_edit_plan` |
| Sections, jobs, KG, profiles | `section`, `job`, `get_job_status`, `list_jobs`, `knowledge`, `etl_profile` |
| A2T tables | `plan_table`, `table_manage`, `table_data`, `table_cite`, `table_history`, `table_draft`, `discover_sources` |

For PDF agent handoff, run `document(op="preflight", pdf_path="...")` when OCR/layout quality is uncertain, then use `document(op="auto", file_paths=[...])`. For an ingested document, use `document(op="prepare_ai", doc_id="...")`, audit as needed, and finish with `document(op="export_assets", doc_id="...")` to create a reusable Foam-compatible asset bundle. Job status and document inspection responses include facade-style next actions while the public tool count stays at 30.

## 🔗 Links

- [GitHub Repository](https://github.com/u9401066/asset-aware-mcp)
- [PyPI Package](https://pypi.org/project/asset-aware-mcp/)
- [Technical Specification](https://github.com/u9401066/asset-aware-mcp/blob/main/docs/spec.md)

## 📝 License

Apache-2.0
