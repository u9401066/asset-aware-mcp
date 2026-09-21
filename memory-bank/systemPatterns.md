# System Patterns

## ODS formula-cache traversal (Unreleased / 1.4.x)

The cell_record function builds identical locator/repetition/value/XML evidence
for both point reads and physical iteration. Cache invalidation reuses each visited
row/cell instead of rescanning its prefix. Reopened output is traversed once against
the complete planned locator map; table/range mismatches, duplicate or missing
targets fail. Physical repetitions stay compressed. No mutable XML index is cached.
Existing source/format/protection guards and complete before/after receipts remain.

Deterministic walk-budget regressions and published output/receipt SHA goldens
prove bounded traversal and exact evidence.5,000formulas improved19.5s→0.34s in
a local replay; environment-dependent speed is supplementary, not a semantic or
visual verdict. ODS MCP/evidence/Wiki wiring remains pending. Public1.4.0,next1.4.1.

## Immutable complete operation-result storage (Unreleased / 1.4.x)

Native operation results move out of the bounded asset metadata index into canonical
UTF-8 blobs under each owning asset's results directory. Domain references bind
SHA-256 and exact size; envelopes bind asset, history index, revision, parent and
operation. The repository checks all bindings on selected access. No full-history
hydration occurs on load/list. v1 inline data stays readable; successful writes
retain full results before publishing v2 metadata. Legacy writeback preflights
retention before replacing external source bytes; existing reconciliation remains.

Application receipt resolution uses the repository port for CSV, workbook, Word
tables/stories/notes, PDF annotations, images, rendition provenance and Wiki. API
records and historical evidence stay complete. Integrity never implies an Agent
semantic/visual verdict. Limits remain16MiB metadata and128MiB per full result.
Source versions/references are unchanged. Public1.4.0,next consolidated1.4.1.

## Native ODS adapter (Unreleased / 1.4.x; MCP integration pending)

Domain native_ods defines zero-based table/name/row/column locators and explicit
lexical values, independent of OOXML IDs and Excel name rules. Infrastructure
native_odf_package checks ZIP/MIME/manifest/XML budgets and untouched member bytes.
ODS reader/text/grid/editor modules retain compressed repetitions, distinguish
values/display/formulas, split only affected ranges, preserve cell/row attributes
and reopen output. Grid growth extends column declarations without expansion.

Actual Calc exposed stale cached formula results after a precedent edit. Invalidate
only typed result attributes, retaining expressions, paragraph formatting and cell
styles, and record full affected ranges. Cached display is explicitly unverified.
Actual Calc confirms numeric11.50, BooleanTRUE and string high; independent odfdo
3.25.0 confirms new/repeated native values. No new runtime dependency. Source ODF
version stays; new files use1.3 for tested Calc7.3 compatibility.

No MCP operation is advertised yet. Revision-bound application operations, evidence
unions/citations/Wiki, sheet/grid lifecycle and actual Codex SDK2 evaluation remain
required. Preserve the full all-format goal; public1.4.0,next consolidated1.4.1.

## Immutable raster projection archive (Unreleased / 1.4.x)

Domain NativeImageArchive defines bounded frame/catalog/preview retention without IO.
FileNativeImageArchive stores canonical content-addressed records beside immutable
native revisions; atomic writes, commit markers, operation locks, byte budgets,
full-reference/hash checks and symlink guards prevent partial or conflicting reuse.
NativeImageProjection coordinates source verification, current reads and explicitly
pinned historical reads. Production injects the archive into operations, evidence,
lineage and Wiki services. Captured previews bind full reference, size and color
policy; original rendering metadata remains. Current-decoder edit checks are
unchanged. Archive integrity is not fresh reproduction or semantic verification.

## Native delimited file boundary

Domain native_delimited defines explicit CSV/TSV dialects, string mutations and exact
field refs. Infrastructure native_text_encoding maps decoded chars to source bytes;
native_delimited_document parses/scans, native_delimited performs checked splices,
native_delimited_process isolates limits. Application operations coordinate one CAS;
evidence/selections/derivations/Wiki preserve revision and dialect. Presentation injects
the bounded adapter. No-op updates do not fabricate history; current receipt hash can
change when identical file bytes recur. Complete operation reads make this visible.

## Native PDF regions (Unreleased / 1.4.x)

Domain region references bind a full native page reference, explicit displayed
CropBox fractions and canonical source geometry. Application verifies parents,
serves complete records and delegates previews through the bounded PDF process.
PyMuPDF clips the displayed page; identity is independent of resolution/renderer.
Region refs participate in native verify, parsed selections and derivation ledgers.
Wiki attaches complete JSON, PNG, renderer metadata and exact source PDFs, with
selected citation display and explicit missing external bibliographic fields.
MCP verifies source/geometry only; Agent supplies transcription/meaning review.
Tests compare full-page raster crops, SDK2 actual images, history and Wiki integrity.
No version bump; public1.4.0 / Unreleased1.4.x; broad goal remains active.

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

## 2026-09-19 — Create native structures without flattening data

Table creation annotates an explicit range with new OOXML Table/relationship/type records. Existing cell payloads and styles survive; blank header fill/calculated replacement/totals are explicit. Read complete revision-pinned operation receipts and exact header XML; native/A2T historical evidence never auto-migrates. Agent reviews actual rendering and formula results.

## Native Table plans retain both original and intermediate cell state (2026-09-19)

Dedicated Table edits share generic geometry/protection guards, then coordinate
metadata and cell content in a private WorkbookPlan. Formula matching uses the
current intermediate names; public before receipts read original package cells.
These states must not be conflated. Rich header runs clone shared strings and retain
formatting. The application checks the combined complete reference/receipt budget
before the repository CAS, then exposes hash-pinned readback for Agent review.

## Native run preservation and complete schema pages (2026-09-18)

PPTX updates resolve revision-scoped slide/notes/shape/paragraph/run locators and
require original text hashes. Reopen bytes, compare requested values, restore only
those text nodes in memory and compare canonical XML; all untouched package members
must retain exact bytes. Group coordinates remain local and inherited formatting
is not inferred. Agents verify semantics, rendering and overflow. Wiki snapshots
use a distinct projection and preserve every raw package part.

Native contract delivery selects one operation or chunks canonical complete JSON.
Continuation uses the original full-schema SHA-256; field guards and discovery
share one registry. Validate semantic constraints at runtime, independent of the
JSON Schema's declarative constraints. Preserve existing format projection hashes.


> 📌 此檔案記錄專案中使用的模式和慣例，新模式出現時更新。

## Projection compatibility (2026-09-18)

Revision-bound evidence hashes use complete parsed representations; bounded text
previews carry the canonical reference separately. Upgrading an opaque DOCX wiki
to parsed block notes uses a new projection identity, preserving old snapshots and
links. Unrelated format outputs remain byte-identical under golden hash tests.
Package-part attachments preserve exact source bytes and their native path mapping;
parser-local filenames do not establish media relationships or extraction accuracy.

## Native document mutation pattern (2026-09-18)

Read immutable revision -> validate typed edits and unsupported features -> modify
only planned OOXML parts -> deterministic metadata repairs -> reopen and verify ->
CAS-publish managed revision. Explicit source writeback checks the tracked source,
retains its original inode as backup, and reports partial publication accurately.
OS advisory locks release on crash; human edits refresh the same asset ID only
when they cannot discard an unpublished managed revision.

## 🏗️ 架構模式

### DDD 分層架構
```
Presentation → Application → Domain ← Infrastructure
```
- Domain 層不依賴任何外層
- Repository Pattern 為唯一資料存取方式

### 憲法-子法層級
```
CONSTITUTION.md (最高原則)
  └── .github/bylaws/ (子法)
        └── .claude/skills/ (實施細則)
```

## 🛠️ 設計模式

### Repository Pattern
- 介面在 Domain 層定義
- 實作在 Infrastructure 層

### Strategy Pattern
- 用於取代複雜條件判斷
- 實例：ShippingStrategy, PaymentStrategy

### Command Pattern (CQRS)
- Commands: 寫入操作
- Queries: 讀取操作

### DFM Bridge Pattern (Docx ↔ A2T)
- **DfmTableBridge** 橋接 Docx 子系統與 A2T 子系統
- `docx_table_to_context` — 從 DocxIR 表格提取 headers + rows → A2T context
- `docx_table_from_context` — 從 A2T TableAsset 反向寫入 DocxIR
- 兩方向都保留型別安全（不直接耦合兩個 domain）

### Template-Based Rebuild Pattern (Docx)
- `ir_to_docx()` 複製原始 .docx ZIP 為模板
- 僅修改 `word/document.xml`
- 所有 media/styles/theme/fonts 由原檔保留 → 非文字保真率極高

### Intermediate Representation Pattern (DocxIR)
- docx → DocxIR → DFM → Agent 編輯 → DFM → DocxIR → docx
- IR 保留：preserved_parts, assets, styles, runs, checksum
- DFM 是人/Agent 可讀的 Markdown 視圖

### Multi-Dimensional Validation Pattern (DocxValidator)
- 6 個獨立維度比較（結構/文字/格式/表格/媒體/樣式）
- 每維度 0–100 分 + 加權總分
- 產出 Agent 可讀 Markdown 報告（emoji 等級）

## 業務流程模式

### A2T 2.0 (Anything to Table) 工作流
1. **Plan**: `plan_table_schema` - AI 驅動的結構發想。
2. **Draft**: `create_table_draft` - 建立持久化草稿，支援斷點續作。
3. **Batch Add**: `add_rows_to_draft` - 分批寫入數據，優化 Token 使用。
4. **Commit**: `commit_draft_to_table` - 正式轉檔為 JSON/MD/XLSX。

### Asset-Aware ETL 模式
1. **Extract**: 使用 PyMuPDF 提取原始 Markdown 與圖片。
2. **Parse**: 識別表格、章節與圖片位置。
3. **Manifest**: 生成結構化清單供 Agent 導航。
4. **Index**: 注入 LightRAG 建立知識圖譜。

## 命名慣例

| 類型 | 慣例 | 範例 |
|------|------|------|
| Entity | 名詞單數 | `User`, `Order` |
| Value Object | 描述性名詞 | `Email`, `Money` |
| Repository | `I{Entity}Repository` | `IUserRepository` |
| Use Case | 動詞 + 名詞 | `CreateOrder` |
| Domain Event | 過去式 | `OrderCreated` |

## 📚 程式碼慣例

### Python
- 使用 `snake_case` 命名
- 檔案名全小寫
- 類別使用 `PascalCase`
- 優先使用 type hints

### 測試
- 測試檔案以 `test_` 開頭
- 測試類別以 `Test` 開頭
- 使用 pytest markers 分類

---
*Last updated: 2025-12-15*
