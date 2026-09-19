# System Architect

## Workbook rendition architecture (Unreleased / 1.4.x)

NativeWorkbookRendition supplies explicit rendering intent; NativeWorkbookRenderer
is an optional domain port. LibreOfficeWorkbookRenderer checks source/package
resources, uses a private Calc profile and bounded converter, and validates the
PDF through ProcessNativePdf. NativeRenditionOperations creates a separate native
PDF with an immutable creation receipt and exact source file reference. Paged
read_rendition works without the converter and never migrates maps to edited PDF
bytes. Existing PDF image/evidence/CRUD APIs reuse this frozen output. Native Wiki
adds exact input XLSX and receipt as mechanical lineage, separate from Agent
review or the derivation ledger. Source workbook caches/history remain unchanged.

## 2026-09-19 — Native Table totals lifecycle

Domain NativeTotalsRowChange is a discriminated add/remove intent on NativeTableUpdate.
TableTotalsTransition coordinates roles, hidden definitions, direct cell styles and
old/new source footprints inside the existing private Table patch and one CAS.
Retained formula operands resolve through bounded static selectors with an explicit
current-row context; other worksheet formulas keep their structured references.
The shared tokenizer shadows @ before quoted qualifiers while preserving all spans.
Existing complete XML/cell/untouched-part readback and review budgets remain in force.

## 2026-09-19 — Native Table creation adapter

NativeTableCreate/NativeTableCreateAdapter remain domain-only. NativeWorkbookOperations coordinates bounded review and one CAS; NativeWorkbookTableCreate delegates geometry/name/style checks, package registration, existing Table cell writers and common native_table_finish verification. Composition root injects creation separately from existing Table editing; contract advertises only configured capability.

## 2026-09-19 — Native Table specialized edit port

NativeTableUpdate/NativeTableEditAdapter live in domain. NativeWorkbookOperations
dispatches the configured port under existing repository CAS and complete paged
readback; capabilities advertise actual adapter availability. Infrastructure
NativeWorkbookTableEdit coordinates TableCellWriter, column metadata and source
checks through WorkbookPlan. GridTables accepts explicit identity changes for
structured-reference reuse. Header inventory exposes cell/resolved shared-string
XML separately from historical cell evidence. No dependency or version changes.
The application checks combined reference inventory/receipt capacity before CAS;
the infrastructure keeps original cell roots for truthful before-state receipts.

## 2026-09-19 — Explicit Table expansion composition

NativeGridEdit owns typed optional NativeTableExpansion part/expected_ref intent.
NativeWorkbookGrid delegates selected membership to native_grid_table_expansion;
TableGridEdit coordinates table column metadata, filters and formula generation.
GridTables tracks final generated-cell coordinates across all sequential transforms.
Existing reference/dependency/cache/package checks and original native CAS remain.
NativeWorkbookStructure adds a read-only inventory adapter for complete Table parts;
it does not require enabling edits or rewriting XML encoding.
NativeTableGridApply resolves native_generated values only against this operation's
new generated-cell map, compares every final typed value and unedited format, and
stores resolved values beside immutable A2T intent. Generic cell edit guards remain.
SDK2 and actual-Codex fixtures independently inspect native packages, full paged
reads, historical references, frozen/live snapshots and Wiki bytes.

## 2026-09-19 structural A2T application

Domain native_table_grid computes identity-based insert/delete proposals and validates
explicit worksheet_grid correspondence. TableContext/table_state retain column IDs
without rewriting legacy immutable snapshots. NativeTableGridApply composes grid,
cell and range ports, checks destination values and unchanged parsed/style records,
and returns combined receipts. NativeTableOperations retains ownership of frozen
input storage and one native CAS. The composition root reuses its configured grid
adapter; contract table_grid_apply_enabled exposes the capability. No file formats
or native package parsing enter the domain layer. Native Table expansion/specialized
editing and axis move semantics remain separate capabilities.

## 2026-09-19 native worksheet grid editing

Domain NativeGridUpdate and NativeGridAdapter define sequential typed row/column
edits, one-based coordinates and explicit inheritance/merge/object policies.
NativeWorkbookGrid edits original OOXML parts; focused modules own address/formula
transforms, tables and filters, sparse geometry, drawing/note objects, named source
resolution and serialized invariants. NativeWorkbookOperations coordinates exact
revision checks and repository CAS; the composition root injects the adapter.
The contract advertises workbook_grid_enabled and pages complete schemas when
response overhead would exceed the transport budget. Native content revisions
remain immutable; current operation receipts are also required when identical
bytes recur. Structural A2T mapping and Agent semantic/visual review stay separate.

## 2026-09-19 native/A2T bridge

Domain native_table_workspace defines typed values, exact worksheet/range binding
and range/workspace ports. Shared table_state codec preserves legacy persistence
fields plus native binding. Infrastructure NativeWorkbookRange returns dense native
records; FileTableWorkspaceReader reads fresh bounded regular files. Application
NativeTableOperations orchestrates projection/read/apply/create and immutable input
snapshots through native repository CAS. Existing TableService retains persistence
ownership; the composition root injects it and the fresh reader. MCP table_data
accepts JSON typed values. Editing original worksheets uses the existing checked
package editor; separate XLSX creation does not claim source layout preservation.

## 2026-09-19 — Optional native presentation rendering port

NativePresentationRenderer is separate from editing adapters. The application binds
explicit revision/slide keys; infrastructure owns private LibreOffice profiles,
conversion/process limits and isolated PDF rendering. Contract configuration is
separate from runtime availability. Static output is an Agent inspection artifact,
not a machine visual-verification verdict. Source and native revisions stay immutable.

## 2026-09-19 — native slide structure

Domain slide keys and insertion models bind stable slide IDs/parts and explicit layouts.
Layout discovery traverses all presentation masters. The builder uses public python-pptx
layout/placeholder APIs but returns only new slide nodes, never a resaved source deck.
Infrastructure applies narrow slide-list/relationship/content-type deltas, reserves all
existing/detached relationship targets and overrides, repairs known count properties,
and independently reopens the result. Deletion retains orphan parts and rejects known
incoming references, sections and index ranges. Application shares native revision CAS,
historical evidence, wiki and guarded source writeback. No new top-level MCP tool or
dependency. Actual Codex audits read original ZIP identities independently of python-pptx
in-memory renaming and compare all intermediate artifacts and prior complete readbacks.

## 2026-09-19 — native table merge/split

Domain native_pptx_grid adds typed merge/split to the existing discriminated edit union.
Infrastructure native_pptx_grid_merges validates body/content/merge topology and moves
exact paragraphs within the same package part, retaining relationship IDs. Existing
grid orchestration performs per-step budget/topology checks and independent serialized
shape/package checks before managed CAS publication. No new dependencies or top-level
MCP operations. The opt-in Codex harness independently opens each intermediate PPTX
and checks source cells, rich paragraph XML, merge/frame geometry and full references.

## 2026-09-18 — native derivation ledger

Extract stable file/cell/DOCX model definitions into native_asset_models; native_assets
keeps backward-compatible public re-exports and request schemas without import cycles.
Domain derivation models pin full reference unions, review claims and validated event
replay. Infrastructure stores bounded append-only metadata under the existing native
asset lock with CAS and atomic publication, separate from file bytes. Application
verifies endpoints, pages ledger/proof responses and augments wiki builders with a
ledger-pinned identity, full history, readable notes and exact source attachments.
Presentation wires the repository into the existing SDK2 document/native surface.
No new tool name or dependency; regular callers without a ledger retain wiki identity.


## 2026-09-18 — native table composition and citation schema

Domain native_pptx_table models define EMU grids, cells, merges and aggregate budgets.
Infrastructure builds scratch table nodes, resolves destination default style and
independently compares serialized grids/text/direct formatting/merge maps to input.
Reuse scoped shape insertion/deletion guards; table creation never resaves the original
presentation with python-pptx or imports foreign parts. Application shares existing
managed PPTX CAS/backup boundaries; full shape evidence/wiki remains compatible.
Native citation_contract now uses CitationFormatPreset | CitationFormatContract;
NativeWikiService resolves its JSON projection. Formatting never stores source proofs.


## 2026-09-18 — native picture composition and extraction

Domain: native file references and typed picture create/replace requests.
Infrastructure: bounded PNG/JPEG validation, scoped package additions, scratch-node
building, media/relationship plans and independently reopened XML/byte checks.
Application: managed picture dispatch, immutable image-source reads, CAS mutation,
source lineage on new image assets and whole-file reference verification.
Presentation: reuse bounded MCP PNG response for embedded raster previews.
No image conversion or full slide renderer; source writes retain existing guards.


## 2026-09-18 — Native PDF page assets and evidence

Domain defines strict page locators/references, mutually exclusive blank/copy inputs,
geometry edits and NativePdfAdapter. Infrastructure separates bounded QPDF graphs,
package rules, form/annotation integration, mutation checks and spawn worker. The
worker reuses PDF extraction private atomic MessagePack, validates NativeEditResult
on return and cleans children/files on all paths. Application performs source loads,
aggregate budgets, asset/revision checks, CAS commit, evidence binding and distinct
pdf-pages-v1 immutable wiki projection. Repository creation accepts an optional edit
report so a newly composed file retains exact source-copy lineage from revision one.
Presentation returns TextContent + actual PNG ImageContent through existing document
facade; the public tool count is unchanged. Existing PDF ETL/A2T remains the separate
image-to-structured-data path. Source backups and wiki note protection remain shared.

## 2026-09-18 — native PPTX shape CRUD boundaries

Domain adds typed shape containers/additions and reuses native shape references.
Infrastructure splits isolated textbox generation from scoped shape-tree edits,
ID/reference checks and reversible XML verification. Application routes additions
and deletions through the same immutable revision/CAS repository, exposes follow-up
read requests and preserves explicit writeback. Existing evidence and wiki ports
remain compatible. No new dependency or presentation-layer tool is introduced.

## 2026-09-18 — native PPTX and scalable discovery

Domain native_pptx defines strict creation, native shape/run locators, text edits,
references and an adapter port. Infrastructure resolves PresentationML relationships,
parses explicit shape structure and preserves exact OOXML members during run edits;
python-pptx supplies independent creation. Application coordinates immutable versions,
CAS, chunked component JSON, evidence verification and pptx-shapes-v1 wiki snapshots.
Schema discovery shares the runtime operation field registry and uses hash-pinned
JSON pages. Presentation keeps one typed document facade and the complete SDK schema.


## 2026-09-18 — native DOCX bridge

- Domain defines typed NativeDocxEdit and adapter/workspace ports without IO.
  Application NativeDocxBridge reuses DocxService in a private session; it is a
  blocking adapter invoked in the existing MCP native worker thread. The private
  event loop only adapts the established asynchronous service entry points.
- FileNativeDocxWorkspaces owns temporary files, bounded OOXML inspection and
  preservation comparison. Input/output packages and unchanged bytes are checked;
  signed/protected packages require another explicit supported workflow. Private
  workspaces are cleaned on success/failure and are not persistent asset locations.
- NativeDocumentService remains responsible for immutable revision selection,
  expected-revision CAS and explicit source writeback. It injects the DOCX adapter;
  capability/contract serialization was extracted to native_document_contract.py
  to keep the coordinator within module/class limits. Contract titles are compacted
  as annotations only, preserving actual input fields named title and all constraints.
- DFM block IDs/locators remain revision-scoped. The next component layer now reuses
  full block serialization through native_docx_records.py, adds native DOCX block
  verification and bounded native_docx_operations.py reads. Exact package parts
  come from the workspace port, without application filesystem access.
- NativeDocxWikiContent specializes the existing wiki serializer under a distinct
  docx-blocks-v1 snapshot identity. Legacy output bytes stay unchanged; the existing
  publisher owns all IO/no-overwrite checks. Original part mapping and exact bytes
  preserve unparsed content without claiming extraction completeness.


> 📌 此檔案記錄重大架構決策，架構變更時更新。

## Native evidence integrity (post-1.1.0)

`NativeEvidenceService` owns canonical cell references and immutable-revision
verification. Native document orchestration delegates to it; spreadsheet locator
resolution remains inside the format adapter. Validity, managed-head freshness,
external-source freshness and agent semantic/visual/formula review are distinct.

## 2026-09-18 — native files and spreadsheets (unreleased)

- Domain `native_assets.py` defines strict file/revision/source identities, typed
  edits, operation requests and repository/format ports, without filesystem IO.
- `NativeDocumentService` composes those ports; `document(op="native")` dispatches
  off the async event loop. The SDK 2 public tool count remains unchanged.
- Infrastructure separates immutable registry metadata, bounded file IO/source
  publication, OOXML packages, spreadsheet readers, edit guards, repair plans and
  transactional editors. New source files stay below repository size limits.
- Revisions retain full native bytes. Canonical cell representations carry native
  locators and hashes; chunked excerpts explicitly retain complete-value identity.
  Native wiki/citation adapters remain separate upcoming work.
- Agent verification remains semantic/visual/formula-aware. Byte-preservation and
  read-back checks do not claim full rendered fidelity.

## 🌐 系統架構圖

```
┌─────────────────────────────────────────────┐
│              專案模板結構                      │
├─────────────────────────────────────────────┤
│  🏔️ 規則層                                        │
│  ┌─────────────┐                                  │
│  │ CONSTITUTION │ ───┐                             │
│  └─────────────┘     │                             │
│        │            ▼                             │
│        │     ┌────────────┐                        │
│        ├────▶│  Bylaws   │                        │
│        │     └────────────┘                        │
│        │            │                             │
│        ▼            ▼                             │
│  ┌───────────────────────┐                      │
│  │    Claude Skills      │                      │
│  └───────────────────────┘                      │
├─────────────────────────────────────────────┤
│  🧠 記憶層                                        │
│  ┌───────────────────────┐                      │
│  │     Memory Bank       │                      │
│  │  (7 markdown files)   │                      │
│  └───────────────────────┘                      │
├─────────────────────────────────────────────┤
│  ⚙️ 工具層                                        │
│  ┌────────┐ ┌─────────┐ ┌─────────┐           │
│  │ CI/CD  │ │ Testing │ │ Linting │           │
│  └────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────┘
```

## 🏛️ 架構決策紀錄

### ADR-001: 採用憲法-子法層級架構

**日期**：2025-12-15

**背景**：需要一個清晰的規則層級系統

**決定**：採用憲法 → 子法 → Skills 三層結構

**理由**：
- 最高原則集中在 CONSTITUTION.md
- 細則可在 bylaws/ 擴展
- Skills 專注於操作程序

### ADR-002: DDD + DAL 獨立

**日期**：2025-12-15

**背景**：確保業務邏輯與資料存取分離

**決定**：Repository 介面在 Domain，實作在 Infrastructure

**理由**：
- 提高可測試性
- Domain 不依賴資料庫技術
- 可替換儲存實作

### ADR-003: uv 優先套件管理

**日期**：2025-12-15

**背景**：Python 套件管理工具選擇

**決定**：優先使用 uv，後備 pip

**理由**：
- 比 pip 快 10-100 倍
- 原生支援 lockfile
- 與 pip 完全相容

### ADR-004: DFM (Docx-Flavored Markdown) 即時編輯架構

**日期**：2026-02-11

**背景**：AI Agent 無法直接讀寫 .docx 二進位格式，需要中間表示

**決定**：設計 DFM 格式 + DocxIR 中間層，實現 docx ↔ IR ↔ DFM 完整往返

**理由**：
- Agent 天然理解 Markdown，DFM 是最小學習成本的編輯界面
- IR 保留完整格式/樣式/媒體資訊，DFM 只暴露可編輯的文字結構
- Template-based rebuild（複製原始 zip → 只改 document.xml）保證非文字部分 100% 保真
- DocxValidator 6 維度驗證彌補 Agent 無法目視確認的缺陷

**架構**：
```
.docx → DocxAdapter.docx_to_ir() → DocxIR
  DocxIR → DfmRenderer.render() → DFM (Markdown)
  DFM (edited) → DfmParser.parse() → DocxIR (updated)
  DocxIR → DocxAdapter.ir_to_docx() → .docx (rebuilt)

DocxValidator.validate(original, rebuilt) → ValidationReport (6D)
DfmTableBridge: DocxIR.tables ↔ A2T TableAsset
```

## 📦 元件圖

```
.claude/skills/          # 12 個 Skills
├── git-precommit/       # 編排器
├── ddd-architect/       # 架構
├── code-refactor/       # 重構
├── code-reviewer/       # 審查
├── test-generator/      # 測試
├── memory-updater/      # 記憶
├── memory-checkpoint/   # 檢查點
├── readme-updater/      # README
├── changelog-updater/   # CHANGELOG
├── roadmap-updater/     # ROADMAP
├── project-init/        # 初始化
└── git-doc-updater/     # 文檔更新

.github/bylaws/          # 4 個子法
├── ddd-architecture.md
├── git-workflow.md
├── memory-bank.md
└── python-environment.md
```

### ADR-005: 官方 MCP SDK 2 為唯一 runtime contract

**日期**：2026-08-13

**決定**：使用官方 `mcp>=2,<3` 的 `MCPServer`、runtime-injected `Context` 與
SDK 2 client。移除 FastMCP／SDK v1 fallback；`legacy` 僅保留 SDK 2 上的舊
tool-name inventory。

**理由**：避免公開 schema 洩漏 context、依賴 private registry，以及兩套
protocol/runtime 路徑造成 release drift。

### ADR-006: 文件輸出採可驗證 agent asset contract

**日期**：2026-08-13

**決定**：canonical document artifacts 經 segmentation/citation index 輸出
`agent-asset-bundle-v1`；record 必須帶 source identity、stable locator、hash
與 citation state。Bundle 使用 document-scoped staging/atomic replace，並可
產生 portable Foam subtree。

**理由**：agent 與 LLM wiki 需要可重用資產，而不只是一次性的分析報告；
引用必須能偵測 stale source 並 fail closed。

---
*Last updated: 2026-08-13*



## Architectural Decisions

- 以 PyMuPDF 作為安全、快速的預設 ETL；PyMuPDF4LLM／Docling 為可選的
  structured extractors，MinerU／Marker 維持 security hold
- 使用官方 MCP Python SDK 2 `MCPServer`；不提供 SDK v1／FastMCP fallback
- 本地優先存儲策略，所有資產保留在 ./data 目錄下



## Design Considerations

- 採用 DDD 架構確保業務邏輯與技術細節分離
- 使用非同步 Job 處理大型 PDF 以避免 MCP 逾時
- Manifest-first 策略：Agent 應先讀取清單再精準取用資產
- 支援 Base64 圖片傳輸以配合 Vision AI 分析能力



## Components

### Presentation Layer (MCPServer)

以官方 SDK 2 實作 MCP tools/resources，並透過公開 registry API 管理 balanced、
compact 與 legacy tool-name surfaces。

**Responsibilities:**

- 定義 ingest_documents, fetch_document_asset 等工具
- 提供 document://{id}/outline 等動態資源
- 處理 MCP 請求與回應格式轉換

### Application Layer (Services)

協調領域對象執行業務流程。處理非同步 Job 狀態。

**Responsibilities:**

- DocumentService: 協調 ETL 流程
- JobService: 管理非同步任務狀態
- AssetService: 檢索與過濾文件資產

### Domain Layer (Core)

核心業務邏輯與實體定義。定義 Repository 介面。

**Responsibilities:**

- 定義 DocumentManifest 實體與 Asset 值物件
- 定義 PDFExtractorInterface 與 KnowledgeGraphInterface 介面
- 實作 ManifestGenerator 領域服務

### Infrastructure Layer (Adapters)

外部技術實作。包含 PDF 解析與知識圖譜。

**Responsibilities:**

- PyMuPDFPreflight: 在隔離 process 中分類 PDF、產生 OCR reasons 與 route
- PyMuPDF/Docling adapters: 預設快速 extraction 與可選高精度 structured route
- LightRAGAdapter: 實作知識圖譜索引與查詢
- FileStorage: 處理本地檔案系統的讀寫與圖片儲存

## 2026-09-18 — cross-format CRUD and evidence library

Authoritative baseline is origin/main e612d20, published 1.0.1. Original master
worktree remains at 0.9.0 with pre-existing user changes; do not reset it.
Worktree: /home/eric/workspace251226/asset-aware-mcp-agent-assets;
branch: feat/agent-asset-contracts.

The latest explicit user reply confirms: MCP provides necessary source/version,
format-preservation and operation-result checks; the agent owns complete semantic
and visual verification and coordinates corrections. This clarification overrides
the earlier complete-MCP-validation wording. Deterministic checks remain enforced
on every supported write; do not claim full fidelity from structural checks alone.
Full scope is tracked in docs/spec.md and ROADMAP.md; a milestone is not completion.

Next: implement versioned citation presentation contracts in existing evidence
and portable asset exports, then native capabilities/CRUD and inspectable operation results.
README/Pages/GitHub metadata/labels/MEM and staged commits/push/releases are
explicitly authorized. Full release gates remain required before tagging.

Domain owns pure contracts; application binds display to evidence; infrastructure
owns native format IO. Citation formatting never mutates source provenance.


## 2026-09-19 — native PPTX table grid edits

- Domain: native_pptx_grid typed sequential insert/delete/resize with full shape refs.
- Infrastructure: native_pptx_grid_model validates/retains DrawingML nodes;
  native_pptx_grid_mutations transforms dimensions/cells/merged rectangles;
  native_pptx_grid scopes writes and verifies immutable evidence, exact package
  inventory, unchanged surrounding XML and serialized planned shape.
- Application: NativePptxOperations enforces asset/revision/archive checks before
  the existing atomic repository commit; source writeback remains separate.
- Tests: native and real SDK2 checks plus opt-in Codex --grid scans/table flow;
  independent auditor checks all five intermediate grids and surviving cell XML.
