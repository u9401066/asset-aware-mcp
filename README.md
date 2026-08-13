# asset-aware-mcp

> Citation-ready document infrastructure for AI agents: turn PDFs, DOCX files,
> tables, figures, and evidence spans into reusable assets and Foam/LightRAG wikis.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

🌐 [繁體中文](README.zh-TW.md) · [Docs Site](https://u9401066.github.io/asset-aware-mcp/#/overview-zh) · [GitHub Wiki](https://github.com/u9401066/asset-aware-mcp/wiki)

## v1.0.1 reliability refresh

- Large PDF text/table/figure results use a private, atomic, size-bounded
  MessagePack handoff instead of a multiprocessing pipe or executable pickle.
  This keeps multi-megabyte raster assets moving without pipe backpressure and
  fails closed on partial, oversized, malformed, or crashed worker output.
  Worker timeout environment values must be finite; `NaN`/infinities fall back
  to safe defaults. Finite values `<=0` retain the historical explicit direct
  mode for compatibility and should not be used by managed production launchers.
- Codex-managed MCP configuration is validated as real TOML, preserves custom
  and unrelated tables, uses 180/900-second startup/tool timeouts, and never
  writes credential values. Its isolated working directory plus
  `ASSET_AWARE_DISABLE_DOTENV=true` prevents a managed server from silently
  reloading an unrelated workspace `.env`.
- Global Codex/Cline/Copilot config writes are workspace-trust gated and always
  use the exact published extension version plus isolated global storage. A
  lookalike repository cannot persist its local Python or `.env` values into a
  global agent launcher.
- MCP SDK 2 operational logs stay on stderr, empty/blank ingest requests are
  rejected before job persistence, and a true-stdio regression now verifies a
  large figure, a table, citation-ready evidence, complete bundle hashes, Foam
  notes, deterministic re-export, and an unchanged source PDF.
- GitHub Pages now provides a bilingual responsive Evidence Rail workflow,
  exact 30-tool explorer, install/development guidance, generated docs reader,
  and direct GitHub/Release/Issue links instead of stale raster architecture
  screenshots.

## 🎯 Why Asset-Aware MCP?

**A server-local image path is not a portable multimodal payload.** Whether an agent can
dereference that path depends on its client, sandbox, and filesystem permissions.

| Method | Can AI analyze image content? | Description |
|------|:-------------------:|------|
| ⚠️ Provide only a PNG path | Client-dependent | The client may be remote or sandboxed and cannot safely assume the server path exists locally |
| ✅ **Asset-Aware MCP** | **Yes, for compatible multimodal clients** | Fetches bounded image bytes through MCP so the client can pass real image content to its vision model |

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

- 📄 **Asset-Aware ETL** - PDF → Markdown with a pluggable multi-engine parser (`ETL_ENGINE`):
  - **PyMuPDF** (default) - Fast extraction (~50MB), no models required
  - **PyMuPDF4LLM** (`[pdf-plus]`) - Drop-in layout-aware upgrade, no GPU
  - **Docling** (`[docling]`) - MIT-licensed layout+table+formula+chart engine; bridges through an isolated `.venv-docling` interpreter when the main environment can't install it directly (see [docs/docling-setup.md](docs/docling-setup.md))
  - **MinerU** - Adapter retained, but the packaged extra is on security hold while MinerU pins a vulnerable `transformers<5` chain
  - **Marker** - Adapter retained for evaluation, but production selection fails closed while upstream `marker-pdf` conflicts with the patched Pillow floor. The legacy `use_marker` parameter now means “prefer the configured structured extractor”; it does not bypass this hold.
- 🧩 **Unified Segmentation Export** - Normalized `segmentation.json` merges manifest, blocks, reading order, and persisted markdown line spans for downstream tools and extensions.
- 🩺 **Safe PDF Preflight Router** - `document(op="preflight")` classifies each page as native, sparse, image, scanned, or hybrid; returns 1-based top-left locators, source SHA-256, OCR reasons, and a bounded extraction-engine recommendation from a process-isolated inspector.
- 📦 **Reusable Agent Asset Bundles** - `document(op="export_assets")` writes deterministic `manifest.json`, `assets.jsonl`, copied media, and a portable Foam `index.md`/`notes/**` subtree while preserving stable IDs, hashes, locators, and citation refs.
- 🛡️ **PDF Safety/Structure/Coverage/Accessibility Audits** - OpenDataloader-inspired artifact-only reports flag suspicious hidden/off-page/prompt-injection text, native structure signals, segmentation coverage gaps, and accessibility/readability readiness via the existing `document` facade. `document(op="prepare_ai")` and `document(op="auto")` expose agent-ready status and next actions without adding public tools.
- 🧭 **Structural Pointer Retrieval** - Proxy-Pointer-inspired `document(op="pointer_index")`, `document(op="structural_retrieve")`, and `document(op="compare")` preserve section breadcrumbs, line/char/byte locators, source hashes, asset IDs, and evidence-span provenance without adding MCP tools.
- 🖼️ **Layout Overlay Debugging** - Render page overlays from `original.pdf` to inspect bbox, segment type, and reading order visually.
- 🔤 **On-Demand OCR Preprocessing** - Optional `ocrmypdf` preprocessing path for scanned PDFs before ETL.
- 🧭 **Section Navigation** - Dynamic hierarchy section tree through the `section` facade: browse, search, detail, content reading, and block extraction for any depth of headings.
- 🔄 **Async Job Pipeline** - Supports asynchronous ingest, configured structured parse, OCR, and conversion jobs with progress tracking.
- 🔀 **Mixed-Format Batch Ingestion** - `document(op="auto", file_paths=[...])` auto-detects a batch mixing PDF with DOCX/DOC/ODT/ODS, ingests each file through its correct existing engine in one background job, isolates per-file failures so one bad file cannot abort the rest, and reports per-file progress — no new public tool required.
- 🗺️ **Document Manifest** - Provides a structured "map" of the document for precise data access by Agents.
- 🧠 **LightRAG Integration** - Knowledge Graph + Vector Index, supporting cross-document comparison and reasoning.
- 🧾 **Verified Citation Bundles** - `citation_bundle`, Foam evidence packs, citation health checks, table/figure evidence notes, and claim promotion export citation-ready spans with locator, quote/hash, context, CRAAP scaffold, and verification status.
- 📝 **Docx Editing (DFM)** - Edit .docx files in Markdown via **Docx-Flavored Markdown** format. Supports legacy `.doc`, `.odt`, and `.ods` ingest via LibreOffice auto-conversion. The balanced surface keeps 6 DOCX/DFM public entrypoints for ingest, read, save, validation, conversion, table edit planning, and Docx ↔ A2T bridges.
- 🛡️ **DFM Integrity Checker** - Automatic validation and auto-repair at every pipeline stage (post-ingest, pre-save, post-save). Catches orphan markers, column mismatches, and format inconsistencies.
- 📊 **A2T (Anything to Table)** - 7 operation-based tools for building professional tables from **any source** (PDF assets, Knowledge Graph, URLs, user input). Features: stable row IDs, row search/filter/paging, citation coverage, artifact-only large-table render, skipped-large-table UX, **Citations** (AssetRef), **Audit Trail**, **Schema Evolution**, **Templates**, **Drafting**, and **Token-efficient resumption**.
- 🖥️ **VS Code Management Extension** - Graphical interface for monitoring server status, ingested documents, document artifacts, citation spans, and **A2T tables/drafts** with one-click Excel export.
- 🔌 **MCP SDK 2 Server** - Uses the official Python SDK `MCPServer` API, runtime-injected context, and v2 clients. MCP SDK v1 is intentionally unsupported.
- 🔬 **Research-ready, domain-neutral assets** - Works with scholarly, technical, policy, and operational documents; bounded image bytes let compatible multimodal clients analyze figures instead of relying on server-local paths.

## 🏗️ Architecture

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
│   └── presentation/        # 🔴 Presentation: MCP SDK 2 MCPServer
├── data/                    # Document and Asset Storage
├── docs/
│   └── spec.md              # Technical Specification
├── tests/                   # Unit and Integration Tests
├── vscode-extension/        # VS Code Management Extension
└── pyproject.toml           # uv Project Config
```

## 📐 Architecture and workflows

The maintained, versioned references are the [documentation site](https://u9401066.github.io/asset-aware-mcp/),
[architecture guide](docs/wiki/Architecture.md), [PDF workflow](docs/wiki/PDF-Document-Workflow.md),
[MCP tool catalog](docs/wiki/MCP-Tools.md), and [release checklist](docs/wiki/Release-And-Testing.md).
They are generated and checked with the implementation so tool counts, engine holds, and release behavior do not drift inside obsolete screenshots.

## 🚀 Quick Start

```bash
# Install dependencies (using uv) — default install stays on the fast PyMuPDF backend
uv sync

# Optional high-fidelity PDF->asset engines:
# uv sync --extra pdf-plus   # PyMuPDF4LLM: drop-in layout-aware upgrade
# uv sync --extra docling    # Docling: MIT layout+table+formula+chart engine
# MinerU and Marker packaged extras are temporarily empty security holds.
# Then set ETL_ENGINE=pymupdf4llm|docling.

# Run MCP Server
uv run python -m src.presentation.server

# Or use the VS Code extension for graphical management
```

Runtime note:
The VS Code extension prefers a managed Python 3.11 runtime when launching the MCP server via version-pinned `uv tool run`, with Python 3.10 fallback for older machines. This avoids native package builds on end-user machines, especially macOS systems without Xcode Command Line Tools, while keeping the project itself compatible with newer Python versions.

Installation scope note:
- The VS Code extension installs once per user. In a trusted workspace, the native VS Code MCP provider may use workspace-scoped `DATA_DIR`, cache, settings, and `.env`; local source is accepted only in Extension Development/Test mode (or a future explicit opt-in).
- Global Codex and Cline entries always launch `asset-aware-mcp==<extension-version>` from extension global storage. They do not inherit workspace-local source, workspace-scoped settings, or repository `.env` values. Restricted Mode skips external config writes and assistant-asset sync entirely.

Engine selection note:
`ETL_ENGINE` picks the extraction backend (default `pymupdf`). The active packaged structured engines (`pymupdf4llm`, `docling`) lazy-load and gracefully fall back to PyMuPDF when their extra is not installed. Marker remains on hold because `marker-pdf` requires `Pillow<11`; MinerU is also on hold because MinerU 3.4.4 pins `transformers<5` while current security fixes require `transformers>=5.5`. Both adapters remain in-tree, but this package will not install a known-vulnerable dependency chain. Use `document(op="preflight", pdf_path="...")` to choose between fast native extraction, OCR, and Docling before ingest.

Agent asset / Foam handoff:

```text
document(op="preflight", pdf_path="/papers/source.pdf")
document(op="auto", file_paths=["/papers/source.pdf"])
document(op="export_assets", doc_id="doc_...", output_dir="agent-assets")
```

The exported directory is deterministic and portable: `manifest.json` is the
bundle contract, `assets.jsonl` is the agent-readable inventory, and
`index.md` plus `notes/**` can be mounted or copied into a Foam workspace.

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
| ETL | **PyMuPDF** (default) + secure optional **PyMuPDF4LLM** / **Docling** engines; MinerU and Marker adapters are on dependency security hold |
| RAG | LightRAG (lightrag-hku) |
| MCP | Official Python MCP SDK 2 (`MCPServer`); SDK v1 unsupported |
| Storage | Local filesystem (JSON/Markdown/PNG) |

## 📋 Documentation

Installation guidance:
- Default install: `uv sync` (slim ~227 MB; no LightRAG/KG dependencies).
- LightRAG / Knowledge Graph backend (optional, since v0.6.34): `uv tool install --upgrade --python 3.11 'asset-aware-mcp[lightrag]'` for uvx/published users, or `uv sync --extra lightrag` for local source checkouts. Required before setting `ENABLE_LIGHTRAG=true`.
- VS Code extension: run the command `Asset-Aware MCP: Install LightRAG Backend` from the Command Palette; it auto-detects source vs published mode and emits the matching install command.
- OpenRouter optional preset (since v0.6.35): set `LLM_BACKEND=openrouter`, `OPENROUTER_API_KEY=...`, and optionally `OPENROUTER_MODEL=liquid/lfm-2.5-1.2b-instruct:free` for fast low-cost summaries and draft RAG answers. LightRAG retrieval still uses the configured embedding backend.
- High-fidelity PDF engines: `uv sync --extra pdf-plus` (PyMuPDF4LLM) or `uv sync --extra docling` (Docling), then set `ETL_ENGINE` accordingly. Docling ships a cross-platform isolated installer; see [docs/docling-setup.md](docs/docling-setup.md).
- MinerU and Marker backends: their adapters remain available for upstream testing, but the packaged extras are empty security holds until their dependency caps permit patched `transformers` and Pillow releases.
- VS Code extension: `assetAwareMcp.enableMarkerBackend` is retained as a setting, but the launcher will not install `marker-pdf` while the security hold is active.

- [Technical Spec](docs/spec.md) - Detailed technical specification
- [Architecture](ARCHITECTURE.md) - System architecture
- [Constitution](CONSTITUTION.md) - Project principles
- [Competitive Analysis](docs/competitor-analysis.md) - MCP + DOCX ecosystem landscape

## 📄 License

[Apache License 2.0](LICENSE)
