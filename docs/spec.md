# Tech Spec: Medical RAG with Asset-Aware MCP

## 1. Project Goal

Build a local-first Model Context Protocol (MCP) server tailored for medical research. The system is designed to help an AI Agent (Copilot) write accurate reports from multiple PDFs. Instead of feeding full texts blindly, the system generates a structured "Document Manifest" (Map) allowing the Agent to precisely inspect structures and fetch specific assets (Tables, Sections, Figures) on demand.

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
