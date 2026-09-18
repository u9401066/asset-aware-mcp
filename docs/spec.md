# Asset-Aware MCP: Agent Document Collaboration Specification

## Agent document collaboration contract (2026-09-18)

The goal is native cross-format document CRUD: create, read, decompose, update,
write back and delete documents/components, preserving features outside the edit.
Standalone table creation is first-class. Markdown and wikilinks are projections,
not universal storage or substitutes for the editable source.

An asset is an addressable, versioned unit an agent can inspect, reuse or operate
on. Source files are root assets; paragraphs, cells, worksheets, slides, pictures,
charts and embedded objects are children. Each carries identity, source revision,
a native locator, typed representations, relationships, operation capabilities,
preservation constraints and validation state. New agent-created assets record a
creation origin without requiring a PDF. Inferred meaning is separate from source.

Human handoff: register original identity → inspect native format/features →
expose structure/previews/capabilities → stage scoped edits → necessary checks →
agent review/correction → revision-checked atomic commit → optionally project selected assets
into a wikilink evidence library. Source files and curated notes retain ownership.
Deleting a projection does not mean deleting the original document.

### Necessary MCP checks and agent verification

MCP owns source/version preconditions, staged writes, format-preservation guards,
structural checks and inspectable before/after operation results. Supported writes
must fail on stale sources or failed integrity checks and publish atomically.
It exposes locators, diffs, warnings and available previews for agent inspection.
The agent owns complete semantic and visual verification, decides corrections and
coordinates subsequent tool calls. MCP rechecks each resulting operation.
Deterministic repair is appropriate only for explicitly supported mechanical rules;
it is not a promise of complete automatic correction or layout verification.
Verification coverage and unperformed checks must remain explicit. Structural
validity alone must never be reported as semantic correctness or full fidelity.

### Citation presentation contract

Canonical identity, revision, locator and exact quote/hash are independent from
human citation style. A versioned declarative contract defines inline/reference
templates and required metadata, supporting source labels, author/year,
caller-assigned numeric references and custom organizational formats. Templates
are not full APA/Chicago/CSL implementations; standards-aware rendering remains
in scope. Missing metadata must be reported, never invented.

Allow only named scalar placeholders, no code/attribute/format expressions.
Metadata cannot replace canonical IDs, hashes or locators. Export the contract
and its hash alongside notes/bundles. Style changes preserve evidence identities
and wikilink targets. Locator validity, extraction accuracy and semantic support
are distinct concepts.

### Starting coverage and completion evidence

Published 1.0.1 covers PDF read/decompose/export, scoped DOCX/DFM writeback and
independent A2T table creation/edit/export. Native spreadsheet/presentation CRUD,
general asset registration, cross-format wiki export, per-format operation checks
and agent review workflows, and standards-aware APA/Chicago/CSL rendering remain
unfinished. The current unreleased milestone adds custom citation display contracts
to existing PDF evidence/Foam and portable exports; it does not complete the
remaining native-format adapters or academic style engine. Conversion to
DOCX/PPTX does not prove native round-trip fidelity. ROADMAP.md tracks full scope.
Each milestone updates README, Pages, repository metadata/labels and Memory Bank;
reviewed commits are pushed in stages and releases require the full harness.

## 2. Core Architecture

### 2.1 DDD (Domain-Driven Design) 分層架構

```text
┌─────────────────────────────────────────────────────────────┐
│                   Presentation Layer                         │
│                   (MCP Server Interface)                     │
│  server.py - MCPServer tools & resources exposed to AI Agent│
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                   Application Layer                          │
│                   (Use Cases / Services)                     │
│  DocumentService, AssetService, JobService, KnowledgeService │
│  TableService (A2T - Anything to Table)                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                     Domain Layer                             │
│                   (Core Business Logic)                      │
│  Entities: Document, Manifest, Table, Figure, Section, Job   │
│  A2T Entities: TableContext, TableDraft, TableSchema         │
│  Value Objects: AssetType, DocId, JobStatus                 │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                 Infrastructure Layer                         │
│                 (External Dependencies)                      │
│  PyMuPDFExtractor (Core ETL), LightRAGAdapter,               │
│  FileStorage, FileJobStore, ExcelRenderer                    │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 ETL Pipeline: "The Mechanic"

- **PyMuPDF Integration**: Uses PyMuPDF (fitz) for lightweight and fast PDF-to-Markdown conversion, including heuristic-based table extraction and image extraction.
- **Asynchronous Processing**: Ingestion is handled as background jobs, allowing the Agent to track progress for large batches of documents.
- **Asset Decomposition**: Separates text, tables, and figures with page-level metadata.
- **Knowledge Graph**: Uses LightRAG to build a dual-index (Vector + Graph) for cross-document reasoning.
- **Document Manifest**: Generates a `manifest.json` for each document, acting as a "map" for the AI Agent.

### 2.3 A2T (Anything to Table) Workflow: "The Orchestrator"

- **Schema Planning**: `plan_table_schema` allows Agents to design table structures before creation.
- **Drafting System**: `TableDraft` provides persistent storage for work-in-progress tables, enabling resumption across sessions.
- **Batch Streaming**: `add_rows_to_draft` supports incremental data accumulation for long tables.
- **Token Efficiency**: `resume_draft` and `get_section_content` minimize context window usage.
- **Excel Rendering**: Professional output with auto-beautification based on table intent.

### 2.4 MCP Server: "The Interface"

- **Tools**: Exposes tools for ingestion, job tracking, manifest inspection, precise asset fetching, and A2T orchestration.
- **Resources**: Provides dynamic URI-based access to document outlines, tables, figures, and A2T table/draft states.
- **Vision Support**: Figures are transmitted as **Base64 images** within `ImageContent` for direct analysis by Vision-capable LLMs.

## 3. Tech Stack

| Category | Technology | Purpose |
| -------- | ---------- | ------- |
| Language | Python 3.10+ | Core runtime |
| MCP | official `mcp>=2,<3` Python SDK | MCPServer; SDK v1 unsupported |
| ETL | **PyMuPDF** | Primary PDF decomposition & Table recognition |
| RAG | LightRAG (`lightrag-hku`) | Knowledge Graph & Vector Index |
| Validation | Pydantic | Data models & validation |
| Storage | Local filesystem | JSON/Markdown/Image storage |

## 4. Project Structure (DDD)

```text
asset-aware-mcp/
├── src/
│   ├── domain/                      # 🔵 Domain Layer (Pure Logic)
│   │   ├── entities.py              # Document, Manifest, Assets
│   │   ├── job.py                   # ETL Job entities
│   │   ├── value_objects.py         # AssetType, DocId, JobStatus
│   │   ├── services.py              # ManifestGenerator
│   │   └── repositories.py          # Abstract interfaces
│   │
│   ├── application/                 # 🟢 Application Layer (Use Cases)
│   │   ├── document_service.py      # Ingestion orchestration
│   │   ├── job_service.py           # Async job management
│   │   ├── asset_service.py         # Precise asset retrieval
│   │   └── knowledge_service.py     # RAG & Graph queries
│   │
│   ├── infrastructure/              # 🟠 Infrastructure Layer (Impl)
│   │   ├── pdf_extractor.py         # PyMuPDF implementation (Core ETL)
│   │   ├── lightrag_adapter.py      # LightRAG integration
│   │   ├── file_storage.py          # Local file repository
│   │   ├── job_store.py             # Persistent job tracking
│   │   └── config.py                # Settings & environment
│   │
│   └── presentation/                # 🔴 Presentation Layer (Interface)
│       └── server.py                # MCP SDK 2 server entrypoint
│
├── data/                            # Local storage root
│   ├── {doc_id}/                    # PDF document artifacts
│   │   ├── {doc_id}_full.md         # Full text markdown
│   │   ├── {doc_id}_manifest.json   # Asset map
│   │   └── images/                  # Extracted figures
│   └── lightrag_db/                 # Knowledge graph database
```

## 5. MCP Interface Definition

### 5.1 Tools

| Tool | Input | Description |
|------|-------|-------------|
| `ingest_documents` | `file_paths`, `async_mode` | Start ETL pipeline (returns `job_id` if async) |
| `get_job_status` | `job_id` | Check progress of an ETL job |
| `list_jobs` | `active_only` | List recent or active ETL tasks |
| `list_documents` | None | List all ingested documents |
| `inspect_document_manifest` | `doc_id` | View the "Map" (Tables, Figures, Sections) |
| `fetch_document_asset` | `doc_id`, `type`, `id` | Get specific Table (MD), Figure (B64), or Section |
| `consult_knowledge_graph` | `query`, `mode` | Cross-document RAG query |

### 5.2 Resources

| URI | Description |
|-----|-------------|
| `documents://list` | List of all documents |
| `document://{id}/outline` | Bird's-eye view of document structure |
| `document://{id}/manifest` | Full JSON manifest |
| `document://{id}/tables` | List of tables in the document |
| `document://{id}/figures` | List of figures in the document |
| `knowledge-graph://summary` | Statistics and sample entities from the graph |

## 6. Image Handling (Base64)

- **Extraction**: PyMuPDF extracts figures with page numbers.
- **Transmission**: `fetch_document_asset` returns `ImageContent` containing the Base64 data.
- **Vision AI**: Agents can "see" the figure directly to interpret charts, diagrams, or medical imaging.

## 7. Constraints & Directives

1. **DDD Integrity**: Domain layer must remain pure and not depend on infrastructure.
2. **Job-Based ETL**: Long-running tasks must use the `JobService` to avoid timeouts.
3. **Manifest-First**: Agents are encouraged to use `inspect_document_manifest` or `outline` resource before fetching full content.
4. **Local-First**: All processing and storage must happen locally by default.

## Upstream adoption (2026-09-18)

- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk):
  current stable v2 API, MCPServer and Client; baseline runtime uses mcp>=2,<3.
- [Docling Core](https://github.com/docling-project/docling-core): native document
  hierarchy and provenance; retain original structure alongside agent projections.
- [MinerU](https://github.com/opendatalab/MinerU): compare current structured output
  contracts and rendering; the existing held adapter is not evidence of 4.x compatibility.
- [pikepdf](https://github.com/pikepdf/pikepdf): evaluate native PDF manipulation,
  object preservation and validation for future PDF CRUD.
- [GROBID](https://github.com/grobidOrg/grobid),
  [gmft](https://github.com/conjuncts/gmft) and
  [OmniDocBench](https://github.com/opendatalab/OmniDocBench): scholarly structures,
  table extraction and parsing evaluation. Selection requires local real-file
  evaluation; repository claims alone do not establish fidelity.
