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

### Canonical A2T citation readback (1.4.x development)

Keep table_cite get as the compatible cell/row/table summary. Add read for one
cell selected by table_id, column_name and row_id (preferred) or row_index.
Return the full persisted CellCitation, including every AssetRef locator, exact
quote/hash, CRAAP metadata, notes and confidence, alongside the current cell value
and stable table/row/column binding. A missing citation is explicit null. Unknown
rows/columns are errors. Do not invent missing source locators or quality scores.

Serialize the a2t-cell-citation-v1 record as sorted compact UTF-8 JSON, preserving
Unicode exactly. The SHA-256 binds the value, citation and cell identity, excluding
the mutable row index. The a2t-citation-page-v1 envelope carries citation_sha256,
text_excerpt, total character length, half-open character range and next offset.
text_limit is 1..4000 (default 4000); the encoded envelope must fit the configured
MCP response cap. Reject a cap too small for any progress. Bound each complete
representation to 16 MiB UTF-8 and reject unsupported non-JSON/non-finite values.
For text_offset > 0, require citation_sha256 from the first page; reject mismatched
hashes, out-of-range offsets or a different cell. Agents concatenate all excerpts
at one hash, verify UTF-8 SHA-256, then parse the complete JSON. Partial excerpts
are transport fragments, never shortened canonical AssetRefs.

Reads do not change table/source artifacts. Hash equality proves consistent stored
content, not source validity, authenticity, extraction accuracy or semantic support.
Source verification and rendered/semantic review remain separate. Tests must cover
long/multiple refs, Unicode/control characters, small response caps, stale paging,
row deletion/reindexing, nonexistent addresses, absent citations and unchanged
artifacts. Real SDK2 and opt-in Codex PDF workflows must read every final Reading
cell's references through MCP, with independent audit of returned locators/content.

### Starting coverage and completion evidence

A2T operation results identify the resolved stable row and index, including the
pre-deletion index for deleted rows. A row_id takes precedence over an input index;
never display the unused -1/default or a conflicting input index as the operated
target. Cell-history labels use the validated stable row ID when supplied. This
changes result metadata/presentation only; row identity, data, citation invalidation
and history semantics remain unchanged. Regress after deleting an earlier row.

### Native PPTX shape structure (1.4.x development)

Add add_pptx_shapes and delete_pptx_shapes under document/native, preserving the
existing native-contract-v2 discovery flow. Both require asset_id and expected_revision,
stage managed revisions through CAS, and never implicitly write the human source.

add_pptx_shapes accepts up to 100 typed textbox additions. Each supplies a container
(slide_id, part, region, optional group_shape_id) and the existing textbox model
(local EMU geometry, explicit paragraphs/runs/styles). Resolve the container through
the presentation relationships, allocate unused unsigned 32-bit shape IDs in its
part, and append shapes at the top of z-order before extLst. Generate only the new
textbox XML using python-pptx's public API; do not round-trip the existing package
through that library. Preserve group transforms without automatically resizing or
repositioning existing children. Bound aggregate additions to 20,000 runs / 4 MiB
UTF-8 text. Return generated locators for reading and subsequent edits.

delete_pptx_shapes accepts up to 100 existing NativePptxReference objects. Require
matching asset/revision and exact full representation hashes. Reject duplicates
and overlapping ancestor/descendant requests. A group deletion includes its subtree.
Reject removal when remaining known connector, timing or build references target
removed shape IDs; deleting a dependent connector in the same batch is allowed.
Shape deletion retains package relationships and related media/embedding parts;
it is not secure content erasure. Slide creation/removal, non-text shape creation,
animation editing and interpretation of arbitrary extension dependencies remain
separate capabilities, not implied by these operations.

For either operation, validate package inventory and untouched member bytes,
read back the intended structural change, and reverse only the planned shape
changes in an independent parsed result to compare all other XML canonically.
Preserve existing immutable references/wiki snapshots and their exact old hashes.
Reject stale, signed/protected, strict/macro/legacy, ambiguous or invalid packages.
Report known mechanical check coverage separately from agent review of meaning,
rendering, z-order, overflow, inherited styles and unmodeled dependencies.
Tests cover groups/notes, text formatting, connector/timing dependencies, retained
charts/media/foreign parts, ID exhaustion/collisions, stale refs/CAS, tampered output,
reopened presentations, historical evidence/wiki and real SDK2 writeback/backups.

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

### Codex-driven PDF collaboration verification

Exercise the current checkout through a real Codex CLI MCP connection, in an
isolated synthetic-data workspace, without changing user MCP configuration.
Keep the expected transcription outside the agent workspace. Capture JSONL tool
events and independently compare persisted outputs with fixture truth; an agent's
success statement or a passing SDK transport test is insufficient evidence.

Cover digital, image-only and mixed/rotated PDF pages. Require source preflight,
ingestion, actual MCP image delivery, agent transcription, structured table CRUD,
source references and reusable asset export. Image-only pages must not acquire
fabricated text-span citations. Distinguish editing derived structured data from
rewriting the original PDF; preserve original hashes throughout the workflow.

Use deterministic SDK regressions for mechanical invariants and opt-in Codex
runs for perception/tool-use evaluation. The latter requires an authenticated
Codex CLI and may incur model usage; it must not silently run during pytest or
claim universal OCR accuracy from a small synthetic corpus. Record skipped,
failed, unperformed and successful checks separately.

Figure crop coordinates use unrotated cropbox-relative page space, consistently
with PDF preflight and native image locators. Intersect/pad in that space, then
transform the clip into the rotated rendering space. Rotated/cropped full-page
scans must retain the complete visible page; pixel comparisons against a full
page render and partial-region crops cover all right-angle rotations.
An image-only ingestion may legitimately have figures without section blocks.
Section-navigation errors must point agents to the document asset inventory and
image fetch path, rather than requiring a particular held extraction backend.

### Scalable native operation discovery (v1.4.0)

The SDK tool input retains the full typed NativeDocumentRequest schema. Native
contract discovery must not duplicate an ever-growing schema until the response
cap silently truncates it. Introduce native-contract-v2 with capabilities,
operation names, a canonical schema digest and an explicit schema delivery mode.
Small schemas may remain inline; large schemas are obtained via native op=schema
using bounded text_offset/text_limit chunks. Each page identifies the full schema
hash; subsequent pages require that hash and reject a changed installed contract.
Agents assemble the complete JSON and verify its hash before interpreting it.

contract(for_op=...) returns the declared schema for one operation, including only
its supported fields and transitive definitions, required/non-null inputs and the
unchanged field constraints. The operation field registry is shared with runtime
validation, so discovery cannot drift from required/unused field checks. Complete
request schemas remain available via schema without for_op. Runtime semantic
validators are still authoritative; JSON Schema is not a claim of exhaustive
validation of XML text, file states or preservation constraints.

Existing native operation inputs and aliases remain accepted. Discovery clients
must inspect schema_delivery instead of assuming schema is always inline; use the
returned schema_request or select for_op. This explicit migration replaces the old
oversized response failure, without raising global output limits or weakening any
validation keyword. The normal MCP tools/list schema remains complete.

### Native PPTX collaboration (v1.4.0)

Treat the original presentation as an immutable native root with revision-scoped
slides, shape trees, text runs, table cells, notes and exact package-part relations.
Resolve slide IDs through presentation relationships rather than assuming that
slide order determines package filenames. Preserve nested group hierarchy and
local coordinates; do not claim computed visual bounds or inherited formatting.
Native read/decompose returns bounded views and complete evidence representations;
unknown objects retain source XML and package attachments for agent interpretation.

Create independent PPTX documents using the existing python-pptx dependency.
Updates to existing presentations must operate on precise native targets, preserving
run/paragraph properties, layouts, masters, themes, media, charts and unrelated
package parts. Broad .text assignment can clear runs and is unsuitable for checked
preservation. Reopen and compare results before a managed revision CAS; source
publish/writeback remains explicit. Signed/protected, ambiguous or unsupported
operations must be explained without silently dropping features.

Component evidence binds original revision and locators; wiki projection retains
full records, exact source/package attachments and existing snapshots. Structural
CRUD and complete rendered/semantic review remain part of the broad objective;
each operation advertises its actual scope. MCP performs necessary deterministic
checks; agents review text meaning, overflow, layout, animations and object behavior.

Reference decisions: [python-pptx shape hierarchy](https://python-pptx.readthedocs.io/en/latest/user/understanding-shapes.html),
[text frames, paragraphs and runs](https://python-pptx.readthedocs.io/en/latest/user/text.html),
and [PresentationML package structure](https://learn.microsoft.com/en-us/office/open-xml/presentation/structure-of-a-presentationml-document).

Implemented operations: create_pptx (presentation), read_pptx (asset_id with
revision/offset/limit), read_pptx_shape (asset_id/pptx_locator with JSON text pages),
update_pptx (asset_id/expected_revision/pptx_edits), native verify and export_wiki.
Locators carry slide_id, native part, slide/notes region and shape_id. Text edit
locators additionally carry paragraph/run indices and paired optional table row/
column. Regular runs are indexed independently of fields and line-break nodes;
text hashes are required preconditions. Tabs/newlines, field editing, merged-cell
continuations and structural edits are rejected. Creation supports explicit
text boxes, paragraphs, styled runs, dimensions in EMU and notes.

PPTX wiki projection pptx-shapes-v1 retains complete shape JSON/XML and every
original package part; previous opaque snapshots remain separate. Existing v1.2
XLSX and v1.3 DOCX artifact digests are regression guarded. Source/revision/CAS
checks are mechanical; visual bounds, inherited formatting, text overflow and
semantic accuracy require agent review. Legacy .ppt, macro .pptm and strict
PresentationML are outside the native editor's current scope.


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


## Native PDF page assets and structural CRUD (1.4.x development)

Goal: extend the immutable native asset registry to PDF pages, including native
read/decompose/render, independent creation, page insertion/copy/deletion/reorder,
geometry updates, explicit source writeback and immutable wiki evidence. This is
page-level editing, not arbitrary semantic text replacement or secure redaction.
MCP performs source/version, object-graph, known dependency and readback checks;
agents verify meaning, layout, accessibility, forms and viewer-specific behavior.

Use pikepdf/QPDF for object-aware edits and PyMuPDF for independent text/render
inspection. Preserve page identities during reorder by detach/reinsert, never
page assignment. Typed references bind asset ID, immutable revision, page index,
object/generation locator and canonical representation digest. Reject mismatched
or duplicate mutation targets and CAS conflicts. Source files change only through
existing guarded writeback with backups; historical refs remain valid.

Verification must account for source pages with text, images, vectors, crop/rotate,
annotations, forms, hyperlinks, bookmarks, metadata, attachments and inherited
page attributes. Object graph hashing must be bounded and stable across output
object renumbering, preserving stream data and shared references. Compare all
existing page content and document-level objects except planned changes, then
reopen with an independent parser. Document metadata is not silently imported by
page copying. Any unsupported dependency must be reported or rejected before
commit, not flattened or dropped. Encrypted/signed/repaired inputs require explicit
unsupported diagnostics rather than implicit protection removal or repair.

All operations use bounded schemas/pages and explicit preservation/review scopes.
Pikepdf compatibility, universal lock security, Python 3.10 and SDK2 transport must
be tested before enabling the adapter. Required tests include positive mixed
content CRUD, rendering/text preservation, internal links/forms/page labels,
negative corruption/dependency/stale writes, prior evidence/wiki stability, and
actual Codex MCP use. Keep public version 1.4.0 and accumulate Unreleased for 1.4.x.


PDF copying must also check annotation graph backreferences. The initial pinned
pikepdf form-aware copy experiment duplicated note/popup graph objects and broke
the original reciprocal identity even though rendered pixels matched. A supported
deterministic repair may relink copied Popup/Parent/IRT pointers using the exact
source-to-destination annotation correspondence, followed by full graph equality.
Do not weaken the graph check merely to accept the upstream copy. Form fields must
remain registered in AcroForm and retain their source values/resources.

Native PDF worker results must use the existing private, atomic, size-bounded
MessagePack handoff used by PDF extraction. A pipe readability check does not
bound a subsequent full-frame receive; partial writes must not bypass the overall
worker deadline. Serialize NativeEditResult as plain data, then validate it in the
parent. Reject missing/partial/corrupt/oversized results and reap children before
removing their private temporary directory.

## Native PPTX image assets and picture CRUD (1.4.x development)

The next cross-format capability is moving immutable human image assets into and
out of native presentations. Keep public 1.4.0, accumulate Unreleased, and keep
MCP necessary checks distinct from the agent's complete semantic/visual review.

- A native-file-ref-v1 identifies complete immutable file bytes by asset ID and
  revision SHA-256. It does not assert image meaning. Register remains the entry
  point for human PNG/JPEG files; canonical file verification uses managed bytes.
- add_pptx_pictures accepts revision-bound image references and existing slide,
  notes or nonzero-extent group containers. Use local EMU rectangles and explicit
  contain/cover/stretch fitting. Embed exact original image bytes, not a re-encoded
  copy. Persist source refs in operation history and expose new shape locators.
- replace_pptx_pictures targets complete current-revision shape references and
  new image references. Preserve the existing picture mapping (geometry, rotation,
  flips, crop, effects and z-order) by changing only the image relationship ID.
  This policy is explicit; new image aspect ratios may alter the displayed content
  and require agent review. Shared original image parts/relationships stay intact;
  never overwrite a shared part when replacing one picture. Reject external-linked,
  ambiguous and alternate-representation image targets rather than retaining a
  competing image rendition silently.
- read_pptx_picture resolves the pinned picture's internal image relationship,
  returns exact media hash/metadata and a real bounded MCP image preview. The
  preview is the embedded image, not a rendering of the slide/crop/effects.
  extract_pptx_picture creates an independent image asset from the exact embedded
  bytes with originating PPTX revision/shape/media lineage in its first history.
- Existing delete_pptx_shapes handles picture deletion and retains media; it is
  not secure erasure. Old presentation evidence and wiki attachments remain valid.
  Do not change the released shape-v1 representation/hash schema to add metadata.
- Preserve original package members byte-for-byte except planned owner XML,
  owner relationships and content types; retain ZIP member metadata. Add only
  explicitly planned media/relationship members. Compare exact new bytes,
  validate relationships/content types and reverse XML changes to prove the rest
  of each touched part is unchanged. Reopen independently with python-pptx in tests.
- Validate PNG/JPEG signatures/content, decompressed dimensions and resource budgets;
  reject multi-frame and EXIF-oriented inputs that cannot be faithfully displayed
  without an explicit transform. Keep immutable originals. Add corruption, shared-
  media, group/notes, stale/CAS/source backup, evidence/wiki and real SDK2 tests.
- Upstream public references: python-pptx Shapes.add_picture accepts width/height
  and preserves aspect when only one dimension is supplied; Image exposes exact
  blob, content type, dimensions and digest. Pillow provides verification and
  decompression-bomb limits. Use these libraries behind native ports, not a
  load-and-save of the user's whole presentation.

### Native PPTX table creation (Unreleased, 1.4.x)

`add_pptx_tables` accepts asset_id, expected_revision and 1–100 `pptx_tables`.
Each item identifies an existing slide/notes/nonzero-group container and a table
with local EMU left/top, explicit column_widths/row_heights, a rectangular cells
matrix, nonoverlapping inclusive merge rectangles, name and description. Width
and height equal the sums of column/row dimensions. Cells contain structured
paragraphs/runs, horizontal/vertical alignment, margins, optional RGB fill/text
colors. Numbers and formulas are literal display text, never recalculated.

The destination tableStyles relationship and default style GUID are resolved and
explicitly applied to the new table. Without that relationship no style ID is
invented. No foreign style/media relationships or parts are imported. Explicit first/last
row/column and banding switches control theme roles. Merges are established before
writing cell content. Covered cells must use the empty/default cell request so
content/formatting cannot silently disappear. Every new table is read back against
its requested grid, text, direct formatting and merge map. Scoped shape-tree
insertion retains exact existing package parts and reverses new nodes to verify
unmodified XML. MCP stages immutable versions with CAS; source writeback is explicit.

Read full tables through read_pptx_shape, edit native cell runs with update_pptx,
delete whole tables with full current shape refs via delete_pptx_shapes, and retain
historical evidence/wiki snapshots. Individual grid row/column insertion/deletion
and edits to existing merge maps remain follow-up work. Agent reviews actual slide
rendering, inherited table style, overflow, data interpretation and accessibility.
Budget: at most 100 rows/columns per table; 10,000 cells, 20,000 runs and 4 MiB UTF-8
text per batch. Per dimension and summed table extent stay within 100,000,000 EMU.

Implementation references: [python-pptx table concepts](https://python-pptx.readthedocs.io/en/latest/user/table.html)
and [public table API](https://python-pptx.readthedocs.io/en/latest/api/table.html).

#### Native citation display schema discovery

Actual Codex scanned-table run 01 correctly transcribed the image but tried to put
source proof objects into citation_contract. The runtime rejected those fields and
the agent recovered. NativeDocumentRequest now must expose a typed union of a
preset selector (`source`, `author-year`, `numeric`) and CitationFormatContract,
including required inline_template/reference_template and bounded allowed template
fields. Valid existing JSON inputs remain accepted; native wiki passes the typed
model's JSON representation to the existing resolver. Canonical source references
are separate from display contracts and cannot be overridden by formatting input.

### Native derivation ledger (Unreleased, 1.4.x)

An agent may record that a revision-pinned native component/file was derived from
one or more other native references. `record_derivation` verifies the target and
every source before storing a bounded, content-addressed assertion. Supported
references are existing file/cell/DOCX-block/PPTX-shape/PDF-page references; no
invented locator or document text is accepted as proof. Activity, agent identity
and semantic/layout/formula review fields are caller assertions, never authenticated
identity or machine proof of meaning. Historical targets/sources remain explicit;
links never migrate automatically when a document changes.

`read_derivations` returns the complete append-only ledger as canonical JSON pages
pinned by `derivations_sha256`; continuations require that hash. Recording and
`retract_derivation` require `expected_derivations_sha256` from a prior read. A new
record can atomically supersede an active record on the same target asset. Retraction
and supersession preserve prior assertions. `verify_derivation` separately reports
active status, immutable-reference validity, current managed revisions and the
agent's review claims. It does not assert external-file freshness or semantic support.

Store the ledger separately from native file bytes, under the existing per-asset
operation lock with atomic writes and digest compare-and-swap. Bound each assertion
to 64 unique sources, each ledger to 1,000 events and 16 MiB. Validate event replay,
record hashes and target identity on load. Reject archived-target mutations,
self-references, stale writes, unknown/inactive replacements and malformed records.
No cross-asset transaction is required: references address immutable revisions.

Wiki export pins the ledger digest into a distinct snapshot identity, preserves
the full ledger for audit, and adds human-readable wikilink notes plus exact source
attachments for active assertions targeting the exported file revision. Verify
those references again before publishing; preserve existing snapshots/curated notes.
Retractions create new snapshots without rewriting old exports. Citation display
templates stay separate from canonical provenance. Existing no-ledger snapshots
retain their identities and byte format. Output byte/artifact budgets still apply.

References: [W3C PROV-O derivation](https://www.w3.org/TR/prov-o/#Derivation) and
[Docling Graph provenance ledger](https://github.com/docling-project/docling-graph/blob/main/docs/fundamentals/graph-management/provenance.md).
This API uses those concepts; it does not claim complete PROV-O/RDF conformance.


### Native PPTX table grid editing (Unreleased, 1.4.x)

`update_pptx_table_grid` accepts `asset_id`, `expected_revision` and
`pptx_table_grid`: one full current shape `reference` plus 1..32 sequential
`edits`. Each edit is `insert`, `delete` or `resize`, with `axis` (`row` or
`column`) and zero-based `index`. Insert/resize specify EMU `sizes`; delete
specifies `count`. Insert may specify a row-major `cells` matrix (same typed
cell creation contract); omitted cells are blank. Indices apply to the result
of the preceding edit. No dimension may become empty or exceed 100 entries,
10,000 grid cells, 100,000,000 EMU total or the existing text/run budgets.

Insertions inside an existing merged rectangle extend it; insertions at its
start move it. New covered cells must be default/empty. Deletion shrinks a
partially surviving merge; if its anchor is deleted, retain the original
anchor content/format at the new top-left cell. Hidden content in a promoted
covered cell is rejected instead of discarded. Fully deleted merges disappear.
Resize preserves content and merge topology. Existing cell XML, row/column
metadata, table style, relationships and unrelated package bytes are retained
except requested deletion, merge flags and explicit anchor promotion. Shape
position remains fixed; its local extent follows the new grid totals, preserving
any existing grid-to-frame scale. Full shape hash, source revision/CAS and
archive/signature/protection checks precede mutation. Independently check final
grid dimensions/merges and serialized shape, restore the old shape to verify
unchanged surrounding XML, and compare every untouched package member.

References remain revision scoped; old evidence still verifies, but cell
coordinates and derivation assertions do not automatically migrate. Return
compact edit/promotion counts and a current-revision read request. Rendering,
banding/inherited styles, text overflow, semantics and unmodeled dependencies
remain Agent review. Package retention/deletion is not secure erasure.

Reference design: [python-pptx merge grid semantics](https://python-pptx.readthedocs.io/en/latest/user/table.html)
and [DrawingML row structure](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.drawing.tablerow).
