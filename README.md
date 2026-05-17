# asset-aware-mcp

> 🏥 Medical RAG with Asset-Aware MCP - Precise PDF asset retrieval (tables, figures, sections) and Knowledge Graph for AI Agents.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [繁體中文](README.zh-TW.md) · [Docs Site](https://u9401066.github.io/asset-aware-mcp/#/overview-zh) · [GitHub Wiki](https://github.com/u9401066/asset-aware-mcp/wiki)

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

- 📄 **Asset-Aware ETL** - PDF → Markdown with a PyMuPDF-first parser and retained Marker code path:
  - **PyMuPDF** (default) - Fast extraction (~50MB)
  - **Marker** (`use_marker=True`) - High-precision structured parsing code path retained, but packaged runtime remains on security hold in v0.7.0 until upstream `marker-pdf` supports patched Pillow
- 🧩 **Unified Segmentation Export** - Normalized `segmentation.json` merges manifest, blocks, reading order, and persisted markdown line spans for downstream tools and extensions.
- 🛡️ **PDF Safety/Structure/Coverage/Accessibility Audits** - OpenDataloader-inspired artifact-only reports flag suspicious hidden/off-page/prompt-injection text, native structure signals, segmentation coverage gaps, and accessibility/readability readiness via the existing `document` facade. `document(op="prepare_ai")` and `document(op="auto")` expose agent-ready status and next actions without adding public tools.
- 🧭 **Structural Pointer Retrieval** - Proxy-Pointer-inspired `document(op="pointer_index")`, `document(op="structural_retrieve")`, and `document(op="compare")` preserve section breadcrumbs, line/char/byte locators, source hashes, asset IDs, and evidence-span provenance without adding MCP tools.
- 🖼️ **Layout Overlay Debugging** - Render page overlays from `original.pdf` to inspect bbox, segment type, and reading order visually.
- 🔤 **On-Demand OCR Preprocessing** - Optional `ocrmypdf` preprocessing path for scanned PDFs before ETL.
- 🧭 **Section Navigation** - Dynamic hierarchy section tree through the `section` facade: browse, search, detail, content reading, and block extraction for any depth of headings.
- 🔄 **Async Job Pipeline** - Supports asynchronous ingest, Marker-required parse, OCR, and conversion jobs with progress tracking.
- 🗺️ **Document Manifest** - Provides a structured "map" of the document for precise data access by Agents.
- 🧠 **LightRAG Integration** - Knowledge Graph + Vector Index, supporting cross-document comparison and reasoning.
- 🧾 **Verified Citation Bundles** - `citation_bundle`, Foam evidence packs, citation health checks, table/figure evidence notes, and claim promotion export citation-ready spans with locator, quote/hash, context, CRAAP scaffold, and verification status.
- 📝 **Docx Editing (DFM)** - Edit .docx files in Markdown via **Docx-Flavored Markdown** format. Supports legacy `.doc`, `.odt`, and `.ods` ingest via LibreOffice auto-conversion. The balanced surface keeps 6 DOCX/DFM public entrypoints for ingest, read, save, validation, conversion, table edit planning, and Docx ↔ A2T bridges.
- 🛡️ **DFM Integrity Checker** - Automatic validation and auto-repair at every pipeline stage (post-ingest, pre-save, post-save). Catches orphan markers, column mismatches, and format inconsistencies.
- 📊 **A2T (Anything to Table)** - 7 operation-based tools for building professional tables from **any source** (PDF assets, Knowledge Graph, URLs, user input). Features: stable row IDs, row search/filter/paging, citation coverage, artifact-only large-table render, skipped-large-table UX, **Citations** (AssetRef), **Audit Trail**, **Schema Evolution**, **Templates**, **Drafting**, and **Token-efficient resumption**.
- 🖥️ **VS Code Management Extension** - Graphical interface for monitoring server status, ingested documents, document artifacts, citation spans, and **A2T tables/drafts** with one-click Excel export.
- 🔌 **MCP Server** - Exposes tools and resources to Copilot/Claude via FastMCP.
- 🏥 **Medical Research Focus** - Optimized for medical literature, supporting Base64 image transmission for Vision AI analysis.

## 🏗️ Architecture

<p align="center">
  <img src="docs/images/architecture-overview.jpg" alt="Asset-Aware MCP Architecture" width="700">
</p>

```
┌─────────────────────────────────────────────────────────┐
│                    AI Agent (Copilot)                   │
└─────────────────────┬───────────────────────────────────┘
                      │ MCP Protocol (Tools & Resources)
┌─────────────────────▼───────────────────────────────────┐
│            MCP Server (Modular Presentation)            │
│  ┌─────────────────────────────────────────────────┐   │
│  │ tools/: 30 public tools (balanced surface)                   │   │
│  │   17 facade tools + 13 high-frequency shortcuts       │   │
│  │   compact=17 │ legacy/direct compatibility=63 │
│  └─────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ resources/: 13 resources in 2 modules           │   │
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
│  ├── {doc_id}/        # PDF document artifacts          │
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

## 📐 Architecture Diagrams

Visual overview for the project. All diagrams use consistent GitHub README style.

| Diagram | Description |
|---------|-------------|
| [01 — System Architecture](docs/diagrams/01-system-architecture.jpg) | Full stack: Telegram → Gateway → MCP Adapter → 3 MCP servers → Ollama |
| [02 — Data Layout](docs/diagrams/02-data-layout.jpg) | 30 balanced public tools + 13 resources; legacy direct tool compatibility remains available |
| [03 — PDF Ingestion Pipeline](docs/diagrams/03-pdf-ingestion-pipeline.jpg) | 7-stage flow from PDF upload to knowledge graph |
| [04 — DOCX Bidirectional Edit](docs/diagrams/04-docx-edit-pipeline.jpg) | DOCX ingest → TableContext edit → round-trip save workflow |
| [05 — Knowledge Graph Search](docs/diagrams/05-knowledge-graph-search.jpg) | Cross-document search with 3 parallel query paths |
| [06 — Installation Steps](docs/diagrams/06-installation-steps.jpg) | 7-step installation from clone to verification |
| [07 — PDF ETL Pipeline](docs/diagrams/07-pdf-etl-pipeline.jpg) | PyMuPDF default path + Marker security-hold diagnostics |
| [08 — KG Architecture](docs/diagrams/08-knowledge-graph-architecture.jpg) | lightrag-hku 3-layer KG architecture |
| [09 — Agent Harness Concept](docs/diagrams/09-agent-harness-concept.jpg) | Assistant harness model for stateless agents |

> 💡 All generation prompts are saved in [docs/diagrams/ALL-PROMPTS.md](docs/diagrams/ALL-PROMPTS.md) for style consistency and regeneration.

## 🚀 Quick Start

```bash
# Install dependencies (using uv) — default install skips Marker/torch
uv sync

# v0.7.0: Marker extra is temporarily empty because marker-pdf pins
# Pillow<11 while the secure runtime requires Pillow>=12.2.0.
# Use the default PyMuPDF backend until upstream marker-pdf supports patched Pillow.

# Run MCP Server
uv run python -m src.presentation.server

# Or use the VS Code extension for graphical management
```

Runtime note:
The VS Code extension prefers a managed Python 3.11 runtime when launching the MCP server via version-pinned `uv tool run`, with Python 3.10 fallback for older machines. This avoids native package builds on end-user machines, especially macOS systems without Xcode Command Line Tools, while keeping the project itself compatible with newer Python versions.

Installation scope note:
- The VS Code extension installs once per user (global). MCP launch env defaults `DATA_DIR` to workspace `./data` and `UV_CACHE_DIR` to `DATA_DIR/.uv-cache`; Prepare Server Runtime warms a workspace `.uv-cache`, falling back to extension global storage only when no workspace is open.
- Runtime data stays with your repo: `.env` and `assetAwareMcp.dataDir` default to `./data`, so ingested assets and the uv cache used by the launched server remain scoped to the current workspace.

Marker note:
Since v0.6.28 the packaged Marker extra has intentionally stayed on security hold: upstream `marker-pdf` 1.10.2 requires `Pillow<11`, while this release pins `Pillow>=12.2.0` for patched image-processing security. Default installs use the PyMuPDF backend only. `use_marker=True` / `parse_pdf_structure` will report that Marker is unavailable until upstream Marker supports a patched Pillow range.

## 🔌 MCP Tools

The default runtime surface is **balanced**: 30 public tools that keep the full document workflow available without overwhelming agents. It is made of 17 operation-based facade tools plus 13 high-frequency shortcuts. Set `ASSET_AWARE_MCP_TOOL_SURFACE=compact` for the 17 facade-only surface, or `ASSET_AWARE_MCP_TOOL_SURFACE=legacy` / `ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS=true` for the full 63-tool compatibility inventory.

| Area | Balanced public tools |
|------|------------------------|
| Documents, assets, evidence, conversion | `document`, `document_asset`, `evidence`, `convert_document`, `ingest_documents`, `list_documents`, `parse_pdf_structure`, `fetch_document_asset`, `find_evidence_spans`, `verify_citation_ref`, `citation_bundle` |
| DOCX / DFM | `docx`, `docx_table`, `ingest_docx`, `get_docx_content`, `save_docx`, `docx_table_edit_plan` |
| Sections, jobs, KG, ETL profiles | `section`, `job`, `get_job_status`, `list_jobs`, `knowledge`, `etl_profile` |
| A2T tables | `plan_table`, `table_manage`, `table_data`, `table_cite`, `table_history`, `table_draft`, `discover_sources` |

See [MCP Tools](docs/wiki/MCP-Tools.md) and [Tool Consolidation](docs/wiki/MCP-Tool-Consolidation.md) for operation details, shortcut rationale, and legacy direct-tool mapping.

Agent handoff note:
Use `document(op="auto", file_paths=[...])` for new PDFs and `document(op="auto", doc_id="...")` or `document(op="prepare_ai", doc_id="...")` for existing documents. `document(op="prepare_ai", output_format="json")` returns the v2 readiness contract with `status`, `blockers`, `warnings`, `capabilities`, `artifacts`, `missing_audits`, `invalid_audits`, `audit_artifacts`, and `next_actions`. `document(op="audit", doc_id="...")` reuses current audit artifacts only when they are present and valid; pass `refresh=true` to rebuild safety, native-structure, coverage, and accessibility reports. Use `document(op="pointer_index")`, `document(op="structural_retrieve", query="...")`, and `document(op="compare", doc_b_id="...", criteria="...")` when an agent needs section-level structural retrieval or comparison without new public tools. Readiness and job-status artifact discovery are read-only, so status checks do not create document directories.

PDF audit caveat:
The audit reports are inspired by OpenDataloader-style artifact workflows, but they are not a sanitizer, a PDF/UA certification, or an OpenDataloader compatibility layer. They preserve source artifacts and report conservative diagnostics for review.

## 🔧 Tech Stack

| Category | Technology |
|----------|------------|
| Language | Python 3.10+ |
| Package Manager | **uv** (all pip/setup-python removed) |
| ETL | **PyMuPDF** (fitz); **Marker** is temporarily on security hold |
| RAG | LightRAG (lightrag-hku) |
| MCP | FastMCP |
| Storage | Local filesystem (JSON/Markdown/PNG) |

## 📋 Documentation

Installation guidance:
- Default install: `uv sync` (slim ~227 MB; no LightRAG/KG dependencies).
- LightRAG / Knowledge Graph backend (optional, since v0.6.34): `uv tool install --upgrade --python 3.11 'asset-aware-mcp[lightrag]'` for uvx/published users, or `uv sync --extra lightrag` for local source checkouts. Required before setting `ENABLE_LIGHTRAG=true`.
- VS Code extension: run the command `Asset-Aware MCP: Install LightRAG Backend` from the Command Palette; it auto-detects source vs published mode and emits the matching install command.
- OpenRouter optional preset (since v0.6.35): set `LLM_BACKEND=openrouter`, `OPENROUTER_API_KEY=...`, and optionally `OPENROUTER_MODEL=liquid/lfm-2.5-1.2b-instruct:free` for fast low-cost summaries and draft RAG answers. LightRAG retrieval still uses the configured embedding backend.
- Marker backend: temporarily disabled in v0.7.0 because `marker-pdf` pins vulnerable `Pillow<11`; the `marker` / `pdf` extras are compatibility placeholders until upstream supports patched Pillow.
- VS Code extension: `assetAwareMcp.enableMarkerBackend` is retained as a setting, but the launcher will not install `marker-pdf` while the security hold is active.

- [Technical Spec](docs/spec.md) - Detailed technical specification
- [Architecture](ARCHITECTURE.md) - System architecture
- [Constitution](CONSTITUTION.md) - Project principles
- [Competitive Analysis](docs/competitor-analysis.md) - MCP + DOCX ecosystem landscape

## 📄 License

[Apache License 2.0](LICENSE)
