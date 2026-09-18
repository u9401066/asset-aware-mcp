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
unfinished in that baseline. Version 1.1.0 adds custom citation display contracts to existing PDF
evidence/Foam and portable exports, plus a native file registry and scoped
spreadsheet operations described below. Remaining native-format adapters,
spreadsheet structural CRUD and academic style rendering are still unfinished. Conversion to
DOCX/PPTX does not prove native round-trip fidelity. ROADMAP.md tracks full scope.
Each milestone updates README, Pages, repository metadata/labels and Memory Bank;
reviewed commits are pushed in stages and releases require the full harness.

### Native DOCX / DFM bridge (v1.3.0)

`read_docx` reads a registered DOCX immutable revision through the existing DFM
parser/renderer in a private temporary workspace. Its deterministic DFM projection
omits the session creation timestamp and binds the full native asset ID and SHA-256
revision in frontmatter. Return bounded character excerpts, the full projection
hash and paginated block summaries; clients must assemble every excerpt before
editing. Block IDs and locators are revision-scoped, not cross-version identities.

`update_docx` requires expected_revision and a complete docx_edit payload. Re-ingest
that immutable revision, check the native frontmatter binding, then reuse
DocxService.save_docx with force disabled. Existing DFM session/checksum,
pre/post-save, table-shape and unedited-block guards remain mandatory. Only after
these pass may a checked package become a managed native revision under the
repository's compare-and-swap lock. No update writes to the human source file;
publish/writeback remain explicit native operations with their existing checks.

Before parsing, enforce the native ZIP/member/XML limits, reject DTDs and require
the supported transitional DOCX main part. Signed/protected documents require a
separate editing workflow. After editing, verify identical member inventory and
unchanged bytes outside document.xml (plus settings.xml for explicit tracked
changes). Report changed parts/block IDs, preservation checks and agent review
requirements. This adds scoped existing-body edits, not arbitrary insertion,
deletion, style design, DOC/DOCM conversion or complete visual fidelity. Native
DOCX evidence/wiki integration is described below. Legacy operations remain available.

### DOCX component evidence and wiki projection (v1.3.0)

Native DOCX blocks expose the complete existing IR representation, native part and
revision-scoped block ID, plus a canonical representation hash. read_docx_block
returns bounded text excerpts with full-reference and full-text hashes. read_docx
summaries carry the same references; previews are never used to compute evidence.
verify resolves the immutable blob and exact block/part, recomputes the complete
representation and reports integrity separately from freshness and agent review.
Old references remain verifiable after edits/archive. The serializer's extraction
coverage is explicit: integrity does not prove that every OOXML feature was parsed.

DOCX export_wiki uses the distinct docx-blocks-v1 projection in snapshot identity,
so previously exported opaque DOCX snapshots and all XLSX/XLSM snapshots remain
untouched. Export full JSONL block representations/references, revision-pinned
block/index notes, the original DOCX and exact package-part attachments with
original-part-to-filename mapping and hashes. Each attachment's provenance points
to the original package member; do not infer chart values or fabricate media links
from temporary DFM filenames. Block/part locators drive custom citation display.

Retain existing no-overwrite publication rules. Reject whole exports exceeding
20,000 block records, 10,000 package parts, 30,004 artifacts or 128 MiB; never export
a silently incomplete evidence collection. Unknown/unsupported parsed semantics
remain available in the original and package parts for agent review. No claim of
full visual fidelity, automatic quality scoring or semantic claim verification.

### Native file assets and spreadsheet operations (v1.1.0)

A registered file receives a persistent asset ID independent of its filename and
content hash. Immutable revisions use SHA-256. Source identity, native structure,
capabilities and review coverage travel together; inferred meaning remains an
agent annotation, not a fabricated extraction result. Registration supports opaque
formats without pretending to provide a native editor for every format.

The first native adapter reads XLSX/XLSM worksheet/cell locators, creates independent
XLSX workbooks and updates/clears typed cells. It edits only the necessary OOXML
parts, retains styles and all unrelated ZIP member bytes, and checks the resulting
package before publishing an immutable managed revision. Shared/array formula
regions, rich-text replacements, protected sheets and digitally signed packages
require an explicit supported operation; unsupported edits fail without writing.
Formula caches are not evaluated by MCP. Edits set recalculation flags and report
cached formula values as unverified. Plain strings never become formulas implicitly.

The registry provides optimistic revision checks, serialized writes and retained
history. Updates first create managed revisions; explicit source writeback requires
the expected source hash plus the saved source stat to prevent stale replacement.
A source backup is retained. Removing an asset archives its registry entry; it does
not silently erase the human's source file. `refresh` adopts human source edits
without changing asset identity and rejects divergent unpublished edits.
Native cell reads include `native-cell-ref-v1`; chunked text keeps its full-cell
reference and a separate full-text hash. Version 1.2.0 adds the native wiki and
citation integration described below. See [operation details and limits](wiki/Native-File-Assets.md).

Read/modify limits apply before decompression and XML parsing. XML entity expansion,
external-resource resolution, path traversal and ambiguous package members are
rejected. A successful structural check proves its stated preservation scope, not
rendered fidelity or formula correctness; agent semantic/visual review stays open.

Reference decisions: [openpyxl preservation limits](https://openpyxl.readthedocs.io/en/stable/tutorial.html),
[XlsxWriter formula semantics](https://xlsxwriter.readthedocs.io/working_with_formulas.html),
and [Microsoft worksheet structure](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-sheets).

## 2. Core Architecture

### Native evidence verification and wiki publication (v1.2.0)

Native cell references must be independently checkable against the immutable
registered revision: verify blob hash, worksheet identity/part/kind, cell address
and the full canonical cell representation hash. Report whether that revision is
the current managed head separately from reference validity. This verifies native
representation integrity, not formula evaluation, rendered layout or claim support.
Old valid references remain verifiable after updates or archival.

Portable native wiki exports retain these references independently of custom
citation display. `native/export_wiki` creates an immutable revision snapshot under
the caller's wiki directory, with a source attachment, canonical JSONL cell records,
one index and revision-pinned cell notes. Note names derive from asset/revision/native
locator, never display metadata. Native worksheet/cell locators feed citation display;
caller metadata cannot override them. XLSX/XLSM expose stored cells, while other
formats export an explicitly opaque source without fabricated semantic notes.

New revisions create separate snapshots, preserving old links and adjacent curated
notes. Repeating an export verifies its complete inventory and exact bytes. Modified,
unexpected or symlink entries fail closed without overwriting them. A different
citation presentation for the same revision requires a separate output directory;
this first version does not rewrite existing notes. Output has explicit cell/byte
limits and never silently truncates. Publication reserves a new directory exclusively
and writes the manifest last as its completion marker. Interrupted exports retain
their files and report reconciliation rather than claiming atomic directory visibility.
Source/store overlap is rejected. Formula, semantic and rendered review remain agent
responsibilities. Standards-aware academic formatting remains separate work.

### Existing PDF bundle publication integrity

Refreshing an existing generated PDF bundle requires its complete declared artifact
inventory, manifest self-hash and file hashes to verify. Modified, missing, extra or
symlink entries reject replacement; the matching doc_id/version marker alone is not
ownership evidence. Recheck the observed manifest token under an OS advisory lock
immediately before publication. Identical exports reuse existing files. Changed
exports retain the previous directory as a named backup and return its path, so
late writes through external editors' open handles are not deleted. An external
writer is not serialized by the MCP lock; conflicts retain recoverable files and
must not claim successful publication. Source-overlap protections remain enforced.

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
