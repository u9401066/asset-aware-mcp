/* global marked, mermaid */

const DOC_PAGES = window.ASSET_AWARE_DOC_PAGES || [];
const embeddedContent = window.ASSET_AWARE_DOC_PAGE_CONTENT || {};
const DOC_STATS = window.ASSET_AWARE_DOC_STATS || {
  version: "unknown",
  tools: 30,
  resources: 13,
  endpoints: 43,
};
const markdownRenderer = window.marked;
const LANGUAGE_STORAGE_KEY = "asset-aware-docs-language";
const SUPPORTED_LANGUAGES = ["en", "zh"];
const NAV_GROUPS = [
  "start",
  "user",
  "evidence",
  "operations",
  "reference",
  "developer",
];

const GROUP_COPY = {
  en: {
    start: "Start Here",
    user: "Document Workflows",
    evidence: "Evidence & Knowledge",
    operations: "Operations",
    reference: "Reference",
    developer: "Maintainers",
  },
  zh: {
    start: "開始",
    user: "文件流程",
    evidence: "證據與知識庫",
    operations: "維運與上線",
    reference: "參考",
    developer: "開發者與維護者",
  },
};

const UI_COPY = {
  en: {
    menu: "Menu",
    navProduct: "Product",
    navWorkflow: "Workflow",
    navCapabilities: "Capabilities",
    navTools: "Tools",
    navDevelopment: "Develop",
    navDocs: "Docs",
    heroTitle: "Turn documents into<br />reusable agent assets",
    heroLead: "Read PDF assets, edit DOCX, create independent tables and build wikilink evidence libraries. MCP SDK 2 preserves source identity throughout the workflow.",
    start: "Get started",
    viewGithub: "View GitHub",
    toolsLabel: "tools",
    demoLabel: "Illustrative flow · PDF preflight / DOCX DFM ingest",
    workflowTitle: "One verifiable document workflow",
    workflowLead: "Inspect the source, then extract, verify, and export it. Every stage has a clear responsibility boundary.",
    wfPreflight: "Preflight",
    wfPreflightDesc: "Classify PDF pages and OCR needs",
    wfIngest: "Ingest",
    wfIngestDesc: "Background jobs keep stdio responsive",
    wfExtract: "Extract",
    wfExtractDesc: "Text, tables, figures, and sections",
    wfVerify: "Verify",
    wfVerifyDesc: "Locator, exact quote, and SHA-256",
    wfExport: "Export",
    wfExportDesc: "Deterministic agent asset bundle",
    wfWiki: "Build wiki",
    wfWikiDesc: "Foam notes and optional LightRAG",
    minimalFlow: "Minimal workflow (MCP call example)",
    capabilitiesTitle: "Capabilities compose into an evidence layer",
    capabilitiesLead: "One source becomes assets an agent can read, query, verify, and recombine.",
    readFlows: "Read complete workflows",
    documentEntry: "Document inputs",
    structuredExtraction: "Structured extraction",
    sourceToEvidence: "Document → evidence layer",
    text: "Text",
    table: "Table",
    figure: "Figure",
    section: "Section",
    reversibleEdit: "Reversible edits with stale-write guards",
    toolExplorerTitle: "MCP tools, grouped by task",
    toolExplorerLead: "Choose a task, then an operation. You do not need to memorize 30 names.",
    fullReference: "Full MCP reference",
    toolChooser: "Tool chooser",
    searchTools: "Search MCP tools",
    module: "Module",
    mainInputs: "Primary inputs",
    outcome: "Outcome",
    callExample: "Call example",
    readToolContract: "Read the complete tool contract",
    installTitle: "From install to the first asset export",
    installLead: "Choose a launch path; detailed client configuration and verification stay in the setup guide.",
    installGuide: "Complete install guide",
    installVsCode: "Install from Marketplace and use the native MCP provider",
    openMarketplace: "Open Marketplace",
    engineeringTitle: "Protect the evidence contract while developing and releasing",
    engineeringLead: "Features, dependencies, and website changes pass the same focused regressions and release gates.",
    progressOnly: "handles progress only; operational logs go to stderr.",
    immutableSource: "Immutable sources",
    sourceContract: "Preserve source SHA, mtime, locators, and citation hashes.",
    regressionFirst: "Regression first",
    regressionDesc: "Every behavior fix includes a focused regression.",
    releaseChain: "Auditable release chain",
    releaseSequence: "Release sequence (evidence-oriented)",
    securityPosture: "Current security posture",
    largeSpanTitle: "Large-span transport contract",
    largeSpanCopy: "Large spans use an explicit asset-ref-preview-v1 over MCP with canonical_asset_ref=false. The exact quote and self-verifying AssetRef remain in persisted bundles; Unreleased inspect_etl_source also reads complete references through hash paging without exporting.",
    githubBand: "Code, issues, and releases live on GitHub",
    openGithub: "Open GitHub",
    viewReleases: "View releases",
    reportIssue: "Report an issue",
    developerGuide: "Developer guide",
    footerCopy: "Built for citation-ready document workflows.",
    documentation: "Documentation",
    backHome: "Back to product home",
    docsIssue: "Docs problem? Report an issue",
    formatCheck: "Format checks",
    readable: "Readable text",
    pageStructure: "Page structure",
    assetIntegrity: "Asset integrity",
    textSpans: "Text spans",
    tables: "Tables",
    figures: "Figures",
    method: "Method",
    conclusion: "Conclusion",
  },
  zh: {
    menu: "選單",
    navProduct: "產品",
    navWorkflow: "流程",
    navCapabilities: "功能",
    navTools: "工具",
    navDevelopment: "開發",
    navDocs: "文件",
    heroTitle: "把文件變成<br />Agent 可重用的資產",
    heroLead: "讀取 PDF 資產、編修 DOCX、獨立建立表格，再延伸成 wikilink 證據庫。MCP SDK 2 讓每一步保留可追溯來源。",
    start: "開始使用",
    viewGithub: "檢視 GitHub",
    toolsLabel: "tools",
    demoLabel: "示意流程 · PDF preflight / DOCX DFM ingest",
    workflowTitle: "一條可驗證的文件工作流",
    workflowLead: "先檢查來源，再拆解、驗證與匯出；每一步都有清楚的責任邊界。",
    wfPreflight: "預檢",
    wfPreflightDesc: "分類 PDF 頁面與 OCR 需求",
    wfIngest: "攝入",
    wfIngestDesc: "背景 job 保持 stdio 回應",
    wfExtract: "拆解",
    wfExtractDesc: "文字、表格、圖像與 sections",
    wfVerify: "驗證",
    wfVerifyDesc: "locator、exact quote 與 SHA-256",
    wfExport: "匯出",
    wfExportDesc: "deterministic agent asset bundle",
    wfWiki: "建庫",
    wfWikiDesc: "Foam notes 與可選 LightRAG",
    minimalFlow: "最小工作流（MCP 呼叫示例）",
    capabilitiesTitle: "功能不是清單，是可組合的證據層",
    capabilitiesLead: "同一份來源被拆成 agent 能讀、能查、能驗證、能重新組合的資產。",
    readFlows: "閱讀完整流程",
    documentEntry: "文件入口",
    structuredExtraction: "結構拆解",
    sourceToEvidence: "文件 → 證據層",
    text: "文字",
    table: "表格",
    figure: "圖像",
    section: "章節",
    reversibleEdit: "可逆編輯與 stale-write 防護",
    toolExplorerTitle: "個 MCP tools，按任務分組",
    toolExplorerLead: "先選任務，再看 operation；不用背 30 個名字。",
    fullReference: "完整 MCP reference",
    toolChooser: "工具選擇器",
    searchTools: "搜尋 MCP tools",
    module: "Module",
    mainInputs: "主要輸入",
    outcome: "Outcome",
    callExample: "呼叫範例",
    readToolContract: "閱讀完整工具 contract",
    installTitle: "從安裝到第一份 asset export",
    installLead: "選擇一條啟動路徑；完整 client 設定與驗證步驟保留在安裝指南。",
    installGuide: "完整安裝指南",
    installVsCode: "從 Marketplace 安裝 VSIX，使用原生 MCP provider",
    openMarketplace: "開啟 Marketplace",
    engineeringTitle: "開發與發布，先守住證據契約",
    engineeringLead: "功能、依賴與網站更新都進同一套 focused regression 與 release gates。",
    progressOnly: "只處理 progress；operational logs 走 stderr。",
    immutableSource: "來源不可變",
    sourceContract: "保留 source SHA、mtime、locator 與 citation hash。",
    regressionFirst: "回歸先行",
    regressionDesc: "每個行為修正都附 focused regression。",
    releaseChain: "可稽核發布鏈",
    releaseSequence: "發布序列（證據導向）",
    securityPosture: "目前安全策略",
    largeSpanTitle: "Large-span transport contract",
    largeSpanCopy: "大型 span 的 MCP 回應只提供 asset-ref-preview-v1，且 canonical_asset_ref=false；完整 exact quote 與可自我驗證 AssetRef 留在持久化 bundle；Unreleased 另可用 inspect_etl_source 分頁讀取，不必先匯出。",
    githubBand: "程式碼、issue 與 release 都在 GitHub",
    openGithub: "開啟 GitHub",
    viewReleases: "查看 Releases",
    reportIssue: "回報 Issue",
    developerGuide: "開發指南",
    footerCopy: "Built for citation-ready document workflows.",
    documentation: "文件導覽",
    backHome: "返回產品首頁",
    docsIssue: "文件有問題？回報 Issue",
    formatCheck: "格式檢查",
    readable: "可讀性",
    pageStructure: "頁面結構",
    assetIntegrity: "資源完整",
    textSpans: "文字 spans",
    tables: "表格",
    figures: "圖像",
    method: "方法",
    conclusion: "結論",
  },
};

const ENGLISH_PAGE_CONTENT = Object.freeze({
  "getting-started": `## Start the runtime
Install the pinned package with uv, then run the doctor and tool-list diagnostics before connecting a client. The default runtime exposes the balanced 30-tool MCP SDK 2 surface.

## Verify a first workflow
Use PDF preflight only for PDF inputs, then ingest in the background and export reusable agent assets.`,
  "vs-code-extension": `## Install and connect
The VS Code extension provides the native MCP provider and can configure Cline, Codex, and Copilot without replacing unrelated entries. Managed launches use the extension package version and trusted workspace state.

## Verify preservation
Confirm activation, provider discovery, and preservation of custom settings before relying on an updated VSIX.`,
  "native-file-assets": `## Native documents and versioned files — v1.4.0

### Native PDF annotations (Unreleased)

Discover pdf_annotations_enabled and assemble complete contract/schema pages. read_pdf_annotations pins asset_id/revision; read_pdf_annotation adds pdf_annotation_locator. Follow every annotation.text_excerpt at one text_sha256 for complete catalogs, records and operation receipts. Identity combines revision, page, zero-based annotation-array index and native object/generation; names alone are not identities.

update_pdf_annotations takes expected_revision and pdf_annotations_update.edits: 1..32 create/update/delete operations, each existing target once at the input revision. Create takes a full page_reference and typed appearance. Update/delete use the whole annotation reference. Text uses point; FreeText/Square/Circle use rect; Line/PolyLine/Polygon use vertices; Ink uses strokes; Highlight/Underline/StrikeOut/Squiggly use quads in UL/UR/LL/LR order. Positions are displayed rotated CropBox fractions, top-left origin, 0–1. Unused style fields are rejected.

Omitted metadata stays; null removes a key. Metadata edits preserve foreign appearance bytes. Visible FreeText changes require explicit same-kind replace_appearance. Annotation Contents is authored commentary, not the highlighted source quotation. FreeText may also enter page text extraction; inspect the separate annotation records. Unknown kinds, Links and Widgets are readable without implying arbitrary edit support.

Delete requires scope:annotation_and_owned_popup. Surviving replies must be explicitly included. Shared arrays/objects, locks, signatures, Widget/standalone Popup edits and unsupported rich formatting retain guards. Exact native inverse checks, serialized readback and body pixels precede commit. Annotation-free disposable reader copies prevent Highlight transparency from changing the body comparison; exact comparisons and source bytes remain intact.

Read the complete review_request, current references and actual affected page PNGs. Agents review glyphs, clipping, geometry, meaning and viewer behavior. Full refs support verify, selections, derivations and CSL/custom citations. Old evidence never migrates; deletion is not secure erasure. Annotated PDFs use pdf-annotations-v1 with exact PDF/page previews, annotation-catalog.json, annotations.jsonl and linked notes. Unannotated PDFs retain byte-identical legacy output and all historical Wikis remain preserved.

See the [full annotation contract and upstream references](https://github.com/u9401066/asset-aware-mcp/blob/main/docs/specs/native-pdf-annotations.md). Public release: 1.4.0; next consolidated patch: 1.4.1, with no per-feature bump.

### Native Word footnotes and endnotes (Unreleased)

Discover docx_notes_enabled; read_docx supplies notes_request. read_docx_notes pins asset_id/revision and pages a complete catalog, independent catalog_sha256 and latest operation_result through note. Assemble every text_excerpt at one text_sha256. Roles follow actual w:type, not conventional IDs. Native IDs are distinct from displayed numbering and page locations.

read_docx_note adds docx_note_locator with part/note_kind/note_id and returns full XML, literal text nodes with their SHA256, body references and native-docx-note-ref-v1. update_docx_note requires expected_revision, the full docx_note_reference and docx_note_update with locator, shared_scope:all_native_references and sequential set_text/insert_blocks/delete_blocks edits. Native reference marks remain intact; special separator definitions are readable evidence but not ordinary editable note content.

update_docx_notes pins expected_revision and docx_notes_update.expected_catalog_sha256, with explicit definitions_and_native_body_references scope and 1..32 sequential create/delete edits. Creation supplies footnote/endnote kind, part and typed blocks, optionally a free positive native ID. Existing notes use the linked main-document part. First creation supplies a new bounded ASCII XML path under word/ and creates the relationship, content type and special separator definitions. The anchor takes full main-XML text_path, Unicode character_offset within one w:t, and that text node's returned text_sha256 as expected_text_sha256.

Insertion splits a native run while retaining literal text, direct formatting and other children. The new definition precedes the next existing body reference's definition; all preexisting IDs and sibling order stay intact. Appending a definition at the end reproduced a real Writer note/content mismatch in our fixture, so actual numbering and bindings are reviewed as well as native XML.

Deletion requires locator, expected_note_sha256 and literal_body_text:preserve. It removes normal definitions and editable main-body native references; retained references elsewhere and unsupported ranges/controls/revisions block the operation. Ordinary body text and custom literal marks remain for explicit Agent correction. Containers, relationships and orphan media stay; this is not secure erasure.

Read complete review_request receipts, every affected note and all actual page PNGs. MCP checks source/version/structure and deliverable receipts; Agent reviews semantics, placement, displayed numbering, fields and custom marks. Historical references remain verifiable and work with selections, derivations, CSL and custom citation templates. The distinct docx-notes-v1 Wiki contains complete notes.jsonl/note-catalog.json, stories, original DOCX and package parts; documents without notes retain legacy snapshots unchanged. A note adapter without the optional header/footer story adapter uses the distinct docx-notes-content-v1 projection, preventing different content from sharing one snapshot identity.

The identity/reference model draws on the official [Open XML FootnoteReference](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.footnotereference?view=openxml-3.0.1) documentation and [eigenpal/docx-editor note nodes](https://github.com/eigenpal/docx-editor/blob/main/packages/core/src/store/package/note-nodes.ts), without importing code or a new dependency. Public1.4.0; next consolidated1.4.1.

Explicit remap_ids edits inside update_docx_notes accept the current main-linked part, note_kind and mappings:[{note_id:11,new_note_id:1}]. They atomically update normal definitions and all editable main-body references, including ID swaps. Unlisted IDs, definition order, special roles, literal content/marks and formatting stay intact. Duplicate old IDs, target collisions, special definitions and references outside that scope reject the edit. New IDs are positive. Complete receipts retain old/new locators, definition hashes and reference changes; read new references before further edits. Old references remain tied to their historical revision.

Controlled Writer 7.3.7/24.2.7 tests exposed different note-import behavior: definition order alone was insufficient. Explicitly aligning IDs with body order corrected both tested readers. This changes the managed DOCX and exported file; previews render its actual bytes. Agent review of all pages, bindings and meaning remains required.

### Native Word story lifecycle (Unreleased)

Discover docx_story_structure_enabled. read_docx_story_structure pins asset_id/revision and returns the complete catalog, independent catalog_sha256 and latest operation_result in hash-paged story_structure JSON. Assemble every text_excerpt at one text_sha256 before editing.

update_docx_story_structure requires expected_revision and docx_story_structure: expected_catalog_sha256, explicit scope sections_and_following_inheritors, and 1..32 sequential edits. create supplies a new part, story_kind and typed paragraph/table blocks. clone supplies a new part, source_part and source_part_sha256. bind takes zero-based section_index, story_kind, variant default/first/even, and a part or null. delete takes part and expected_part_sha256 after all bindings are removed. first_page takes section_index/enabled; even_pages takes document-level enabled. Both options affect headers and footers.

Null binding resumes inheritance; it does not produce blank content. Create/bind a blank paragraph definition to suppress inherited content. Following sections inherit the change until another direct declaration, so explicitly rebind a successor to its original part when needed. Disabling first/even options retains their definitions.

Clones preserve native runs, tables, field caches and media bytes, relocate relationship targets and allocate distinct supported paragraph/drawing identities. Known ranges, controls, revisions, notes and embedded dependencies require further identity-aware clone support and are explicitly rejected. New names are bounded ASCII XML paths under word/, without _rels directories, collisions or existing dangling targets.

Deletion checks retained parts and historical section XML, removes the definition and its own relationships, and retains referenced media; this is not secure erasure. Complete receipts must be deliverable before atomic commit. Source bytes/mtime, unrelated XML/parts, historical references, selections and Wikis remain intact. No-op batches add no history. Agent reviews every full receipt/story and actual page. Footnote/endnote CRUD uses the separate operations above; Microsoft Word parity remains further work. Public1.4.0; next consolidated1.4.1.

### Native Word header/footer stories (Unreleased)

Discover docx_stories_enabled. read_docx_stories pins asset_id/revision and returns complete section definitions, inherited/shared bindings and header/footer parts based on actual content types and relationships. Never infer variants from filenames. Legacy DFM header/footer fields are abbreviated projections; read_docx supplies header_footer_request for complete native discovery while retaining historical references.

read_docx_story adds docx_story_part and returns complete XML, literal text_nodes paths, direct block indices, relationships and native-docx-story-ref-v1 evidence. Both readers page their story object with text_offset/text_limit; follow every next_text_offset at one UTF-8 text_sha256. Bindings include dormant/unbound definitions; unknown switches are null. This is a definition map, not a rendered page map.

update_docx_story requires expected_revision, the complete docx_story_reference and docx_story_update containing part, explicit shared_scope all_sections_using_part and sequential edits. set_text(path,text) changes an existing w:t; insert_blocks(index,blocks) adds typed native paragraphs/tables; delete_blocks(index,count) removes complete direct blocks. Paths and indices are zero-based in each intermediate XML tree. Editing a shared part affects every linked section and dormant definition; it never silently detaches a section.

Native runs/styles, unrelated XML and other package parts remain intact. Field, range, revision and bound/locked-control checks apply. Literal text includes field caches and alternate/revision branches, not evaluated results or reading order. Read every review_request page and the complete operation_result, then inspect every affected actual PNG. A recurring file SHA may have a newer receipt; verify the complete text hash. No-op edits create no history entry.

Historical story references participate in verification, JSON selections, derivations and custom/CSL citations. Wikis containing stories use the distinct docx-stories-v1 projection with stories.jsonl, story-catalog.json, the original DOCX and every package part. Legacy snapshots remain intact. Whole-definition lifecycle and section links use the operations above; remaining identity-aware clone dependencies and footnote/endnote editing require further work. Public 1.4.0; next consolidated patch 1.4.1.

### Native Word table pagination (Unreleased)

Exact row heights can hide text that remains in the native file. Discover docx_table_layout_enabled, read the complete table and actual pages, then use update_docx_table_grid with the full reference, expected_revision and sequential edits.

set_header_rows takes count: a contiguous prefix from the first row, with zero disabling repetition. A boundary cannot cut through an existing vertical merge. set_row_layout takes zero-based index/count and at least height or split. height.rule is auto, at_least, exact or inherit; only at_least/exact require value_twips. split is allow, prevent or inherit.

Omitted settings stay intact; inherit removes a direct property so styles/defaults apply. auto requests content-driven height. Exact heights can still clip text; prevent keeps a row together when it fits, but oversized rows can span pages. Read row_layout and repeat_header_prefix_length; repeat_header_rows also retains noncontiguous declarations, which do not extend the repeating prefix. Unknown split values remain unknown.

MCP verifies requested property readback and unchanged native content, other properties, versions and package bytes before an atomic commit. Full before/after operation_result is paged through review_request. Relevant tracked row properties require a revision-aware workflow; pure layout edits retain fields, while structural dependency checks remain in place. Review every new actual page. Historical refs, source files and Wiki snapshots stay intact. This does not establish Microsoft Word rendering parity. Public1.4.0 / Unreleased1.4.x.

### Native Word table grids (Unreleased)

Discover docx_table_grid_enabled. read_docx_table requires asset_id, revision and a complete docx_table_reference from read_docx. Follow every next_text_offset at one text_sha256 to inspect the layout grid, physical cells, omitted positions, merges and full native XML. This is a table block reference, not a new cell evidence type; DFM character offsets are not grid coordinates.

update_docx_table_grid pins expected_revision and docx_table_grid.reference. Supply 1–32 sequential edits using zero-based coordinates in each intermediate grid. insert/resize use axis, index and sizes_twips; row heights are minimums and columns become fixed widths (20 twips per point). Inserted cells use the existing rich Word cell schema. delete uses axis/index/count and must retain a row and column. merge uses an inclusive rectangle plus require_empty or append_blocks: the latter moves complete paragraphs and nested tables in physical row-major order. split addresses the merge anchor; content stays there and exposed cells are blank.

Insertion inside merges expands them; covered input positions must be default empty. Omitted positions remain omitted. Deleting a surviving vertical merge's anchor promotes its full content. New rows are not repeated headers; merges cannot cross header/body boundaries. Column edits set grid/cell/table widths; inherited styles, nested-table overflow and pagination still require actual page review.

Mutation summaries are bounded; full operation_result is in paged table reads. The latest matching history entry supplies the receipt; repeated file SHAs may have newer receipts, so verify complete text_sha256. No-op changes add no history or receipt.

One batch commits atomically after structural, serialized XML and untouched-part checks. Follow the complete review_request, then render_docx_page through all actual pages. Historical references, source bytes and Wiki snapshots remain unchanged. Coverage follows tables exposed by the current extractor: body/nested tables and ordinary unlocked body controls. Bound controls, range/field/revision dependencies and unextracted stories need dedicated handling. MCP checks mechanics; Agent checks meaning and visual layout. No Microsoft Word fidelity claim. Public1.4.0 / Unreleased1.4.x.

### Checked historical PDF syntax (Unreleased)

Some historical scans contain duplicate stream Length declarations. Native PDF reads accept this case only after independently checking every original dictionary value is the same direct integer and matches the raw stream bytes and boundaries. Listings and complete page records retain parser_checks with policy, counts and proof digest; source bytes remain unchanged. Conflicting/indirect lengths, other parser warnings and unsupported dictionaries still require separate handling.

Requested page edits or copies serialize a single Length and record canonicalized_equal_duplicate_stream_lengths in repairs, retaining existing graph/render checks and immutable source history. Agents still review actual glyphs and meaning. See [real PDF validation](#/release-testing). Public1.4.0 / Unreleased1.4.x.

### Native CSV/TSV files (Unreleased)

Register human CSV/TSV files or create independent string tables with create_delimited. Query delimited_enabled and contract.for_op. read_delimited and read_delimited_cell require asset_id/revision; delimited_row/column are zero-based logical coordinates. Assemble all text_excerpt chunks at one text_sha256 and verify UTF-8 SHA-256. Fields retain values, raw spelling, byte/character/physical-line spans, context and full native-delimited-cell-ref-v1 references. No header, number or formula inference.

update_delimited pins expected_revision. set_cells uses full field references; insert_rows requires index/rows/record_separator; delete_rows uses index/count. insert_column takes one value per existing row; delete_columns uses index/count. Ragged rows remain ragged; positions must exist in every affected row. One column may be inserted per call; row edits/column deletion allow up to 1,024 positions, with 1,000 replacements and a 16 MiB / 20,000 field-row budget.

Byte splices preserve untouched encoding, quoting, escape spelling and mixed CRLF/LF/CR. New rows use explicit separators. Appending after an unterminated row records a separator repair. Deleting every column retains zero-field rows; a surviving sole empty field receives required quoting. Reparse all values and row correspondence before one commit. Follow review_request for the full receipt. Byte-identical updates return complete no-change receipts without a history entry; recurring file SHAs may have newer receipts, so restart if text_sha256 changes.

CSV defaults comma, TSV tab, with double-quote quoting. delimited_dialect explicitly controls delimiter/quotechar/escapechar/doublequote/encoding. UTF BOMs are detected, otherwise UTF-8; UTF-16 LE/BE, CP950, CP1252 and Latin-1 are available. Custom dialects/encodings must accompany later reads, edits and Wiki export; review_request includes the resolved dialect. NUL values survive Python3.10 and newer runtimes with original bytes/positions intact. No sniffing or replacement decoding. Bounded child processes isolate csv.field_size_limit.

verify, parsed selections and derivations accept full fields. Wiki binds its projection to the resolved dialect and keeps exact CSV/TSV bytes, structure, JSONL, notes and custom citations. Historical refs never migrate; curated notes remain. Agent chooses PDF regions, views actual PNGs, transcribes strings and checks downstream meaning/rendering. Source refresh, publish and backed-up writeback retain their existing checks. Based on [Python csv](https://docs.python.org/3/library/csv.html); [CleverCSV](https://github.com/alan-turing-institute/CleverCSV) informs dialect discovery, not authoritative writes. Public1.4.0 / Unreleased1.4.x.

### PDF region evidence (Unreleased)

read_pdf_region connects an explicitly selected scanned cell to its typed target value. Query pdf_regions_enabled and contract.for_op, read the complete PDF page record, then pass its full reference and pdf_region={rect:[0.2,0.25,0.4,0.3]}. Fractions address the displayed CropBox AFTER rotation, from the top-left, right/down positive, within 0–1. This differs from native bottom-left PDF crop coordinates and unrotated text-block coordinates.

The response contains a complete region record, actual MCP PNG, image hash and renderer/geometry metadata. Re-read using the full native-pdf-region-ref-v1 without overriding its selector. render_size64–2048 changes image detail without changing evidence identity. Empty/out-of-page rectangles and unbounded zoom fail explicitly. Source bytes, crop/rotation and managed history stay unchanged.

verify checks source/geometry; read_selection can select region JSON values. Agent views the image, checks glyph coverage, transcribes typed cells and records an explicit derivation per region/cell. Later edits never migrate assertions. Wiki retains region JSON/PNG/render metadata, source PDFs and wikilinks. The chosen citation contract receives page and rectangle in locator. External sources do not borrow target authors/year/reference numbers; missing fields produce citation_unavailable while preserving the full reference and selected contract.

Partial scan resampling, renderer/fonts and preview detail may change pixels; region identity is not a universal pixel identity or OCR verdict. Agent reviews meaning, layout and results. See [evaluation](#/release-testing). Public1.4.0 / Unreleased1.4.x.


### Worksheet layout correction (Unreleased)

Read an actual workbook PDF, identify clipping, then correct native dimensions and render a new revision. When worksheet_layout_enabled is advertised, read_worksheet_layout requires asset_id, revision and worksheet_key. Assemble every JSON chunk at one text_sha256.

update_worksheet_layout requires expected_revision and worksheet_layout with worksheet plus 1–32 sequential edits. Each edit has axis (row/column), one-based at and count (default1, maximum1024). Choose height_points or width_ooxml, reset_size, and/or hidden. Raw OOXML column width includes font padding and differs from Excel's displayed character count. Reset removes manual dimensions; it does not calculate text AutoFit. For example, row1 height_points36 and column1 width_ooxml30 are explicit choices for Agent review.

Cell identities, content, styles, merged ranges and Tables stay intact. DrawingML and legacy notes follow authored move/resize anchoring with complete geometry receipts. Nondefault font geometry needs explicit calibration; collapsed objects reject unless preserve_size is requested. Worksheet protection must permit formatting the affected axes. Existing workbook and unsupported-object checks still apply.

Width or visibility changes can affect formulas, so formula/chart caches are invalidated and recalculation requested. Follow the complete review_request, then create_workbook_rendition with recalculate and inspect actual pages. Source files, historical PDFs and evidence remain unchanged. MCP mechanical checks do not certify layout or Excel fidelity. Public1.4.0 / Unreleased1.4.x.

### Workbook renditions (Unreleased)

create_workbook_rendition converts an exact XLSX asset_id/revision into a separate native PDF using optional LibreOffice Calc. workbook_rendition requires mode (print or whole_sheet) and calculation (recalculate or prefer_cache); name defaults to workbook-preview.pdf. Original workbook bytes, formula caches and history stay unchanged.

Follow review_request and read complete read_rendition chunks at one PDF revision/text_sha256. The receipt records the source file reference, renderer/version, requested policies, page geometry and limitations. Use read_pdf/read_pdf_page/render_pdf_page to inspect every actual page. Reading this frozen PDF does not recalculate or repaginate. Modified PDF revisions do not inherit its worksheet mapping.

Print honors print ranges and paper settings, so hidden/blank sheets or out-of-range cells may be absent; no guessed page-to-sheet mapping. Whole-sheet ignores those settings and includes hidden sheets, requiring one page per source worksheet before mapping. Blank pages may be tiny and overflowing text or objects can still be clipped. Compare native cells with actual print and whole-sheet views. Requested recalculation is not a formula correctness verdict; missing caches, volatile formulas and unsupported functions need review.

export_wiki includes rendition.json, the exact input XLSX and PDF page evidence. This is mechanical conversion provenance, without invented Agent review. Install Calc separately and optionally set LIBREOFFICE_BIN. Initially supports 1–100 ordinary worksheets in transitional XLSX; linked resources, macros and embedded OLE need dedicated workflows. Agent reviews semantics, fonts, layout and results. Use the native dimension operations above to correct widths/heights and review a fresh PDF. This is not Microsoft Excel fidelity certification. Public1.4.0 / Unreleased1.4.x.


### Native table workspaces (Unreleased)

Project an exact workbook range into A2T, read complete typed cells and source references, then edit through table_data/table_manage. With table_grid_apply_enabled, an explicit identity-checked worksheet_grid plan applies row/column insertion and deletion together with value edits in one native commit. Renaming retains column identity; deleted/recreated rows and columns receive new identities. Applied inputs remain immutable workspace_reference snapshots. Whole worksheet axes move; native table membership and specialized edits have explicit limits. See the A2T guide. Public stays 1.4.0, with development within 1.4.x.

### Worksheet grid operations (Unreleased)

Discover update_worksheet_grid and workbook_grid_enabled. Assemble any paged schema, then read complete current workbook references. Supply asset_id, expected_revision and worksheet_grid={worksheet:current_key,edits:[{axis:"row",operation:"insert",at:2,count:1}]}. Coordinates are one-based; up to 32 sequential edits each affect at most 1,024 rows or columns. Later edits use the intermediate grid.

Insertion uses inherit_format to inherit formatting from before (default), after or none. Deletion preserves a removed merged anchor's payload by default unless that would overwrite surviving content; merged_anchor="delete" discards it. collapsed_objects selects preserve_size (default) or reject when deletion would collapse an image. Cells/styles, table column identities and supported formulas, names, filters, charts, notes and views move together. Deleted references become explicit #REF!; stale formula/chart caches are cleared and recalculation requested.

Drawing geometry records 96-DPI assumptions. Non-default fonts may require measured column_digit_width/default_column_pixels/default_row_height_points. Dynamic named sources needing evaluation, partial array/pivot edits, protected or unmodeled structures report explicit limits. Agents review automatic row heights, rotated/grouped objects, rendering and actual formula results. Complete the returned review_request and inspect the full operation receipt. Old references and Wiki assertions remain historical; A2T insertion/deletion uses its explicit structural plan. Source writeback is explicit. Public stays 1.4.0 / Unreleased for 1.4.x.

### Workbook sheet structure (Unreleased)

Query contract.for_op for workbook_structure_enabled. read_workbook returns complete, hash-pinned JSON for workbook_view="structure" or "references". Pin revision and view, assemble every text_excerpt through next_text_offset, and verify UTF-8 SHA-256. Structure includes sheet identities/order/visibility, names and views; references adds explicit formula, chart, validation, conditional-format, hyperlink, pivot and consolidation fields. Use read_cell for cell contents.

add_worksheets takes worksheet_insert={index:0,names:["Review"]}. rename_worksheet takes worksheet_rename={key:current_key,name:"Research"}. reorder_worksheets supplies all current keys exactly once in worksheet_order; delete_worksheets supplies selected worksheet_keys. Every key contains sheet_id and part from that exact revision. Mutations require expected_revision, create managed versions, and return review_request. Full operation results are retained in read_workbook.operation_result. Limits: 32 inserted/deleted sheets per request and 256 sheets for structure edits.

Renaming preserves IDs and updates supported explicit local references without altering string literals or external workbook references. Deletion fails when retained formulas, tables, pivots or package links depend on removed sheets. At least one visible worksheet must remain. Insertion/reordering preserve 3D-reference membership by default; explicitly allow_3d_membership_change only after reviewing the intended formula scope.

Untouched native package parts retain their exact bytes. Scope/view indices follow sheet identity; stale calculation-chain links are detached, recalculation requested, and optional stale sheet-title caches cleared. Detached sheets, media and chain parts remain; deletion is not secure erasure. Historical cell/selection references and Wiki assertions never migrate automatically. Protected, signed, VBA/ActiveX, revision and unknown workbook-extension structures require dedicated workflows. Agents review dynamic references, calculated results and Excel rendering. The openpyxl tokenizer identifies formula spans only; it never resaves source workbooks. Public remains 1.4.0, with this work Unreleased for 1.4.x.

### Native selections (Unreleased)

read_selection identifies exact JSON values or Unicode text spans inside full native cell, DOCX block, PPTX shape or PDF page references. Start with an empty selector to discover the complete parsed parent record without added evidence metadata. Then supply an actual RFC6901 pointer, such as /value for a cell, and optionally char_range={start:0,end:3}. DOCX table text is a projection, not a complete native cell geometry model.

Follow next_text_offset and retain one text_sha256 while assembling the complete JSON. Each native-selection-ref-v1 binds parent identity, revision, selector, selected value and nearby text context. Ranges count zero-based Unicode codepoints with an exclusive end; UTF-8 byte ranges belong to that parsed string, not to source-file bytes. Equal values at different locations are not interchangeable. False, zero, null and empty strings retain their types.

verify and derivation ledgers accept complete selection references. Wiki exports attach active selection records under manifest.derivations.selection_records, alongside original source files. New revisions do not inherit assertions; historical evidence remains verifiable. Re-reading a selection cannot override its selector. No opaque-file or nested selection parents. Limits: 2,048 pointer characters, 64 levels, 16 MiB record; missing keys, bad types and out-of-range spans fail explicitly.

Agents choose spans and review semantic support and rendering. Selection checks do not infer OCR, scan pixel regions or cell correspondence. See [RFC6901](https://www.rfc-editor.org/rfc/rfc6901) for pointer syntax and [W3C selectors](https://www.w3.org/TR/annotation-model/#selectors) for conceptual guidance; this is not a JSON-LD implementation. Public stays 1.4.0; future work remains 1.4.x.

Use the document tool with op="native" and a typed native_request. Start with native_request={"op":"contract"} to discover the schema.

- Register a human file or create an independent XLSX workbook.
- Inspect cells, read long text in chunks, and update or clear typed values with an expected revision.
- Publish a new file, explicitly write back to the original, or refresh human edits under the same asset ID.
- Divergent human and agent edits are preserved for reconciliation. Archive retains history and the human source.

MCP checks source versions, locators, saved values and unchanged package parts. Agents still review meaning, rendered layout and recalculated formulas. Protected sheets, rich text and special formula/table regions require supported operations. Broader native CRUD remains unfinished.

## v1.2.0: native evidence wiki
Version 1.2.0 adds verify and export_wiki. Export a revision-pinned Foam index and cell notes, original attachment, manifest and full JSONL references. Native citation_contract and citation_metadata go inside native_request; sheet/cell locators come from the source. Opaque formats export attachments without fabricated interpretation.

New revisions create new snapshots. Existing notes are verified and never replaced; modified or unexpected files stop reuse. Put human synthesis in adjacent notes. A new citation style for the same revision requires a separate wiki directory. The 20,000-cell and 128 MiB limits reject incomplete exports. Interrupted publication retains files and reports reconciliation_required. Document-context CSL citations use evidence csl_contract/render_citations; the native export_wiki projection retains display templates. Rendered verification still requires Agent review.

## v1.3.0: native DOCX
Version 1.3.0 adds read_docx and update_docx using the existing DFM checks. Read all excerpts at a fixed revision, preserve frontmatter and block markers, then submit complete edits to create a managed revision. Untouched OOXML parts are checked byte for byte; source writeback stays explicit. DOCX block references now support bounded read_docx_block and native verification. A distinct docx-blocks-v1 wiki projection includes full parsed block records, the original DOCX and exact package-part attachments, preserving previous snapshots. Integrity does not prove extraction completeness. Unreleased body creation and insertion/deletion are described below. Document-wide styles and full layout verification remain separate work.

### DOCX page previews (Unreleased)

render_docx_page requires asset_id, an explicit revision and zero-based docx_page_index. Optional LibreOffice Writer converts exact original DOCX bytes and returns an actual MCP PNG plus page count/geometry, continuation, renderer identity and image/PDF hashes. Start at page 0 and follow next_page_index; compare current and historical pages with complete DFM content. LIBREOFFICE_BIN can select the executable; missing Writer fails explicitly.

Each request converts the complete document in a fresh private profile, retaining blank pages and static form appearance. Fields can recalculate, so page indices belong to that rendition; they are not stable DOCX evidence locators. Installed fonts and Writer pagination may differ from Microsoft Word. Agents review text, tables, headers/footers, clipping and page flow. Previews do not certify Word fidelity or semantic correctness. A private Linux font fixture reproduces and corrects missing Chinese glyphs without changing DOCX bytes or global settings; see [CJK evaluation](#/release-testing).

Known external resource relationships, resource-loading fields, embedded OLE/chunks, linked VML and SVG fail before conversion. Macro-disabled profiles, process/output budgets and source-copy checks protect the operation; this is not an OS sandbox. Sources and managed revisions stay intact. Limits: 2,000 pages, 64 MiB converted PDF, 64–2,048 pixel previews. See [LibreOffice PDF export](https://help.libreoffice.org/latest/en-US/text/shared/guide/pdf_params.html) and [actual evaluation](#/release-testing).

### DOCX creation and body structure (Unreleased)

Public version stays 1.4.0; this work is on main for 1.4.x. Query contract(for_op="create_docx") for docx_structure_enabled. create_docx creates independent native Word paragraphs and editable tables, with rich runs, half-point sizes, explicit twip grids, merged cells, shading and repeating headers. Covered merged cells must be default/empty.

add_docx_blocks inserts at start/end or before/after a current full block reference. delete_docx_blocks takes docx_block_refs for complete top-level body paragraphs/tables. Pin expected_revision; read all DFM chunks and block listings after each mutation. update_docx still edits existing blocks using complete DFM and original markers.

Known section, range, field, revision and embedded-content dependencies block unsupported deletion. New blocks are checked after serialization; untouched main XML and other package-part bytes are preserved. History and attachments remain after deletion. Agent reviews meaning, page flow, inherited styles and fields/viewer caches. Use the optional page renderer below for actual images; general Word object/style design remains open. Source publication/writeback remains explicit.

### v1.4.0: native PPTX and schema discovery

Native PPTX supports create_pptx, read_pptx, read_pptx_shape and update_pptx. Creation uses explicit text boxes, styled runs and notes; updates target existing native runs with revision and text-hash preconditions. Shape references support verify. The pptx-shapes-v1 wiki projection retains complete shape JSON/XML and exact package attachments, including media, charts, layouts, masters and relationships. Older snapshots remain unchanged. Agents review rendering, overflow, inherited formatting and semantic accuracy; Unreleased structural operations are described below; legacy or macro formats remain outside this adapter.

Unreleased discovery also advertises contract_delivery. If paged, follow contract_request to contract_details, preserving contract_sha256 and for_op, then assemble every text_excerpt and verify UTF-8 SHA-256. The compact index retains all enabled flags, format/operation lists and schema continuation; complete policies remain in these pages. Capability/scope changes require rediscovery. This is separate from schema_delivery/schema_request; read both when advertised.

The native-contract-v2 discovery response supports for_op. Check schema_delivery; follow schema_request for complete JSON pages, preserve schema_sha256 and for_op, then verify the assembled UTF-8 hash. Existing native document inputs are unchanged. Version 1.4.0 includes this discovery migration; clients must no longer assume that the full schema is always inline.

### PPTX shape operations (Unreleased)

Development on main adds add_pptx_shapes and delete_pptx_shapes. Public version remains 1.4.0; subsequent development stays on 1.4.x. Query the installed contract before use. Both operations require asset_id and expected_revision and accept 1–100 targets per atomic batch.

add_pptx_shapes takes pptx_shapes with container (slide_id, part, region and optional group_shape_id) and a typed textbox. Existing slide, notes and nonzero-extent group containers are supported. Positions use local EMU coordinates; group transforms remain unchanged. New textboxes append at the top of the container's z-order. Batch limits are 20,000 runs and 4 MiB of UTF-8 text. Image/chart creation, slide creation/reordering and arbitrary insertion positions are outside these operations.

Follow review_request to read the new revision, page shape listings and assemble complete read_pptx_shape JSON. Existing update_pptx can edit the new runs. If an operation response is marked response_truncated, use revision-pinned paged readback instead of treating the preview as complete.

delete_pptx_shapes takes pptx_shape_refs containing complete native-pptx-shape-ref-v1 evidence from the expected revision. Groups include descendants. Duplicate targets, ancestor/descendant overlaps, stale hashes and surviving known connector/timing/build shape references are rejected. A connector and its target can be deleted together. Checks cover numeric spid/shapeid and a:stCxn/endCxn IDs; arbitrary vendor-extension or GUID dependencies still require agent review.

MCP verifies package inventory, untouched member bytes, IDs and XML outside requested nodes by reversing the planned changes for comparison. Relationships, media and embedded parts remain even when orphaned; deletion is not secure erasure. Historical evidence and wiki snapshots remain available. Edits stage managed revisions; explicit writeback retains source checks and backups. Agents perform the full semantic and visual review and correction.

### PPTX slide structure (Unreleased)

read_pptx_layouts discovers layouts across all destination masters using asset_id, revision, offset and limit. Follow next_offset at one revision. Records include part, master_part, name, type and placeholder_count; layout indices are never assumed.

add_pptx_slides takes expected_revision and pptx_slide_insert={index,slides:[{layout_part,textboxes}]}. The zero-based boundary may precede any slide or append at the end. Each batch inserts 1–100 slides using an explicit destination layout. Ordinary shape placeholders are created empty with inherited formatting; master prompt text is not copied into content, and date/footer/slide-number placeholders remain inherited. Optional textboxes use existing typed EMU/run models. Only generated new slide XML is extracted; the original presentation is never resaved by python-pptx.

Completely read current read_pptx slides through next_slide_offset. reorder_pptx_slides takes pptx_slide_order, a complete unique permutation of {slide_id,part} keys. delete_pptx_slides takes pptx_slide_keys with 1–100 keys, and may leave an empty deck. Both require asset_id and expected_revision. Follow review_request, then read complete shape JSON and use update_pptx for precise new-run edits.

Surviving slide IDs, parts, media, charts, notes and XML remain intact. Deletion removes slide-list entries and presentation relationships while retaining detached slide/notes/media parts; it is not secure erasure. Incoming relationships from retained parts or custom shows block deletion; exclusively removed slides' notes backreferences may remain. Reordering preserves independent custom-show order. Section lists and index-based show ranges currently block structure edits. Cross-deck copying/import and new speaker-note structures remain further work.

Limits: 2,000 slides, 20,000 new runs / 4 MiB UTF-8 per batch, plus existing package/component budgets. MCP checks revisions, dependencies, ordering, relationships, new content and untouched parts, and updates known slide/notes count properties. Agents review actual rendering, overflow, inherited styles, interactions and other cached viewer properties. Historical evidence/wiki and guarded explicit source writeback remain available. See [python-pptx layout semantics](https://python-pptx.readthedocs.io/en/latest/user/slides.html) and [Microsoft slide deletion](https://learn.microsoft.com/en-us/office/open-xml/presentation/how-to-delete-a-slide-from-a-presentation).

### Native PDF pages (Unreleased)

Main adds create_pdf, read_pdf, read_pdf_page, render_pdf_page, add_pdf_pages, update_pdf, delete_pdf_pages and reorder_pdf_pages. Public version remains 1.4.0 on the 1.4.x development line. Discover each installed operation through contract.for_op. Creation takes pdf_create with a name and pages, each specifying exactly one blank or full source reference. Insertion takes pdf_insert with position and pages. Mutations require asset_id and expected_revision; deletion uses pdf_page_refs, reordering uses pdf_order with every page exactly once, and geometry edits use pdf_edits with reference and absolute rotation or crop_box.

Page indices are zero-based. Locators combine page_index, object_id and generation at one immutable revision; read fresh references after writes. Assemble every read_pdf_page text_excerpt at one revision using next_text_offset and verify UTF-8 text_sha256 before parsing. render_pdf_page returns actual MCP PNG images with a longest edge of 64–2048 pixels. Native text extraction is not OCR. Scanned-page interpretation remains an agent/OCR task.

Rotation is absolute 0/90/180/270 degrees. Crop boxes use unrotated native PDF user space, bottom-left origin and UserUnit-scaled units, inside MediaBox. PyMuPDF text blocks use a different unrotated point coordinate system; records declare both. Page operations do not replace arbitrary PDF text or provide secure redaction.

pikepdf/QPDF preserves page identities and encoded streams; PyMuPDF independently reads text and pixels. Checks cover version/representation hashes, remaining page dependencies, document properties, copied form registration, serialized object graphs and unchanged-page rendering at 512 pixels. Known annotation backreferences are deterministically relinked and graph-checked. Agents review changed-page geometry, full-resolution layout, semantics, forms, scripts, reading order and accessibility. Serialized object numbers/xref/file IDs can change; original source bytes and old revisions remain exact.

Within-document edits retain checked bookmarks/links, labels, forms, metadata and attachments. Cross-document copies retain selected pages and complete supported form trees, persist source-reference lineage and do not import document-level metadata/attachments. Encryption, signatures, XFA, parser repairs, dangling page dependencies, partial/renamed fields and cross-document tagged/layer/named-destination integration are rejected. A copy batch cannot repeat a source page. Limits are 2,000 pages/64 MiB per PDF and 100 pages per mutation batch except whole-document reordering. A 60-second worker deadline, supported-platform memory limits and private atomic MessagePack results bound execution and output.

verify retains historical page evidence. export_wiki creates an immutable pdf-pages-v1 projection with complete JSONL, page notes, 768-pixel previews, citation contracts and the exact PDF attachment. Old opaque snapshots remain; modified managed notes block reuse. Publish/writeback are explicit, with source checks and backups. See [native PDF evaluation](#/release-testing) for real Codex MCP calls and independent audits.

### PPTX whole-slide previews (Unreleased)

render_pptx_slide requires asset_id, explicit revision and pptx_slide_key={slide_id,part} from read_pptx. It returns an actual whole-slide MCP PNG, image hash, source slide index, hidden status and LibreOffice renderer version. Historical revisions can also be viewed without changing managed or human files.

Install LibreOffice with Impress separately; LIBREOFFICE_BIN can select its executable. The contract's pptx_rendering.configured describes adapter wiring, while availability is checked per request. Writer alone cannot convert PPTX. Temporary full-deck export includes hidden slides and excludes notes pages, preserving slide-number context. PDF page counts and exact source keys are checked before bounded rendering. Limits: 100 slides, 64–2048 pixel longest edge and a 60-second deadline, with normal package/PDF byte budgets. Linked external content, SVG media and alternative show selections require separate workflows. Ordinary hyperlinks are supported. Private processes/profiles are not an OS sandbox.

Agents compare native content and rendered images for overlapping shapes, clipping, layout and meaning, then coordinate corrections. A static LibreOffice image does not establish PowerPoint fidelity, installed-font equivalence, animation or media playback. read_pptx_picture remains an embedded-image preview. Public packages stay 1.4.0; this work is Unreleased for 1.4.x.

### PPTX picture assets (Unreleased)

Main adds add_pptx_pictures, replace_pptx_pictures, read_pptx_picture and extract_pptx_picture. Public version remains 1.4.0; development continues on 1.4.x. Register human PNG/JPEG files, then use their native-file-ref-v1 file_reference. verify checks immutable whole-file bytes; it does not prove semantic interpretation or live source freshness.

Creation accepts an existing slide, notes or nonzero-extent group container, local EMU left/top/width/height, fit=contain/cover/stretch, name and description. Mutation requires asset_id and expected_revision. Replacement takes full current shape references and mapping=preserve_existing: only the image relationship changes; crop, geometry, rotation, flips, effects and stacking order remain. Original image bytes are embedded exactly, and shared media is never overwritten. Different aspect ratios still require visual review.

read_pptx_picture returns an actual MCP PNG and separate original-image and preview hashes. This is the embedded raster only: slide crop, group transforms, effects and color management are not rendered. Use read_pptx_shape for complete geometry and evidence. extract_pptx_picture copies exact image bytes into a new native asset whose initial history retains the source deck revision, full shape reference and media hash. Existing delete_pptx_shapes retains underlying media and is not secure erasure.

Sources must be single-frame PNG/JPEG without EXIF rotation. Linked/alternate image representations, ambiguous content types and unsupported formats are rejected. Limits: 16 MiB / 16 million pixels per image, 1–100 pictures and 32 MiB / 64 million pixels per batch, counting repeated uses. Package limits still apply. MCP checks source/revision/CAS, image integrity, exact new parts, untouched bytes and XML outside the operation. Agents review semantics, actual slide rendering, crop, accessibility and color. pptx-shapes-v1 wiki snapshots retain all media/relationships and exact PPTX files; publish/writeback remain explicit.

### Native PPTX tables (Unreleased)

add_pptx_tables takes asset_id, expected_revision and pptx_tables. Each item has an existing container and table with local EMU left/top, column_widths, row_heights and a matching rectangular cells matrix. Cells contain paragraphs of formatted runs plus alignment, vertical_anchor, margin and optional six-digit RGB fill_rgb/text_rgb. Name/description provide identity and alt text. Numbers, leading zeros and formula-like strings remain literal text.

Inclusive, zero-based merge rectangles cannot overlap or exceed the grid; covered cells must remain empty/default to avoid hidden data loss. Merges are built before text is populated. Existing destination tableStyles/default GUID is used, with no invented style ID when absent. First/last row/column and banding flags select style roles. MCP checks the requested geometry, strings, direct formatting, merge map, untouched parts and XML. Agents review actual rendering, themes, overflow and meaning.

Read complete tables with read_pptx_shape; update_pptx edits anchor cell runs and delete_pptx_shapes deletes whole tables using full current references. Historical verification, wiki snapshots and guarded source writeback remain available. Existing-grid row/column operations are described below; automatic A2T bridging and semantic PDF-to-cell lineage remain follow-up work. Limits: 100 tables per batch, 100 rows/columns per table, 10,000 cells, 20,000 runs and 4 MiB UTF-8 text per batch; dimensions and summed extents are bounded to 100,000,000 EMU.

Native export_wiki now exposes citation_contract as a typed union: source/author-year/numeric preset, or custom inline_template and reference_template. Valid existing JSON remains compatible. Display contracts do not store source references, proof reports or arbitrary transcription data; canonical evidence remains separate.

### Table grid CRUD (Unreleased)

update_pptx_table_grid takes asset_id, expected_revision and pptx_table_grid={reference, edits}. Supply the complete current shape reference and 1–32 sequential edits. Each uses op insert/delete/resize, axis row/column and a zero-based index in the current intermediate grid. Insert/resize use EMU sizes; delete uses count. Optional inserted cells use the existing typed cell contract in row-major order, matching the inserted slice. Omitted cells are blank.

Insertions inside merges expand them; insertion at the start shifts them. Partial deletion shrinks merges. When deleting a surviving merge's anchor, its content and formatting move to the new top-left cell; hidden content, fields, relationships, extensions or identity at that destination block promotion. A surviving single cell becomes unmerged. New covered cells must be default/empty. Source signatures, stale references, malformed grids, bounds and concurrent writes fail before commit.

Existing cell XML, row/column metadata, styles and untouched package parts are retained, except explicit deletion, changed merge flags and anchor promotion replacing covered-cell formatting. Position stays fixed; frame extents follow grid totals at the existing scale. Limits apply at every intermediate step: 1–100 rows/columns, 10,000 cells, 20,000 runs, 4 MiB text and 100,000,000 EMU dimensions/frame; at most 10,000 cells inserted per batch. Old evidence remains valid; coordinates and derivation assertions do not migrate automatically. Agents review rendering, overflow, banding and semantics. Cell merge/split is described below.

### Table cell merge/split (Unreleased)

The same update_pptx_table_grid edits accept merge with row, column, end_row, end_column and required content_policy; split takes the existing merge origin row and column. Coordinates are zero-based and inclusive; a merge must span at least two cells.

require_empty rejects meaningful non-anchor content, including whitespace text, fields, links, extensions and paragraph identities. append_paragraphs moves complete paragraphs from nonempty cells to the top-left anchor in row-major order. Literal text, rich formatting, fields, links and paragraph XML survive. Internal empty paragraphs and the anchor's existing empty paragraphs are retained. Source cells receive an empty paragraph; cell properties and text-body settings stay with their original cells.

Existing merges must be wholly contained by the new rectangle; partial intersections require splitting first. Split removes the merge flags and keeps all migrated text at the anchor; it does not reconstruct earlier content distribution. Split, row/column insertion and merge can be composed within one checked batch. This follows [python-pptx merge/split semantics](https://python-pptx.readthedocs.io/en/latest/user/table.html#un-merging-a-cell), with explicit content policies and version checks.

MCP checks current full references, unchanged paragraph XML during migration, merge structure, serialized results and untouched parts. Agents read the complete updated shape and review paragraph order, meaning, rendered borders/styles and overflow. Managed revisions precede explicit source writeback. Public packages remain 1.4.0; these changes stay Unreleased for 1.4.x.

### Native derivations (Unreleased)

record_derivation connects full immutable native file/cell/DOCX-block/PPTX-shape/PDF-page references. It records the activity and agent review while mechanically checking both endpoints. Agent identity and semantic/layout/formula review are caller assertions. A valid reference can coexist with a failed semantic review. Source and target versions remain explicit; new file revisions never inherit old claims automatically.

Read the complete read_derivations ledger using text_offset/text_limit and one derivations_sha256; concatenate all chunks and verify UTF-8 SHA-256. record_derivation and retract_derivation require expected_derivations_sha256. A new assertion may supersede an active record atomically; corrections and withdrawals retain history. verify_derivation reports active status, reference validity and current managed revisions separately, with at most ten source results per page (next_offset plus the same ledger hash). Review notes remain in the complete ledger. External source freshness still requires refresh/reconciliation.

Limits are 64 distinct source references per assertion, 1,000 ledger events and 16 MiB. The ledger shares native operation locks and atomic publication; source/document bytes stay intact. export_wiki can pin derivations_sha256, creates a distinct ledger-pinned snapshot, retains the full history and attaches exact sources for active assertions targeting that exported revision. Other revisions and withdrawn assertions remain historical metadata, without newly verified attachments. Supported native/image source formats retain their extensions for direct native registration; opaque sources use .bin with original format metadata. Existing snapshots and curated notes are preserved. citation_contract controls display only. PDF-to-PPTX links currently identify a page and whole shape, not individual OCR cell mappings.

The design draws on [W3C PROV-O derivation](https://www.w3.org/TR/prov-o/#Derivation) and [Docling Graph provenance](https://github.com/docling-project/docling-graph/blob/main/docs/fundamentals/graph-management/provenance.md); it does not claim complete PROV-O/RDF conformance.

See the source page for operation fields, examples, format restrictions and recovery details.`,
  "workflow-chapters": `## Choose by source and task
Use the PDF workflow for page inspection and extraction, the DOCX workflow for reversible DFM editing, and A2T for reusable tables. Evidence, wiki, and knowledge features build on those source-specific paths.

## Keep verification attached
Carry locators, hashes, and source identity through every chapter instead of reconstructing provenance later.`,
  "design-ux": `## Information architecture
The landing page explains the product and routes readers into task-oriented documentation, reference, and maintenance chapters. The reader keeps long technical pages searchable and provides an in-page outline.

## Quality standard
Desktop and mobile QA must cover routing, language, keyboard focus, filtering, copy actions, console health, and accessible controls.`,
  architecture: `## Runtime layers
Domain models define document and evidence contracts, application services orchestrate use cases, and infrastructure adapters own external I/O. The MCP presentation layer exposes the balanced public surface through the official SDK 2 server.

## Evidence flow
Source identity, extraction metadata, locators, and hashes remain connected from ingest through persisted assets and Foam exports.`,
  "mcp-tools": `## Public tool surface
The default balanced surface contains 30 tools, while compact mode contains 17 facades and legacy mode retains 63 direct tools. Facade operations preserve the same source, job, and citation contracts as their shortcuts.

## Read exact contracts
Check each tool signature and operation name before copying an example into an MCP client.`,
  "mcp-resources": `## Resource families
Thirteen registered resources expose document and table artifacts through stable URI templates. Resources are read-oriented views over persisted state rather than alternate mutation paths.

## Use tools for changes
Choose a tool operation when you need ingest, conversion, editing, deletion, or another state-changing workflow.`,
  "tool-chooser": `## Start from the task
Choose document, evidence, DOCX, table, job, knowledge, profile, or section tools according to the outcome you need. Prefer a facade operation unless a balanced shortcut is clearer for a frequent action.

## Confirm inputs
Use the MCP Tools page for the exact parameter names and supported operation values.`,
  "pdf-workflow": `## Inspect before ingest
PDF preflight is a read-only, process-isolated operation for PDF files only; it reports page signals, OCR needs, routing guidance, and source identity. Ingest then runs through a background job so stdio clients remain responsive.

## Export verified assets
After ingest, export deterministic text, table, figure, citation, and Foam assets without changing the source PDF.`,
  "document-sections": `## Navigate structure
Use the section facade to read a tree, inspect details, search headings, and fetch bounded section content or blocks. Reading order and line ranges answer different questions and are preserved together.

## Return to the source
Use section paths and block metadata with document locators when a claim needs precise verification.`,
  "docx-dfm-workflow": `## Edit reversibly
DOCX ingest creates a DFM representation with Word-origin block and run metadata for supported edits. Save operations enforce stale-source and integrity checks before writing a new document.

## Respect format boundaries
Use validation and conversion tools for supported round trips, and review structural table edits before writeback.`,
  "citation-provenance": `## Captured ETL evidence (Unreleased)

Legacy PDF extraction references bind mutable ETL files. First inspect_etl_source using ref={doc_id,source_type,source_id}, where source_type is span, table or figure. Read all hash-pinned result pages to obtain the full current asset_ref without writing a snapshot. Pass that complete reference to capture_etl_source and retain its full etl-citation-ref-v1. Previews, partial/stale refs and mismatched expected hashes are rejected before publication.

read_etl_source verifies every captured artifact and returns the complete original record after the ETL directory changes or is deleted. view_etl_source returns an actual MCP PNG of the captured original PDF page; render_size is the longest edge, 64–2048 pixels. Missing pages fail explicitly. Use text_offset/text_limit/expected_text_sha256 for inspect/capture/read, following next_text_offset to null and checking assembled UTF-8 SHA-256; image views do not use text paging.

Put captured references alongside native references in a CSL document's sources and bind each cite with source_keys. Raw mutable ETL refs require capture first. Wiki exports include all original bytes, extraction artifacts, selected images, complete evidence JSON and citation-note links. Historical paths in captured manifests are descriptive, never used to resolve immutable readbacks. Existing native DOCX refs remain the route for Word; DOCX DFM is a separate pipeline.

Snapshots check source bytes, hashes and locator consistency. Agents compare full extraction content, tables, actual source-page images and bibliographic data before citing or correcting. Raw bytes and decoded/BOM-stripped/LF-normalized text hashes remain distinct. Limits: 128 MiB per snapshot, 20 MiB per metadata/image file, 2 MiB per complete evidence record. Public stays 1.4.0; this work is Unreleased within 1.4.x.

## CSL citation documents (Unreleased)
Render a complete document through evidence(op="render_citations", citation_document=...). Discover the hash-paged csl_contract first. Pinned citeproc-js and official styles support APA7, Chicago18 author-date/notes and Vancouver-NLM citation sequence. Document context handles retroactive year suffixes, repeat citations and bibliography ordering; sorting within a group follows the selected style. Existing citation-format-v1 custom templates remain available.

Provide structured CSL-JSON items, ordered clusters and optional uncited_ids. Chicago notes require positive ordered note_index values; in-text styles use zero. locales are en-US and zh-TW, with bundled zh-CN base fallback. Missing author/date/title fields are reported; no bibliographic data is invented. Optional local Node.js >=20 is required only for this operation (use a supported Node24 LTS). No runtime network downloads or installs. The bundled npm release is 2.4.63; its internal processor version is 1.4.61, recorded separately with exact resource hashes and upstream licenses.

Place full native references in sources, then connect each cite through source_keys. Native source integrity is verified at immutable revisions. Printed CSL locators remain caller-supplied display data, separate from PDF indices or native locators. Agent review covers bibliographic truth, semantic support, printed locator correspondence and typography.

Read every text_excerpt page at one text_sha256 and verify UTF-8 SHA-256. expected_text_sha256 rejects changed content before publication. Optional wiki_root creates an immutable citation snapshot with exact source attachments, complete citations.json, per-cluster wikilinks and references.html typography preview. Identical snapshots require exact byte/inventory checks before reuse; curated notes and historical citations remain intact after native edits. This is a document citation snapshot; existing native export_wiki projections remain unchanged.

Limits:500 bibliography items,1000 clusters,2MiB input,8MiB result,128MiB total Wiki output. Bounded Node processing fails explicitly on timeout or invalid input. Public1.4.0 / Unreleased1.4.x.

## Preserve exact evidence
A canonical AssetRef ties an exact quote to document identity, revision, line or character ranges, context, and hashes. Verification fails closed when the current source no longer matches those fields.

## Distinguish previews
A bounded asset-ref-preview-v1 response is not canonical and must not be submitted as a verification reference.`,
  "a2t-tables": `## Build reusable tables
Plan schemas, manage tables, query stable rows, attach cell citations, and use durable drafts for interrupted work. Table history records changes while render operations produce reusable artifacts.

## Native workbook workspaces (Unreleased)
Discover table_workspaces_enabled and each operation with contract.for_op. Read the workbook's exact sheet_id/part, then project_workbook_table with asset_id, revision and table_projection={worksheet:key,start_cell:"A1",end_cell:"E3"}. All rows remain data, including headers. Columns use Excel letters; types are never guessed.

Read the complete read_table_workspace JSON through next_text_offset, pin table_sha256 on continuation, and verify the assembled UTF-8 text_sha256. Limits are 20,000 cells, 16 MiB per complete representation and 4,000 characters per page. Use table_data.update_cell with stable row_id, column_name and tagged value={kind:"string",value:"007"}. Strings, numbers, booleans, formulas and blanks remain distinct; source_only values cannot be written without choosing a supported type.

After another complete read, apply_table_workspace requires table_id, expected_table_sha256, asset_id and the bound expected_revision. It patches only changed cells in the original package; styles, unchanged rich text and unrelated parts survive. Existing merged-cell, rich-text and table-header guards still apply. Read the new workbook and its operation_result. Source publication/writeback stays explicit.

Applied/exported input is retained as an immutable workspace_reference: verify it or pass it to read_table_workspace after the live table changes or is deleted. Bindings never auto-advance; project the new revision for a subsequent synchronized edit. Source references describe extraction origin and do not assert support for edited values.

Changed correspondence requires the explicit structural plan below. create_workbook_from_table can also create an independent XLSX with table_workbook={name:"table.xlsx",sheet:"Data",include_headers:false}, the table ID/hash, and an optional frozen workspace_reference. It retains typed data and formula text, with row/column mapping in the stored operation result. Source styles and formula relocation are not copied to independent workbooks. Ordinary scalar A2T tables are also supported. Agent review covers meaning, formula results and layout. Public stays 1.4.0; this is Unreleased development for 1.4.x.

### Structural A2T writeback (Unreleased)

Check table_grid_apply_enabled on contract(for_op="apply_table_workspace"). New workspaces retain row_ids and column_ids. Renaming preserves identity; deleting/recreating a same-name column creates a new identity. table_manage accepts typed JSON default_value for native columns. Historical snapshots retain their hashes; ambiguous legacy column history needs a fresh explicit correspondence.

After table_data/table_manage edits, read the COMPLETE workspace again. Review structural_plan.worksheet_grid and its destination plus the complete current native workbook references. Supply the plan explicitly as worksheet_grid to apply_table_workspace with asset_id, bound expected_revision, table_id and the current expected_table_sha256. The MCP checks each surviving identity and new slot, applies structure and values before one native commit, and reads the complete destination back. Re-read the new workbook references, full operation receipt and frozen workspace_reference; verify the snapshot. Source bindings and old evidence never auto-advance.

Unchanged source cells follow native relocation, preserving supported formulas, rich text and styles. Edited/new formulas use destination coordinates; missing new values mean blank. Plans move WHOLE worksheet rows/columns, including content outside the projection, and discard deleted merged anchors. Reordering existing identities requires native move support. Native Table headers/calculated columns, partial arrays and unmodeled structures retain their checks; table-boundary membership requires explicit expand_tables as described below. Agent review covers membership, dynamic references, calculated results and actual rendering.

### Native Table totals lifecycle (Unreleased)

When table_totals_lifecycle_enabled is advertised, update_workbook_table accepts table_update.totals_row with exact revision, worksheet key, Table part and expected_ref. columns may be omitted for a totals-only transition. Add uses {action:"add",reuse_definitions:true,cell_styles:"preserve"}; it requires blank cells directly below the Table and restores hidden totals definitions. Set reuse_definitions:false for blanks, or override columns[].totals. Optional cell_styles:"last_data_row" copies direct cell styles only.

Remove uses {action:"remove",cells:"clear"|"keep_cells",retain_definitions:true}. Clear removes contents while retaining styles; keep retains text/runs and freezes only the retained cells' own Table references to absolute pre-removal ranges. Other workbook formulas keep structured references, including #Totals. Set retain_definitions:false to discard hidden definitions. Neither transition moves worksheet rows; compose update_worksheet_grid explicitly if physical space must change.

Data membership and filter/sort ranges remain stable. Overlaps, special formulas, protection and source dependencies retain checks, including pivots over detached totals cells. Current-row selectors (#This Row / [@Column]) in kept totals formulas require explicit correction because they have no data-row intersection. Shared strings retain content/runs while reference counts may be recomputed. Read the complete operation receipt and updated references. Agent review covers future formula membership, results and rendering; historical evidence never migrates. Public stays 1.4.0 / Unreleased within 1.4.x.

### Native Table creation (Unreleased)

When workbook_table_creation_enabled is advertised, add_workbook_table turns an explicit worksheet range into a native Excel Table. Use create for an independent workbook or register an existing XLSX. Pin expected_revision and the worksheet key from complete read_workbook references. table_create provides ref, unique name, ordered columns, header_row, totals_row, autofilter and style.

Matching headers retain rich/shared strings. header_policy=fill_blank additionally fills blank headers, never silently renaming existing values. Headerless Tables require autofilter=false. Ranges include at least one data row and any explicit totals row; totals must start blank and no worksheet rows are inserted. New calculated columns use require_matching for blanks or explicit replace_all. Choose built-in/existing Table styles; ordinary data, leading zeros, cell formats and untouched package parts remain intact.

Read the complete created_table identity, header_cells and operation receipt. Name/ID/relationship allocation reserves retained detached Table parts. Overlaps, special formulas and active protection retain checks; empty/disabled workbookProtection is accepted. Historical evidence and A2T bindings never migrate. Agent review covers meaning, actual layout, filter behavior and recalculated results. Public stays 1.4.0 / Unreleased on 1.4.x.

### Native Table column edits (Unreleased)

When workbook_table_edit_enabled is advertised, update_workbook_table pins the exact worksheet key, Table part, expected_ref and file expected_revision. Each column edit identifies column_id and expected_name. name updates the header and existing structured references by original identity. Complete read_workbook.tables[].header_cells exposes native cell and resolved shared-string XML. Rich headers require header_runs matching the original run count and concatenating to the new name; run formatting survives and shared strings are cloned.

calculated uses a scalar formula beginning with =, anchored at the first data row. require_matching accepts blank cells or formulas matching the previous column formula; replace_all explicitly replaces ordinary values/formulas. Null formula with keep_cells removes automatic-fill metadata while retaining cells. totals edits an EXISTING totals row using blank, label, formula or function (sum, average, count, countNums, min, max, stdDev, var). New formulas use final names. Bounds, column IDs and styles remain intact.

Read the complete new references and operation_result. Protected/merged cells, unsupported text/formula features and mapped/query source schemas retain checks; pivot header changes need coordinated field identities. Caches are invalidated and recalculation requested. Agent review covers actual results, filtering and rendered layout. Historical evidence and A2T bindings never migrate. Public stays 1.4.0 / Unreleased for 1.4.x.

### Native Table expansion (Unreleased)

When table_expansion_enabled is advertised, complete read_workbook.tables exposes worksheet/part identities, attributes, column IDs, original part SHA-256 and complete parsed XML. Each insert edit can supply expand_tables=[{part:"xl/tables/table1.xml",expected_ref:"A1:F3"}]. expected_ref names the table range BEFORE that intermediate step. Extend first/last data boundaries or left/right column boundaries; insert before totals. Adjacent Tables are not selected implicitly. Whole worksheet axes still move.

Table/filter/sort extents are coordinated, surviving column IDs retained, new IDs and unique headers generated, and calculated formulas filled. Sort keys keep their original column identity. Filtering visibility, sorting, recalculated results and rendered layout require Agent review. Inserting before totals includes new rows in the filter even without an explicit edge override.

Use the tagged A2T value {"kind":"native_generated","value":null} ONLY to retain a header/calculated cell generated by this structural operation. Missing or blank values remain blank. Ordinary/surviving cells and direct independent exports cannot use the placeholder. Read generated_table_cells and resolve_native_generated_values in the full operation receipt; frozen workspaces retain input intent. Reproject the result to obtain resolved values. Source bindings and historical evidence remain unchanged.

Specialized Table header/calculated/totals editing, mapped/pivot source schema changes and native identity reordering retain their own boundaries. Public remains 1.4.0, with this work Unreleased for 1.4.x. Design references: [Microsoft SpreadsheetML tables](https://learn.microsoft.com/en-us/office/open-xml/spreadsheet/working-with-tables) and [XlsxWriter tables](https://xlsxwriter.readthedocs.io/working_with_tables.html).

## Keep row evidence explicit
Use stable row identifiers and cell-level AssetRefs so every comparison can return to its source.

## Complete citation readback (main development; unreleased)
When the installed tool schema advertises it, call \`table_cite(operation="read", table_id="tbl_...", row_id="row_...", column_name="Reading")\`. Keep \`get\` for summaries. The read response includes \`text_excerpt\`, \`citation_sha256\` and \`next_text_offset\`; follow subsequent pages with that hash, concatenate the excerpts, verify UTF-8 SHA-256 and parse the complete JSON. Pages contain at most 4,000 characters and adapt to the MCP response cap; a complete representation is limited to 16 MiB.

The record binds stable cell identity, current value, full stored references and annotations. Missing citations are explicit null; changed content or a different cell rejects continuation. Partial excerpts are transport fragments. Stored-content integrity does not verify the cited source or its meaning.`,
  "llm-wiki": `## Export a portable wiki
Agent asset and evidence exports can create Foam-compatible indexes, notes, anchors, tables, figures, and media. These files remain readable Markdown while retaining embedded provenance records.

## Check evidence health
Run wiki health checks before promoting claims, and keep unresolved or stale references visible for review.

## v1.2.0: preserve human notes
Version 1.2.0 verifies the complete existing PDF bundle inventory and hashes before refreshing it. Changed, missing, extra or symlink entries stop replacement. Identical exports reuse files; actual replacements retain the previous directory and return backup_path. Publication rechecks the observed version under an OS lock, while external editors still require coordination.`,
  "knowledge-graph": `## Use discovery as optional context
LightRAG is opt-in and can support consultation or graph export when its backend is configured. Knowledge responses help discovery but do not replace canonical document evidence.

## Verify cited answers
Request reference verification and follow returned evidence back to citation bundles or persisted AssetRefs.`,
  "background-jobs": `## Track long work
PDF ingest and other bounded long-running operations return job identifiers instead of blocking the MCP request. Job status exposes progress, warnings, results, and artifact paths.

## Handle lifecycle explicitly
List active work, inspect terminal states, and cancel only the intended job.`,
  "etl-profiles": `## Select extraction policy
ETL profiles group validated settings for document extraction and can be listed, inspected, loaded, detected, or activated. Detection proposes a profile from source hints without silently changing unrelated configuration.

## Verify the active profile
Inspect the current selection and backend availability before starting a production ingest.`,
  "git-harness-hygiene": `## Preserve managed assets
The VSIX synchronizes assistant instructions, skills, rules, and MCP setup assets into trusted workspaces. Local skip-worktree policy can keep automatic synchronization from polluting feature diffs.

## Check parity before packaging
Run the asset synchronization check and inspect staged paths so generated or unrelated files do not enter a release.`,
  "developer-guide": `## Keep boundaries clear
Domain code stays free of I/O, application services coordinate use cases, infrastructure owns adapters, and presentation owns MCP transport. Behavior changes should include a focused regression that proves the edge case.

## Validate the integrated product
Run Python checks, documentation generation, extension tests, asset parity, and relevant smoke tests before handoff.`,
  "release-testing": `## Run release gates

### Native PDF annotation evaluation (Unreleased)

The synthetic suite covers all 12 appearance kinds, rotation/CropBox/UserUnit, foreign AP bytes, direct/shared arrays, dependencies, signatures, locks and stale references. Actual SDK2 balanced/compact lifecycle tests read complete schemas/records/receipts, compare real PNG pixels and retain historical references, selections, derivations and Wikis.

On 2026-09-21, the default Codex model processed the original 17-page NIST SRM 1648a PDF: 399 successful MCP calls, 321.35 seconds, 4 managed revisions, 37 complete annotation records and 8 actual PNGs. It visually transcribed Aluminum (Al)(a,b) | 3.43 ± 0.13 | %, created Highlight/FreeText, replaced the FreeText appearance and deleted the Highlight. Independent audit checked all 17 pages' native streams/body pixels, 8 existing Links, actual image transport, source provenance and both Wikis. One invalid contract.text_limit call was recovered and retained. Visual review covered page indices 4/5 only.

The original 359-page NASA Apollo 11 scan first failed safely: its body-reader copy bypassed the existing original-byte proof for equal duplicate Length declarations, so a writer warning prevented any committed revision. Reusing the strict native package check fixes the copy; 58 focused regressions passed and conflicting lengths still reject. The original failed run is retained. NIST numbers above precede that later correction and have a separate source fingerprint.

The corrected NASA run passed: 238 successful calls plus 1 recovered parameter error, 379.19 seconds, 4 versions, 5 complete annotation records, 8 actual PNGs and 2 Wikis. The transcription is Lift-off | 00:00:00.6. Independent audit compared native body streams and annotation-free body pixels across all 359 pages, plus complete untouched-page images. Agent visual review covered indices 17/18 only; 357 other pages were not visually reviewed. Original source bytes stay unchanged; the managed creation receipt explicitly records equal-Length canonicalization. Installed Python 3.13 wheel and Python 3.12 Docker replays passed at final source fingerprint 74e3abc3…, with identical 4 versions/8 images/records/Wikis and src imported from site-packages.

A mixed Highlight/FreeText fixture also exposed one-level MuPDF compositing drift with annots=False. Disposable annotation-free reader copies now retain exact body comparisons and native inverse checks. FreeText can enter ordinary page extraction; it is distinct from original body content.

The final full suite passed 3,521 tests with 33 optional skips in 698.37 seconds, including Writer/CJK fonts, the real PDF corpus and both SDK2 annotation workflows. Ruff, type checks across 306 modules and the Bandit medium/high gate passed; 185 low-severity Bandit findings remain recorded. VSIX 199 tests, 64-file package checks, install/update and wheel/Docker MCP stdio passed. Local VS Code activation was unavailable because xvfb-run was missing; remote CI still checks it. Desktop/mobile documentation and both language switches passed without horizontal overflow or browser errors.

Adding both annotation workflows to the explicit Python 3.10 CI list exposed the original 180-second test limit: that run retained 1,157 passes, four skips and two timeout failures. An isolated Python 3.10 diagnostic completed all original assertions and 408 MCP calls in 142.51 seconds. Only these two cases now allow 300 seconds, with a 20-minute enclosing CI job and slow-test duration reporting. Other test limits, runtime code, complete pagination and every content-integrity assertion remain unchanged. Both configurations then passed the isolated Python 3.10 pytest run: two tests in 266.20 seconds.

Ordinary pytest never launches a model. Use uv run python -m tests.codex_pdf_annotations.run --corpus /path/to/verified-corpus --case nist-1648a --output /path/to/new-run; use --case apollo11 for the second original. No model override. Audits retain full contract/schema/record continuation and ordering, errors, actual images and limits. Public release: 1.4.0; next consolidated patch: 1.4.1.

### Native Word footnote/endnote evaluation (Unreleased)

Subsequent CI correctly caught actual note-content misbinding in Writer 24.2.7. Replaying the same DOCX with the official isolated 24.2.7.2 runtime proved this was not whitespace extraction. Eight controlled runs compared definition order and ID mappings: body-ordered definitions with aligned IDs passed both 7.3.7 and 24.2.7. Explicit remap_ids lets the Agent inspect the mismatch and apply a checked correction while preserving source, native content/styles and historical references. Original failing PDFs/PNGs, CI logs and probes remain retained.

The corrected default-model Codex run on Writer 24.2.7.2 completed 211 successful MCP calls, two recovered argument errors and 282.24 seconds. The retained errors were unsupported text_limit on contract and text_offset:null after schema pagination ended. The Agent inspected all nine initial, misbound and corrected PNGs; independent replay matched every pixel. The audit verified 24 complete notes, four catalogs, 13 complete contracts, four managed revisions and two historical Wikis. Explicit mappings were footnote 11→1 and endnote 12→1 / 5→2; other IDs, text/styles and human source stayed intact. Deleted-footnote and pre-correction footnote 11/endnote 5 references still verified against their historical revisions.

Set LIBREOFFICE_BIN to isolated 24.2.7.2 and add --repair-note-ids to the existing runner; ordinary pytest never starts a model. The official archive SHA256 is be967ebc63cb15b831b4e8176492e83eb625dc00852eb96eda2b299b6e74bb74. Both earlier 7.3 traces remain retained; the correction audit additionally checks four revisions and the actual misbound pages. Python 3.10: 79 passed, one optional rendering skip in 28.60 seconds. The installed wheel outside checkout reproduces 24 notes, four catalogs and both byte-identical Wikis at this Codex run's source fingerprint.

Corrected full suite: 3,403 passed, 33 optional skips in 426.69 seconds, including the original Writer 7.3/CJK and NIST/NASA PDFs; both SDK2 configurations also passed with Writer 24.2.7.2. The installed Docker runtime reproduces the same 24 notes, four catalogs and both byte-identical Wikis, with the exact Codex/wheel source fingerprint. Standard pip installation, MCP stdio, all artifact audits and VSIX 199 tests/64-file packaging/install-update pass. The first CI npm audit returned 503 during upstream maintenance; after recovery both local npm lock audits report zero vulnerabilities. Original failure logs remain and all remote jobs are still required after pushing.

The earlier Writer 7.3 development evidence follows; it does not establish compatibility with every reader.

Actual default-model Codex processed a synthetic three-page Word document: complete initial records for seven normal/special definitions, body references, contracts and all initial page PNGs; then create native footnote ID11/endnote ID12, delete footnote ID8, and correct ID2 text while preserving other paragraphs and formatting. Previous-source evaluation completed 153 successful MCP calls, one recovered argument error and 204.28 seconds, without a model override. The error supplied text_limit to contract; the Agent removed that unsupported field and completed the workflow. Original errors remain retained.

Independent audit passed sixteen complete note records, three catalogs, twelve complete contracts, three managed revisions, two historical Wikis and all six actual PNGs. Final page1 shows the new footnote as1 and corrected original as2; page3 shows the new endnote asi and original asii. Native IDs11/12 remain distinct. The old page2 footnote disappears and adjacent endnote marks remain. Bold body text, 007 µg, -0.50 mg/L, preserved paragraphs, source bytes/mtime, complete native XML/parts, receipts and deleted-note historical references/selections all pass.

The first SDK2 render attempt exposed a real content/mark mismatch when a new body reference preceded an old one but its definition was appended. Retained failing documents and controlled definition-order/ID probes led to placing new definitions before the next existing body reference's definition, without changing existing IDs or sibling order. A regression covers actual content order. This is a bounded mechanical correction, not a semantic or universal renderer verdict.

An earlier default-Codex run also passed:149 successful calls, one recovered error,223.72 seconds. A later optional-adapter snapshot-identity collision required a distinct docx-notes-content-v1 projection; the full projection remains byte-compatible. The final model run followed that production change, rather than rerunning to erase errors. Both traces remain retained.

Reproduce with the native note unit/SDK2 tests, tests.codex_docx_notes.run --output <new-dir> --font-fixture <pinned-font-dir>, then tests.codex_docx_notes.audit. Outside checkout, replay installed code with scripts/smoke_docx_note_runtime.py and the run workspace. Ordinary pytest never starts a model.

Previous full suite:3,384 passed,33 optional skips in396.74 seconds, including Writer/CJK and NIST/NASA PDFs. Python3.10:60 passed,one optional rendering skip in23.43 seconds. Its first private test harness lacked locked backports-asyncio-runner; installing that exact dependency resolved it, with the original log retained. The clean wheel outside checkout reproduces sixteen full notes,three catalogs and both byte-identical Wikis at the exact final-Codex source fingerprint. VSIX:199 tests,64-file package check and install/update pass; GUI activation is delegated to CI. Local Impress/Calc are absent and their optional tests skip. Standard pip wheel installation and MCP stdio pass. The installed Docker runtime reproduces the same sixteen notes,three catalogs and both byte-identical Wikis with the exact source fingerprint. Eight desktop/mobile zh/en website states pass interactions and overflow checks with no console errors; cached CDN scripts do not establish live CDN availability.

This synthetic case uses optional Writer and private pinned fonts. Microsoft Word, arbitrary real documents and every custom mark/special setting/revision dependency remain unverified. MCP supplies source/version/structure checks; Agent owns full semantic and visual review and correction. Public1.4.0; next consolidated1.4.1.

### Native Word story lifecycle evaluation (Unreleased)

Actual default-model Codex processed a synthetic four-page, three-section Word document. It assembled complete story, binding and contract records and reviewed all four initial pages, cloned a header, created a footer, bound the middle section, explicitly retained the following section's original definitions, deleted an unused definition and corrected the new header text. The run completed 98 successful MCP calls, zero tool errors and 222.28 seconds, without a model override.

Independent audit passes ten complete story records, three complete structure records, two complete contracts, three managed revisions, two historical Wikis and all eight actual PNGs. Source bytes/mtime, native XML, untouched package parts, full operation receipts, paged hashes, deleted-definition historical references/selections and every Wiki attachment pass. All three versions render four pages. Initial/final pages one, two and four have identical pixels; only page three changes. Bold/italic styling, 007 and -0.50 mg/L survive; its new footer reads Section B verified / 007 µg. The longer header wraps KEEP-ITALIC and moves subsequent content downward. The Agent explicitly records that layout change; native preservation does not imply identical layout.

The first independent audit incorrectly treated equivalent font-size values 9 and 9.0 as different requests. Numeric comparison was corrected with a regression test; the same 98-call trace then passed without rerunning the model. The original failed audit remains retained. New capabilities also exposed contract response truncation: complete policies now use hash-pinned contract_details pages, while the compact index retains every capability flag and schema continuation. Retained Codex audits accept read-only contract pages while still rejecting unauthorized writeback and missing required operations.

Opt in with python -m tests.codex_story_lifecycle.run --output /absolute/new-story-lifecycle-run --font-fixture /absolute/pinned-font-fixture; audit with python -m tests.codex_story_lifecycle.audit /absolute/new-story-lifecycle-run. Replay installed packages with scripts/smoke_docx_story_runtime.py and that run's workspace. Ordinary pytest never starts a model.

Final full suite: 3,315 passed, 33 optional skips in 357.08 seconds, including Writer/CJK and NIST/NASA PDFs. Python 3.10 focused group: 36 passed, one optional rendering skip. A clean wheel outside checkout reproduces ten complete stories, three structure records and both byte-identical historical Wikis at the exact actual-Codex source fingerprint; standard pip installation and SDK2 smoke also pass. VSIX: 199 tests, 64-file package check and install/update pass; local activation is delegated to CI. Local Impress/Calc are absent, so their three optional integration cases are skipped. Earlier full attempts encountered an expired corpus path, a legacy contract consumer and temporary-storage exhaustion; corrected wiring and per-test cleanup of successful temporary fixtures resolve them. Original error logs remain retained.

This synthetic case uses optional LibreOffice Writer and does not establish Microsoft Word fidelity, arbitrary-document coverage, every special clone dependency or footnote/endnote support. MCP checks source, version and structure; Agent owns full semantic/visual review and correction. Public 1.4.0 / Unreleased 1.4.x; next consolidated release 1.4.1.

### Native Word header/footer evaluation (Unreleased)

Actual default-model Codex processed a synthetic three-page, two-section Word document: a separate first-page header and blank footer, plus shared default stories on pages two and three. The shared header deliberately used a nonstandard part filename. After complete binding/content reads and initial page review, the Agent edited shared text, inserted and deleted paragraphs, and changed the page-number prefix. The run completed 75 successful MCP calls, zero tool errors and 165.22 seconds without a model override.

Independent audit checks eight complete story records, three managed revisions, two historical Wikis and all six actual PNGs. Complete paged hashes, native XML, unchanged package parts, source bytes/mtime, historical references, text selections and every Wiki attachment pass. Initial and final first-page PNGs are identical. Pages two and three show the corrected shared content, preserving bold/italic formatting, 007, -0.50 mg/L and the added REVIEWED 1,234.50. The native PAGE field cache remains 1; Writer evaluates and displays Verified page 2 and Verified page 3. Stored literal text and evaluated results are distinct evidence.

Opt in with python -m tests.codex_docx_stories.run --output /absolute/new-word-stories-run --font-fixture /absolute/pinned-font-fixture; audit with python -m tests.codex_docx_stories.audit /absolute/new-word-stories-run. Ordinary pytest never starts a model. Actual runs use authenticated Codex, optional Writer and the pinned private font fixture.

Final full suite: 3,268 passed, 33 optional skips in 325.91 seconds, including existing Writer/CJK and NIST/NASA PDF cases. New unit tests: 42 passed; SDK2 with both rendering configurations: two passed. Python 3.10: 43 passed and one optional rendering skip. A clean installed wheel outside checkout reproduces eight complete story records, two catalogs and both byte-identical historical Wikis, with the same source fingerprint as actual Codex.

This case does not test Microsoft Word, whole-definition creation/removal, section relinking or footnote/endnote stories. MCP checks source, version and structure; Agent owns full semantic/visual review. Public 1.4.0 / Unreleased 1.4.x; next consolidated release 1.4.1.

### Native Word pagination evaluation (Unreleased)

Actual default-model Codex received a native Word table with clipped rows and missing repeated headers. It read complete records and the initial page, then set the two-row header prefix, automatic body heights and prevent-split policy. The run completed 74 successful MCP calls with one recovered input error in 200.83 seconds, without a model override. A schema read requested text_limit12000 above the4000 limit; the Agent corrected it. Original errors remain retained, with no model rerun to erase them.

The corrected document spans four pages, repeating both headers. All14 rows retain visible END/CONFIRMED lines, 007, -0.50 mg/L, 1,234.50 and µg. Complete DFM/table XML/receipts for both revisions, five actual PNGs, historical verification, published DOCX and two historical Wikis were inspected. Independent audit checks every pixel, each row's page membership, repeated headings, unchanged native cell/style XML and other package parts, source bytes/mtime and every Wiki attachment.

This synthetic14-row case establishes that particular multi-page correction. Oversized single rows, all inherited styles, arbitrary real documents and Microsoft Word rendering remain unverified. MCP sets and checks native properties; Agent owns full semantic/visual judgment.

Opt in with python -m tests.codex_docx_layout.run --output /absolute/new-word-layout-run --font-fixture /absolute/pinned-font-fixture; audit with python -m tests.codex_docx_layout.audit /absolute/new-word-layout-run. Ordinary pytest never invokes a model. Actual runs require authenticated Codex, optional Writer and the pinned private font fixture.

Final full suite: 3,218 passed, 33 optional skips in 305.27 seconds, including actual Writer pages, CJK glyphs and NIST/NASA PDFs. New pagination/audit/SDK2 group: 34 passed; Python 3.10: 33 passed and one optional rendering skip. VSIX: 199 tests, 64-file package check and install/update passed; local activation was skipped and is required in CI. Public 1.4.0 / Unreleased 1.4.x.

### Native Word grid evaluation (Unreleased)

The final source includes complete paged mutation receipts. Initial run01 (61 successful calls / 174.05 seconds) remains retained. A long-receipt regression then exposed truncated delivery; the production fix justified the new run below, with the original failure preserved.

Actual default-model Codex on 2026-09-19 completed 70 successful MCP calls, zero tool errors and 162.73 seconds without a model override. It visually transcribed a scanned PDF page into native DOCX, inserted/deleted rows and columns, resized dimensions, merged complete paragraphs, split cells and restored widths. All three managed revisions had complete DFM/grid XML reads. Independent checks retained exact source bytes/mtime, historical references, untouched package parts, literal strings, rich formatting and every Wiki attachment.

One original scan PNG and two intermediate/final Writer page PNGs were delivered. Independent rendering matched every RGB pixel and checked Chinese glyphs in the pinned font fixture. Agent inspection found equal final columns, visible 007/-0.50/1,234.50/mg/L and no temporary row or column. This is a synthetic one-page case; cross-page repeated headers, arbitrary real Word documents and Microsoft Word rendering are not established.

The final full suite passed 3,184 tests with 33 optional skips in 290.27 seconds, including actual Writer/CJK and NIST/NASA PDF cases. The Python 3.10 focused group passed 59 tests. Regressions cover long receipts, recurring file hashes with newer receipts and rejection before committing an oversized complete review.

Opt in with python -m tests.codex_docx_grid.run --output /absolute/new-word-grid-run --font-fixture /absolute/pinned-font-fixture; audit with python -m tests.codex_docx_grid.audit /absolute/new-word-grid-run. Ordinary pytest never launches a model. Actual runs require authenticated Codex and optional LibreOffice Writer; the private font fixture changes no system settings. MCP checks mechanics; Agent coordinates full semantic/visual review. Public1.4.0 / Unreleased1.4.x.

### Captured ETL citation evaluation (Unreleased)

Actual default-model Codex on 2026-09-19 completed 52 successful MCP calls, two recovered input errors and 223.68 seconds. A fictional one-page PDF produced full span/table/figure snapshots, an XLSX string cell preserving 007 and one mixed-source APA Wiki. All three sources were read and viewed again after ETL deletion; six actual PNGs match independent original-page pixels. Source bytes/mtime, every portable attachment, full hash-paged readback, bibliography and unchanged Wiki reuse pass independent audit. The Agent visually identified the raster reading -0.50 mg/L; general extraction and semantic correctness are not established.

The two rejected calls supplied text_limit to native contract; complete schema discovery recovered. Initial auditing used mime_type instead of the actual MCP wire key mimeType and omitted read-only schema discovery. Both auditor assumptions were corrected with regressions, then the same retained trace passed; no model rerun erased the initial failure.

Reproduce with uv run python -m tests.codex_etl_csl.run --output /absolute/new-etl-run and replay tests.codex_etl_csl.audit. Ordinary pytest never starts a model. scripts/smoke_etl_snapshot_runtime.py replays retained evidence with an installed runtime outside checkout. Unit snapshots: 34 passed; real SDK2 ingestion/history: one passed in 38.65s. Full suite with NIST/NASA: 3,110 passed / 35 optional skipped in 289.41s, followed by seven passing auditor regressions. Public stays 1.4.0 / Unreleased1.4.x. Clean Python3.10 wheel and Docker replay all three historical images and the byte-identical Wiki outside checkout; source fingerprints match actual Codex. Docker uses read-only evidence, matching UID and optional Node without changing source permissions. VSIX199 tests, 64-file packaging and install/update pass; activation remains a CI check. Desktop/mobile zh/en guides and APA preview pass six retained browser screens. The first CI Python3.10 job exposed a test decoder treating SDK structured content as image metadata. Local reproduction confirmed it; the integration test now parses actual TextContent, checks PNG hashes and source refs, and covers both list-wrapped and unwrapped responses plus altered images. Production bytes and the actual/wheel/Docker source fingerprint are unchanged. Corrected Python3.10 snapshot/auditor/SDK2 group: 44 passed in 49.37s; Python3.13 auditor/SDK2: 10 passed in 40.13s. The initial failure is retained.

### CSL citation document evaluation (Unreleased)

On 2026-09-19 the actual default Codex model completed APA/Vancouver citation documents and two immutable Wikis in 38 successful MCP calls, one recovered tool error and 192.75 seconds. It viewed four PDF images before/after rotation, read the complete contract, page records and citation pages, and checked APA same-author/year disambiguation, ordering, bibliography and historical references. A truncated native schema hash was rejected and retrieved again; this was not a zero-error run. Human PDF bytes/mtime stayed unchanged and the original APA snapshot remained reusable after the managed source changed.

The first run is also retained: 167 successful calls, one recovered error and 221.2 seconds, including many redundant page reads that do not establish additional coverage. That run exceeded the CSL page limit; MCP now advertises typed bounds and the test prompt explicitly stops at null next_text_offset. Independent audit checks complete readbacks, images, original attachments, snapshot inventories, bibliography values and resource hashes. Forged excerpts and missing initial chunks have regression tests. The two-book/two-page fixture is explicitly fictional, not proof of real scholarly accuracy.

Reproduce with uv run python -m tests.codex_csl.run --output /absolute/new-csl-run; ordinary pytest never starts a model. scripts/smoke_csl_runtime.py checks the installed optional Node.js processor. Full suite: 3,075 passed / 35 optional skipped in 221.04s, including the actual NIST/NASA corpus. Clean Python3.10 CSL unit/audit/SDK2 group: 31 passed in 23.30s. Three outdated GitHub description fixtures were synchronized after an earlier full-suite failure; the complete rerun passed. Source hashes match checkout, wheel, actual Codex and Docker. The base container explicitly reports Node.js unconfigured; mounting an optional Node executable read-only passes real APA rendering. VSIX199 tests and install/update pass; local extension activation is unavailable and remains a CI check.

Browser checks cover 1440x1000 and390x844, Chinese/English guide switching, APA/Vancouver previews, nonblank content, no horizontal overflow, italics and APA hanging indent, with eight screenshots retained. These cases do not establish every journal, language or metadata combination. Agent review still owns bibliographic truth, semantic support, printed locator correspondence and final typography. Public1.4.0 / Unreleased1.4.x, with no new version tag.

### Real PDF corpus (Unreleased)

On 2026-09-19 the actual default Codex model used this checkout's MCP on unchanged public PDFs: [NIST SRM 1648a](https://tsapps.nist.gov/srmext/certificates/1648a.pdf), Table1 on PDF index4, and the [NASA Apollo11 mission report](https://ntrs.nasa.gov/citations/19700008096), Table3-I across indices17/18. NIST completed 234 successful calls, zero tool errors, 75 exact data cells in 283.58 seconds; NASA completed 232/0, 68 exact cells in 251.22 seconds. Source sizes, hashes and page counts are pinned. NASA retains its historical scan and imperfect OCR layer; expected strings were separately image-reviewed, never supplied to the model.

Agents viewed three complete pages and three chosen table regions, read all initial/final CSV fields, performed update/restore plus row/column insertion/deletion, and exported Wiki/source attachments and exact CSV bytes. Audit checks seven history events per table, BOM/CRLF, every intermediate byte revision, complete receipts, historical refs, immutable source bytes/mtime and three sampled region-to-value claims. All 143 data cells are checked; only each page's first-row value has a derivation, not every cell.

Preserve the failed NIST first workflow: transcription75/75 was correct, but the Agent edited the first column when the second was required (237 calls,256.27s); the byte audit rejected it. The retry explicitly states zero-based coordinates. NASA's initial SDK2 run exposed359 duplicated Length dictionaries, now proven against original stream bytes and reported; copied pages record canonicalization. Scan clip/full-page raster sampling also differs: exact independent direct-source pixels are required; full-page crop mean differences4.726/3.847 are diagnostic, not a universal less-than-one gate. Both paths use MuPDF; glyph bounds and complete string truth are separate checks.

Run tests.real_pdf.corpus with --directory /absolute/corpus --fetch explicitly; set ASSET_AWARE_REAL_PDF_CORPUS for tests/integration/test_real_pdf_corpus_stdio.py. Actual model runs use python -m tests.real_pdf.run --corpus /absolute/corpus --case nist-1648a (or apollo11) --output /absolute/new-run. Normal pytest downloads nothing and invokes no model. CI explicitly fetches/verifies both sources; offline parser/oracle cases run on Python3.10/macOS/Windows. Focused parser/oracle/SDK2: 31 passed in 72.10s. Full suite: 3,044 passed / 35 optional skipped in 198.26s. Clean Python 3.10: 31 passed in 74.86s plus installed-wheel CLI/SDK2 smoke. Corpus/trace/report IO explicitly uses UTF-8, with an additional non-UTF-8-locale subprocess regression. VSIX 199 tests, install/update and Docker SDK2 smoke pass; source hashes match checkout, wheel, actual Agent runs and container. These documents do not prove arbitrary-PDF fidelity. Public1.4.0 / Unreleased1.4.x.

### Native CSV/TSV evaluation (Unreleased)

The actual default Codex model completed 103 successful MCP calls, zero tool errors, 210.09 seconds and four actual region PNGs. It independently selected Count/Reading/Unit in an image-only synthetic PDF, reviewed two detail levels for Count, created a UTF-8-BOM/CRLF CSV with exact strings 007, -0.50 and mg/L, and recorded three region-to-field derivations.

Five native updates changed Count to 008, inserted a row, inserted a column, then deleted the added row and column. Independent audit checks all six history events against exact expected bytes, including LF for the temporary Unicode row, retained BOM/CRLF, every original/final field, full operation receipts/ledger, actual source pixels/glyph coverage, historical evidence, two Wikis and the published CSV. The final content SHA recurs from the first correction; operation history stays distinct. Human PDF bytes/mtime remain unchanged and assertions never migrate.

Regressions cover strict UTF-8/BOM/UTF-16/CP950/CP1252/Latin-1, mixed EOL/multiline/empty/ragged records, byte splices, source refresh/backed-up writeback, dialect-bound snapshots and long paged fields. Sole surviving empty fields retain required quoting. Rehashed wrong spans or numeric coercion still fail the independent auditor. All-enabled schema discovery remains within its existing response cap.

Full suite: 3,012 passed, 35 optional skips, 126.86 seconds. Clean Python3.10 SDK2 plus its focused unit group: 37 passed in13.91 seconds. Reproduce with uv run python -m tests.codex_delimited.run --output /absolute/new/run-dir; ordinary pytest never starts a model. The first remote CI exposed an outdated fake GitHub description after the documentation update; the fixture was synchronized and the final full suite passed. CSV regressions also join the explicit Python3.10/macOS/Windows inventories. That coverage exposed legacy [CSV NUL rejection](https://github.com/python/cpython/issues/97503); reversible one-character masking around the parser preserves original values, bytes and positions. Marker collisions and dialect variants are covered; actual Codex and package proofs were rerun. This synthetic scan/CSV fixture establishes no arbitrary OCR or spreadsheet rendering guarantee. Agent owns meaning and downstream interpretation. Public1.4.0 / Unreleased1.4.x.

### PDF region evidence evaluation (Unreleased)

Actual default-model Codex completed 82 successful MCP calls, zero tool errors, 218.02 seconds and 5 actual region PNGs. It selected three scanned cells, preserved strings 007, -0.50 and mg/L in a new workbook, and recorded three region-to-cell derivations. Higher-detail previews retained region identity. Changing A2 to 008 and rotating the managed PDF preserved the human source and historical evidence. Two Wiki snapshots retained original assertions without inheriting them into the new workbook revision.

Independent audits check complete page/cell/ledger readbacks, source bytes/mtime, glyph coverage, published XLSX and Wiki JSON/PNG/source attachments. Sixteen vector geometry cases compare exact full-page raster crops. Actual scan PNGs require exact independent direct-render replay plus full-page crop dimensions/mean-error comparison; partial embedded-image resampling and edge antialiasing can differ. The first audit rejected the completed run because it assumed universal pixel equality; the corrected audit rechecked the same raw trace. A regression rejects a one-pixel image shift even with an updated PNG hash. SDK2 additionally checks a fixed scan crop within 2/255 maximum and 0.1/255 mean error.

Full suite: 2,967 passed and 35 optional skips. Reproduce with uv run python -m tests.codex_pdf_regions.run --output /absolute/new/run-dir. Ordinary pytest never starts a model. This synthetic fixture does not certify arbitrary PDF or Excel fidelity; broad real-file coverage remains open. Public1.4.0 / Unreleased1.4.x.


### Worksheet layout correction evaluation (Unreleased)

Optional real Calc/SDK2 testing compares before/after PDFs, delivered MCP PNGs, exact source revisions and historical images. Set NATIVE_WORKBOOK_RENDER_TEST=1 and run tests/integration/test_native_worksheet_layout_stdio.py, with Calc installed or LIBREOFFICE_BIN set. Separate unit cases cover rich text, Tables, merges, styles, authored picture/note anchors, protection permissions and default-hidden rows.

Actual default-model Codex on the final source completed **125 successful MCP calls with zero tool errors in194.47 seconds**, viewing **9 actual MCP PNGs**. It chose36-point first rows on First/Last and raw OOXML width24 for Hidden columnA. Corrected images show the full colored titles and HIDDEN CONTENT. Independent audit checks four workbook versions, complete layout receipts/pages, unchanged cell contents/styles, historical PNGs, both PDFs and exact Wiki source attachments. Colored title pixels increased at the same PDF rendering scale.

An earlier run completed136 successful calls in170.34 seconds with **14 rejected schema requests** using text_limit12000. The limit is4000; contract schema_request supplies2000. Codex corrected the arguments and completed the workflow; the audit retains every failed call. After improving sparse row lookup, final-source testing produced the125-call zero-error result above. Neither run certifies Excel fidelity. Visual coverage is limited to this synthetic workbook; picture/note geometry is covered by separate unit cases.

Full pytest passed2,931 tests with35 optional skips; real Calc/SDK2 testing passed separately. Run uv run python -m tests.codex_workbook_layout.run --output /absolute/new/run-dir. Ordinary pytest never starts a model. Human sources and old PDFs remain unchanged. Public1.4.0 / Unreleased1.4.x.

### Workbook rendition evaluation (Unreleased)

The optional real Calc/SDK2 test covers all four print/whole-sheet and prefer-cache/recalculate combinations, actual PNG pixels, print areas, hidden/blank sheets, source bytes/mtime, historical revisions and portable Wiki provenance. Set NATIVE_WORKBOOK_RENDER_TEST=1 and run tests/integration/test_native_workbook_rendition_stdio.py with Calc installed; optionally set LIBREOFFICE_BIN.

On 2026-09-19 actual default-model Codex completed **232 successful MCP calls with zero tool errors in184.70 seconds**, receiving **11 actual MCP PNGs** across ten pages and one historical reread. It created cached print, recalculated whole-sheet and updated-formula PDFs, checked displayed999/3/5, complete source receipts/page records and historical cell evidence, then published three PDFs, one XLSX and a PDF Wiki retaining exact conversion inputs. Independent audit checks source immutability, both workbook revisions, PDF bytes, complete page records, delivered pixels and Wiki attachments.

Codex identified top-edge heading clipping and right-edge hidden-sheet text clipping in whole-sheet output. That earlier run left clipping uncorrected; the subsequent layout evaluation above now corrects this sample. Complete page counts do not certify visual fidelity, and broader corpus coverage remains open. Run uv run python -m tests.codex_workbook_rendition.run --output /absolute/new/run-dir. Ordinary pytest never starts a model. Public1.4.0 / Unreleased1.4.x.

### Native Table totals lifecycle evaluation (Unreleased)

Actual default-model Codex completed 201 successful MCP calls with zero tool errors in 181.76 seconds. It viewed a synthetic scanned PDF through an MCP PNG, created an independent workbook/Table, removed and cleared totals, restored retained definitions, then removed totals while keeping cells.

Independent openpyxl/ZIP/trace audits checked five history entries, complete reference/receipt reads between mutations, ten exact source strings/types, column IDs, filter ranges, formulas and styles. The retained totals formula uses absolute pre-removal data coordinates. Historical 007 evidence, original PDF bytes/mtime, final XLSX and two immutable Wiki attachments all passed. The suite passed 2,834 tests with 33 optional skips, including SDK2, CAS conflicts and public readback budget rejection.

This actual Codex fixture uses default direct cell styles; richer styles have separate unit coverage. Excel rendering and calculated results were not verified. Reproduce with uv run python -m tests.codex_table_totals.run --output /absolute/new/run-dir. Ordinary pytest never launches a model. Public stays 1.4.0 / Unreleased within 1.4.x.

### Native Table creation evaluation (Unreleased)

Actual default-model Codex viewed a synthetic scanned PDF through an MCP PNG, created an independent XLSX and added a native Inventory Table through add_workbook_table. The run completed 73 successful MCP calls with zero tool errors in 109.47 seconds. No prebuilt Table template was supplied.

Independent openpyxl/ZIP and trace audits checked ten exact source strings and types, leading zeros, six column IDs, Table/filter ranges, calculated/totals formulas, Table style and preserved cell formats/parts. Complete paged reads, the original historical 007 reference, source PDF bytes/mtime and both revision Wikis with exact attachments passed. The full suite passed 2,764 tests with 33 optional skips. An openpyxl empty workbookProtection compatibility failure was reproduced and fixed while retaining active/password/unknown protection guards.

This synthetic first-page workflow does not establish general OCR accuracy, Excel rendering or recalculated results. Reproduce with uv run python -m tests.codex_table_create.run --output /absolute/new/run-dir. Ordinary pytest never launches a model. Public remains 1.4.0 / Unreleased within 1.4.x.

### Native Table column editing evaluation (Unreleased)

Actual Codex completed 66 successful MCP calls, zero tool errors, in 132.75 seconds. It viewed the synthetic scan through an actual PNG, transcribed ten data cells as exact strings into a supplied Table, then renamed the rich Count header to Quantity, changed the calculated formula and edited existing totals in one specialized operation. Bold/italic run formats, source data, native styles, column IDs and Table/filter bounds survived. Existing formula/defined-name references followed the renamed identity.

Independent openpyxl/ZIP and trace audits checked complete reads, receipts, historical Count/007 references, original PDF/XLSX bytes and mtimes, and two revision Wikis with exact attachments. The first audit incorrectly named the schema operation; a later check caught an intermediate formula recorded as before. The corrected implementation was rerun and now proves original-revision before values. Combined public readback size is checked before commit. The final source passed 2,716 tests with 33 optional skips and matches the wheel and Docker code. This uses a supplied Table and does not establish native Table creation, Excel rendering or recalculated results.

Reproduce with: uv run python -m tests.codex_table_edit.run --output /absolute/new/run-dir. Ordinary pytest never launches a model. Public remains 1.4.0 / Unreleased within 1.4.x.

### Native Table expansion evaluation (Unreleased)

Actual Codex CLI completed 82 successful MCP calls with zero tool errors in 150.48 seconds. It viewed the synthetic scan through an actual MCP PNG and transcribed ten data cells as exact strings into a supplied Inventory Table template with a CountLength calculated column. Template preparation is not counted as native MCP table creation.

The agent read complete table definitions/references, projected A2T, changed 007 to 008 and added one row and one Review column. Explicit per-step part/expected_ref expansion and native_generated intent produced one native commit with A1:G4 Table/filter membership, retained column IDs, generated F4 formula and G1 Column7 header. Independent openpyxl/ZIP checks verified 20 source/manual strings and their types, formulas, identities, styles and unchanged parts.

The audit checks complete paged reads, current receipts, frozen and live A2T, historical 007 evidence, unchanged source PDF/XLSX bytes and mtimes, and two native revision Wikis with attachment hashes. Native Excel rendering and calculated results were not evaluated. Regression fixtures additionally cover totals, sorting, adjacent Tables, non-UTF-8 definitions, boundaries, pivot/mapping guards, stale revisions and invalid generated intent.

Reproduce with: uv run python -m tests.codex_table_expansion.run --output /absolute/new/run-dir. Ordinary pytest never starts a model. The isolated runner uses the current checkout and default Codex model; tests.codex_table_expansion.audit verifies results independently. Public stays 1.4.0, with development Unreleased for 1.4.x.

### Structural A2T writeback evaluation (Unreleased)

Run tests/unit/test_native_table_grid_apply.py and tests/integration/test_native_table_grid_stdio.py for renamed/recreated identities, identical row recreation, native formula relocation, rich text/styles, complete destination reads, version conflicts and historical snapshots. SDK2 sends typed JSON column defaults and checks one native commit.

Explicit model run: uv run python -m tests.codex_native_selection.run --table-grid --output /tmp/table-grid-codex; replay tests.codex_native_selection.audit. Run 01 on 2026-09-19 made **86 tool calls: 84 successful and two recovered input errors**, in **178.67 seconds**. Codex viewed the scan PNG, retained the original 007 selection/derivation, edited B2 to 008 in A2T, deleted/recreated a row and column, added manual data and applied everything in one native commit. Independent audit checks the original 15 and final 20 literal cells, stable identities, complete before/after reads, the native operation receipt, frozen A2T input, source PDF bytes/mtime and two historical Wikis. Old assertions never migrate.

The two rejected discovery calls passed table_data/table_manage to native contract.for_op, which accepts only native operation names; Codex recovered using their exposed MCP tool schemas. CLI 0.154.0-alpha.6.1 uses its default model. This actual model fixture has no native Excel Table object and does not certify general OCR, formula evaluation or Excel rendering. Rich native formulas/styles have separate package tests. Public stays 1.4.0 / Unreleased within 1.4.x.

### Native worksheet grid evaluation (Unreleased)

Run tests/unit/test_native_grid_*.py, tests/unit/test_native_workbook_grid.py and tests/integration/test_native_grid_stdio.py. They cover native row/column insertion and deletion, formula and table identities, merges, notes/drawing geometry, named sources, complete paged readback and version conflicts. Independent openpyxl inspection never resaves the source package.

Explicit model run: uv run python -m tests.codex_native_selection.run --grid --output /tmp/grid-codex; replay tests.codex_native_selection.audit. Run 01 on 2026-09-19 completed **126 successful MCP calls, zero tool errors, 175.95 seconds**. Codex viewed the actual scan PNG, created 15 literal cells, changed B2 from 007 to 008, then inserted and deleted rows/columns. Independent audit verifies all intermediate values/blanks, complete pinned reads, current operation receipts, history, source bytes/mtime, old references/derivations and two revision-specific Wikis.

Deleting the newly inserted blanks returned to an earlier content SHA. The auditor therefore checks the current history event as well as immutable bytes. An initial auditor bug rejected exploratory reads; corrected auditing permits exploration but still requires complete pinned reads before every mutation. Regressions reject missing current receipts and reused proof for repeated hashes. CLI 0.154.0-alpha.6.1 uses its default model. This synthetic case does not certify general OCR, Excel rendering, formula evaluation or structural A2T writeback. Public stays 1.4.0; development remains Unreleased for 1.4.x.

### Native A2T correspondence evaluation (Unreleased)

Run tests/unit/test_native_table_*.py, tests/unit/test_codex_table_audit.py and tests/integration/test_native_table_stdio.py. They cover typed JSON tool inputs, exact source-cell evidence, unchanged native parts, rich-text/merge guards, stale revisions, independent creation and frozen input recovery after live table deletion.

Explicit model run: uv run python -m tests.codex_native_selection.run --tables --output /tmp/a2t-codex; replay tests.codex_native_selection.audit. Run 01 on 2026-09-19 made **90 MCP calls: 89 successful and one recovered input error**, in **145.14 seconds**. Codex viewed the scan PNG, transcribed all 15 literal cells, projected A2T, changed string 007 to 008, applied it to the original workbook and created an independent XLSX from its frozen input. The rejected schema request used text_limit=20000; subsequent valid paging completed the workflow.

Independent audit verifies complete reads before writes, typed values, source references, immutable A2T snapshots, original PDF bytes/mtime, native history, unchanged parts, both outputs and two revision-specific Wikis. The old 007 assertion never migrates to 008. CLI 0.154.0-alpha.6.1 uses its default model; no general OCR, formula evaluation or Excel rendering guarantee. Public stays 1.4.0; development remains Unreleased for 1.4.x.


### Native workbook structure evaluation (Unreleased)

Run tests/unit/test_native_workbook_*.py, tests/unit/test_codex_workbook_audit.py and tests/integration/test_native_workbook_stdio.py. Rich native fixtures cover formulas, styles, comments, merges, charts, pivots/consolidation, 3D ranges and source/version preservation. SDK2 exercises complete paged read-back, worksheet CRUD and historical selected-value verification with independent workbook inspection.

Explicitly opt into the real model with uv run python -m tests.codex_native_selection.run --worksheets --output /tmp/workbook-codex. Replay tests.codex_native_selection.audit against that directory. Run 01 on 2026-09-19 completed **115 MCP calls, zero tool errors, 160.49 seconds**. Codex viewed an actual scan PNG, created all 15 literal XLSX cells, retained the original 007 selection and updated B2 to 008. It added Review/Temporary sheets and a native cross-sheet formula, renamed Sheet1 to 資料 O'Brien, reordered the workbook and deleted Temporary.

Independent audit checks all seven native revisions, literal values, stable sheet IDs/parts, exact formula rewriting, unchanged parts, complete reads before/after edits, source bytes/mtime, published output and two revision-specific Wiki snapshots. Regression tests reject late reads, forged revision transitions and hashes. Codex CLI 0.154.0-alpha.6.1 used its default model, not a pinned model. No general OCR, formula evaluation or Excel rendering claim; source evidence covers the whole scanned page. Ordinary pytest never starts Codex. Public remains 1.4.0 / future 1.4.x.

### Native selection evaluation (Unreleased)

Run tests/unit/test_native_selection.py, tests/unit/test_native_selection_service.py, tests/unit/test_codex_selection_audit.py and tests/integration/test_native_selection_stdio.py. Explicitly opt into a real model with uv run python -m tests.codex_native_selection.run --output /tmp/selection-codex; replay with tests.codex_native_selection.audit. Ordinary pytest never starts Codex.

Run 01 on 2026-09-19 completed **58 MCP calls, zero tool errors, 130.45 seconds**. Codex viewed a real scan PNG, transcribed all 15 literal XLSX cells, selected B2's original count and changed B2 to 008. The old 007 selection remained historical. Independent audits checked complete PNG pixels, every native string, source bytes/mtime, paged parent/selection/ledger reads, context hashes, published output and two revision-specific Wiki snapshots. The historical Wiki retains selection JSON and the exact source PDF; the current Wiki inherits no old assertion. Rehashed forged values, locators and context fail the auditor's regression tests.

SDK2 separately exercises precise text in a merged-title PPTX table, edits, historical proof and source preservation. All four parent formats and Unicode/UTF-8 spans have regressions. Codex CLI 0.154.0-alpha.6.1 used its default model, not a pinned model. Synthetic coverage does not establish general OCR, pixel-region evidence, automatic cell alignment or Excel visual fidelity. Public remains 1.4.0 / future 1.4.x.
A release candidate must pass lint, formatting, types, full tests, documentation checks, security audits, package audits, VSIX tests, and artifact verification. Install and activation smoke tests validate the production extension path.

## Codex PDF evaluation
Run \`uv run python -m tests.codex_pdf.run --mode scanned --output /tmp/pdf-codex-scanned\` from a checkout with a logged-in Codex CLI. The output directory must be new; use \`--codex /absolute/path/to/codex\` if needed. This explicit opt-in uses model quota. Ordinary pytest never starts Codex.

The runner connects only the current checkout's MCP server to synthetic data, captures actual image/tool events, and independently checks final transcription, citations, edit/delete/restore history, source hashes, scan pixels, reopened Excel and asset bundles. Re-run the independent auditor with \`uv run python -m tests.codex_pdf.audit /tmp/pdf-codex-scanned\`.

Main development adds \`citation_readback_required\`: after all corrections, Codex must use \`table_cite read\` for every final Reading cell. The independent auditor checks complete MCP pages, hash continuity, stable cell binding and equality with persisted references. \`citation_paging_required\` also requires at least one actual continuation using 200-character pages. Historical runs retain their original eight checks; they do not retroactively prove this new capability.

Recovered tool errors remain visible as \`passed_with_recoveries\`; \`first_transcription_exact\` distinguishes initial extraction from a corrected final result. The three-page corpus covers digital, scanned and mixed pages, rotation/cropbox offsets, leading zeros, signs and units. It does not establish general OCR accuracy, handwriting support or PDF layout writeback fidelity.

## Codex native PDF evaluation (Unreleased)
Run \`uv run python -m tests.codex_native_pdf.run --codex /absolute/path/to/codex --output /tmp/native-pdf-run\` for the separate native page workflow. Three image-only pages require actual MCP PNG delivery, complete page JSON, a new composed PDF, two blank insertions, rotation, deletion, reordering, historical verification, publication and wiki export. The original source must remain unchanged. Ordinary pytest never invokes a model.

Re-audit with \`uv run python -m tests.codex_native_pdf.audit /tmp/native-pdf-run\`. Independent checks inspect actual image pixels, contiguous reference readbacks, persisted lineage/history, source hash/mtime, final page order/geometry/pixels, wiki files and exact string transcription. Unicode µ/μ is not normalized. Keep raw events, runtime/lock hashes, artifacts and tool errors, including failed runs. These synthetic checks do not establish arbitrary PDF fidelity or general OCR accuracy.

On 2026-09-18, native scanned run 02 against the final worker completed 49 MCP calls with zero tool errors. All seven independent checks passed, including ten full page records, six actual original/final images, and exact final transcription of seven rows/35 cells. Images were independently compared to their pinned-revision render pixels. Earlier run 01 retained 171 calls and its passing evidence; call counts depend on the model's paging strategy.

## Codex PPTX picture evaluation (Unreleased)
Run \`uv run python -m tests.codex_pptx_pictures.run --codex /absolute/path/to/codex --output /tmp/pptx-picture-run\`. The logged-in CLI uses only the native document MCP tool. A synthetic raster with leading zeros is inserted twice into a complex deck, viewed as actual MCP images, extracted, replaced on only one shape and deleted on the other. Full shape reads, historical references, exact image bytes, shared-media isolation, unchanged shapes/parts and wiki artifacts are independently audited. Ordinary pytest never starts Codex. Embedded-image verification does not establish slide rendering or general OCR accuracy. Two runs on 2026-09-18 each completed 38 MCP calls with zero tool errors, three actual image deliveries and two complete shape records; exact leading-zero visual transcription and the independent package audit passed.

## Codex scanned PDF to PPTX table evaluation (Unreleased)
Run \`uv run python -m tests.codex_pptx_tables.run --codex /absolute/path/to/codex --output /tmp/pptx-table-run\`. The actual CLI views a scanned first-page PNG, creates editable tables with a merged title, reads full native representations, edits/restores a cell, deletes a duplicate, verifies old/source evidence and publishes PPTX/wiki. Independent audits check exact strings, pixels, grids/merges, reference chronology and managed history. Ordinary pytest never starts a model.

Run 01 on 2026-09-18 made 67 attempts / 66 successful calls, with exact initial transcription and one recovered citation-format input error. The agent initially put source proof objects into citation_contract; the typed display schema now advertises the valid selectors/templates. Recovery remains visible as passed_with_recoveries. Run 02 with the typed schema completed 66 calls with zero tool errors, exact first transcription, one actual scanned PNG and four distinct complete evidence records. Both runs pass the final PPTX/wiki/history audit. This synthetic case does not establish general OCR accuracy or complete slide visual fidelity.

## Codex native derivation evaluation (Unreleased)
Add \`--derivations\` to the scanned-table runner. The actual agent reads final table/page evidence and complete ledgers, records and supersedes a source-to-table assertion, adds/retracts a temporary assertion, verifies historical/active states and exports exact source attachments. Independent checks bind operations to prior complete readbacks, ledger hashes and actual MCP results. Ordinary tests never start a model; semantic support and full slide rendering remain agent review work.

On 2026-09-18, derivations run 02 completed 93 MCP calls with zero MCP tool errors and exact first transcription. Independent checks passed for one scanned PNG, five full component records, four ledger events, one retained assertion and exact source PDF attachment. The agent separately reported correcting a local orchestration syntax error; the event stream has no independent tool record for it, so the statement remains in agent_reported_limitations rather than being counted as an observed MCP error.

A second run (03) against the same initial ledger runtime completed 92 MCP calls with zero tool errors and exact first transcription. The same one-image, five-record, four-event, single-active-assertion and exact-source-attachment audits passed. Neither run claims full slide rendering verification.

Run 04 against the final runtime preserving native source extensions completed 96 MCP calls with zero MCP tool errors and exact first transcription. Table/ledger/source audits passed. An initial auditor incorrectly rejected a preview followed by a fresh complete read from offset zero; three regressions now accept that restart while still rejecting gaps and wrong hashes. The original failed audit is retained. The model separately reported correcting an over-escaped font diagnostic; this remains a caller statement, not proof of slide fidelity.

## Native table grid exercise (Unreleased)

Add --grid to tests.codex_pptx_tables.run for five actual Codex mutations after scanned-table creation: insert a column, insert a temporary row, resize both dimensions, delete the row and delete the column. Every mutation uses a current full reference and complete readback. Independent checks open all five intermediate PPTX revisions and compare literal strings, merged title coverage, dimensions, surviving cell XML/formatting, surrounding XML and untouched parts. Final source/history/wiki checks still apply. It can be combined with --derivations. This synthetic scan does not establish full slide rendering or real-corpus coverage.

Grid run 01 on 2026-09-19 completed 123 MCP calls with zero tool errors, exact first transcription, one actual PNG and nine complete records. All five intermediate grids passed independent content, merge, geometry and preserved-XML audits, together with source/history/published-file/wiki checks. The full Python suite passed 1,971 tests with 30 optional skips; extension tests passed 199. No full-slide rendering claim is made.

## Native table merge/split exercise (Unreleased)

Add --merges to tests.codex_pptx_tables.run, optionally with --grid and --derivations. Six mutations insert a temporary formatted row, merge its five cells with explicit paragraph migration, split it while keeping all text at the anchor, delete it, then split and remerge the original title. Each mutation uses a complete current reference and full readback. Independent audits inspect every intermediate PPTX for exact paragraph XML, rich formatting, ordering, original scanned cells, grid/frame/merge geometry and untouched XML/parts. Auditor regressions deliberately corrupt leading zeros, formatting, merge coverage and split content. Ordinary pytest never starts a model; live events, transcription errors and recoveries remain separate. Full slide rendering remains a separate check.

Merge run 01 on 2026-09-19 (--grid --merges) completed 180 MCP calls with zero tool errors, exact first transcription, one actual PNG and thirteen complete records. Five grid and six merge/split intermediate revisions passed independent audits of paragraph XML, original strings/styles, source, published files and wiki. No full-slide rendering was performed. Full pytest passed 2,015 tests with 30 optional skips; one subsequent absent-anchor-body regression passed within an 18-test focused run, with production source unchanged. VSIX tests passed 199.

## CJK font correction evaluation (Unreleased)

The first Writer evaluation found boxes for 「研究」. No Chinese font was available;
Arial resolved to Liberation Sans. Even those boxes had nonzero PDF glyph IDs and
misleading Unicode mappings, so text extraction alone could not prove appearance.
The opt-in Linux fixture below supplies pinned Noto Sans TC Regular/Bold and copied
local Liberation Sans faces. It retains both licenses, hashes all font/configuration
bytes and includes only those font directories; global settings and DOCX run fonts
remain unchanged. A changed or unexpected font file causes the audit to fail.

\`\`\`bash
# Requires Linux, Fontconfig, Liberation Sans and LibreOffice Writer.
uv run python -m tests.codex_docx_structure.fonts --output /tmp/docx-review-fonts
NATIVE_DOCX_FONT_FIXTURE=/tmp/docx-review-fonts uv run pytest tests/integration/test_native_docx_cjk_stdio.py -q
LIBREOFFICE_BIN=/usr/bin/libreoffice uv run python -m tests.codex_docx_structure.run --render --font-fixture /tmp/docx-review-fonts --output /tmp/docx-codex-cjk
uv run python -m tests.codex_docx_structure.audit /tmp/docx-codex-cjk
\`\`\`

The setup command explicitly downloads about 11 MiB from the official
[Noto Sans 2.004 source](https://github.com/notofonts/noto-cjk/tree/523d033d6cb47f4a80c58a35753646f5c3608a78/Sans/SubsetOTF/TC),
verifies fixed hashes and copies installed Latin fonts. Keep the generated directory
for replay; choose a new directory to rebuild. No fonts are bundled in this project,
and ordinary pytest never downloads them. The runner forwards the private
[Fontconfig configuration](https://fontconfig.pages.freedesktop.org/fontconfig/fontconfig-user.html)
to its MCP process; the auditor restores the same recorded environment and checks
its hashes before and after rendering. Fontconfig cache UUIDs are permitted without
relaxing font-content checks. This does not standardize other platforms or scripts.

CJK run 01 on 2026-09-19 completed **49 MCP calls with zero tool errors**, one scan
PNG and two Word page PNGs at current/historical revisions. Codex reported readable
Chinese glyphs in both images; it preserved exact table values and saw no clipping.
Independent rendering matched every delivered RGB pixel and confirmed both Chinese
codepoints using distinct glyphs from the supplied Noto face. The separate SDK2
regression compares missing-font and corrected renderings of **identical DOCX bytes**
and preserves source bytes/mtime. Native content, five complete DFM revisions,
historical references, publication and wiki attachments also passed the model audit.

These are complementary checks: parsed text/font identities are mechanical evidence;
actual appearance is reviewed by the Agent. Word compatibility, different installed
fonts, repeated-header pagination and real-corpus coverage still require evaluation.
The original missing-glyph run below is retained as historical evidence; the private
fixture corrects that case without changing the machine's default font environment.
Public remains **1.4.0**, with new work Unreleased for **1.4.x**.

Local CJK gates passed **2,221 Python tests** (33 optional skips), the **37-test**
focused run including actual CJK SDK2 images, **199 extension tests**, lint/type,
workflow/dependency/harness checks and desktop/mobile zh/en browser review. Runtime
source and dependencies are unchanged from the previously verified page renderer.

## DOCX page rendering evaluation (Unreleased)

Add \`--render\` to \`tests.codex_docx_structure.run\` to make Codex view every page
of the final DOCX and the historical revision with the temporary \`008\` Count.
The isolated MCP server receives an explicit \`LIBREOFFICE_BIN\` when set. The
independent auditor reconverts exact stored bytes, checks every delivered RGB
pixel and verifies complete page coverage, revision identity, PNG hashes,
continuation, renderer metadata and the Agent's stated review scope.

\`\`\`bash
NATIVE_DOCX_RENDER_TEST=1 uv run pytest tests/integration/test_native_docx_render_stdio.py -q
LIBREOFFICE_BIN=/usr/bin/libreoffice uv run python -m tests.codex_docx_structure.run --render --output /tmp/docx-codex-render
uv run python -m tests.codex_docx_structure.audit /tmp/docx-codex-render
\`\`\`

Rendering run 01 on 2026-09-19 completed **47 MCP calls with zero tool errors**:
one source scan PNG and two Writer page PNGs across final/historical revisions,
with complete DFM reads for all five managed revisions. All delivered Word pixels
matched independent rendering. Table strings, merged title/grid, \`007\` versus
\`008\`, source integrity, published bytes and wiki attachments passed the audits.
Agent review detected **missing Chinese heading glyphs** on this machine; both
Writer previews showed boxes for 「研究」 while the stored text was correct. This
is an unresolved local font limitation, not a Word fidelity pass. Install suitable
fonts in the rendering environment and repeat visual review before relying on
those glyphs. The separate real SDK2 test covers two pages, headers/footers and
historical/current previews; the synthetic Codex document was one page per revision.
Neither check establishes Microsoft Word fidelity or real-corpus coverage.

Final page-preview gates on 2026-09-19 passed **2,210 Python tests** (32 optional
skips; Writer and Impress SDK2 image tests also passed separately), **199 extension
tests**, source/type/security/dependency checks, clean-wheel CLI/SDK2, Docker
CLI/SDK2, artifact audits and fresh/update VSIX install. Local GUI activation was
unavailable; remote CI covers that check. Public remains 1.4.0, with no new tag.

## Native DOCX structure evaluation (Unreleased)

Run tests.codex_docx_structure.run with a new --output directory to have the logged-in Codex CLI transcribe a synthetic scanned PDF page into a new editable DOCX table. It changes/restores a cell, inserts/deletes disposable body blocks, verifies old evidence and exports a wiki. Only native document MCP access is enabled; ordinary pytest never invokes Codex.

The independent tests.codex_docx_structure.audit checks actual source PNG pixels, exact strings, rich formatting, grids, merges, every managed revision, complete DFM reads before edits, full references, published bytes and wiki attachments. Add --render for the page review described below; real-corpus coverage remains open. Public stays 1.4.0 / Unreleased for 1.4.x.

Run 01 on 2026-09-19 completed **45 MCP calls with zero tool errors**, one actual
source PNG and complete DFM readback for all five managed DOCX revisions. Exact
transcription, leading zeros, half-point Arial runs, merged title/grid, temporary
insert/delete, old evidence, published bytes and all 17 wiki package attachments
passed independent checks. Codex also exported a source PDF wiki and verified a
whole-file reference; the auditor accepts these additional valid outputs. It
explicitly reported that DOCX page rendering/page flow were not reviewed.


Final local gates passed on 2026-09-19: **2,156 Python tests passed, 31 optional
skipped**; extension **199 passed**. Ruff, mypy, dependency/security gates, Docker
CLI/SDK2 stdio, fresh/update VSIX install and clean-wheel CLI/stdio checks passed.
Local GUI activation was unavailable; CI runs that check. No public version bump.

## Whole-slide rendering evaluation (Unreleased)

Use --render with tests.codex_pptx_tables.run to make the real Codex CLI view
both the final slide and a historical slide through render_pptx_slide.
The runner forwards an explicitly set LIBREOFFICE_BIN to its isolated MCP server.
The auditor independently converts the exact stored PPTX revisions with LibreOffice,
uses raw ZIP slide relationships and PyMuPDF, and compares every delivered RGB pixel.
It checks revision/slide identity, image hashes, actual MCP image delivery and the
Agent's declared review scope. Agent observations remain judgments, not machine proofs.

Run 01 on 2026-09-19 completed **78 MCP calls with zero tool errors**, exact first
scan transcription, five complete native records and three actual images: one PDF
page and two whole-slide previews at distinct revisions. Source bytes/mtime,
published PPTX, history, old references and wiki checks passed. Codex identified
that a historical native 008 edit was hidden by a second overlapping table, so
both screenshots visibly showed 007. It also reported that the new table's blue
style and equal column widths differed from the scanned original. This illustrates
why XML readback and visual review answer different questions.

The local renderer was LibreOffice 7.3.7 with matching Ubuntu Impress/Draw modules in
a private test overlay; the installed system originally had Writer only. No system
installation was changed. An SDK2 integration test separately checks hidden-slide
and reordered-slide colors plus historical image stability; enable it with
NATIVE_PPTX_RENDER_TEST=1 and a usable Impress installation. CI installs Impress
for that test. Ordinary pytest never starts Codex. Full local suite: **2,095 passed,
30 optional skipped**; extension: **199 passed**. No PowerPoint, animations, media
playback, general OCR or real-corpus coverage is claimed. Public version stays 1.4.0.

## Native slide structure exercise (Unreleased)

Add --slides to tests.codex_pptx_tables.run, optionally with grid/merge/derivation exercises. After scanned-table creation, Codex discovers layouts, inserts two formatted temporary slides, reorders all slide identities and deletes the temporary slides. It fully reads slide listings before/after each mutation, complete temporary shapes and the original table, then verifies deleted-shape historical evidence. Independent audits inspect raw ZIP relationships/XML for all intermediate slide IDs/order, exact strings/leading zeros, formatting/geometry, original parts, content types, relationships and count properties. A regression exposed python-pptx's in-memory slide-part renaming after reorder; the auditor now reads original package relationships. Synthetic scan results do not establish general OCR accuracy or full slide rendering.

Slides run 01 on 2026-09-19 completed 96 MCP calls with zero tool errors, exact first transcription, one actual PNG and eight complete shape/page records. All three intermediate presentations passed independent identity/order, rich text, preserved-parts, historical evidence and final published-file/wiki audits. Full pytest passed 2,068 tests with 30 optional skips; VSIX tests passed 199. No presentation-viewer rendering was performed.



## Publish in order
Confirm built artifacts and runtime diagnostics before tagging, then verify each public registry after publication.`,
  "mcp-tool-consolidation": `## Understand the surfaces
Balanced mode exposes 30 public tools, compact mode exposes 17 operation-based facades, and legacy mode retains 63 direct compatibility names. These are tool UX policies on the same MCP SDK 2 runtime.

## Preserve compatibility
Keep operation payloads, source identity, job semantics, and citation fields stable when routing a direct tool through a facade.`,
  "code-map": `## Find the implementation
Domain, application, infrastructure, presentation, extension, and script sections identify the files that own each major capability. Start with the public tool module, then follow its service and adapter dependencies.

## Find verification
Use nearby focused tests and release scripts to confirm the behavior and packaging boundary you are changing.`,
});

const CATEGORY_META = {
  document: {
    en: "Document core",
    zh: "文件核心",
    summary: "PDF/DOCX routing, assets, sections, ingest, and retrieval",
  },
  citation: {
    en: "Citation",
    zh: "引用與證據",
    summary: "Find, verify, bundle, and promote evidence",
  },
  docx: {
    en: "DOCX / DFM",
    zh: "DOCX / DFM",
    summary: "Reversible Word ingest, editing, validation, and table bridges",
  },
  table: {
    en: "A2T tables",
    zh: "A2T 表格",
    summary: "Plan, manage, cite, draft, and audit reusable tables",
  },
  job: {
    en: "Jobs / conversion",
    zh: "Jobs / 轉換",
    summary: "Background lifecycle and document conversion",
  },
  knowledge: {
    en: "Knowledge / profile",
    zh: "Knowledge / Profile",
    summary: "Opt-in discovery, source selection, and ETL profiles",
  },
};

function defineTool(name, category, summary, inputs, outcome, example, module) {
  return { name, category, summary, inputs, outcome, example, module };
}

const TOOLS = [
  defineTool("document", "document", "Document facade for PDF workflows, native file versions, DOCX/PPTX evidence and wiki snapshots (v1.4.0).", "op, pdf_path, doc_id, file_paths, output_dir, native_request", "PDF assets or native file revisions with explicit preservation checks", 'document(op="export_assets", doc_id="doc_...", output_dir="agent-assets")', "document_tools.py"),
  defineTool("document_asset", "document", "Fetch document assets, navigate sections, and write table or figure Foam notes.", "op, doc_id, asset_type, asset_id, path", "Bounded asset content or provenance-rich Foam notes", 'document_asset(op="foam_notes", doc_id="doc_...", asset_type="all")', "document_tools.py"),
  defineTool("section", "document", "Browse, search, and read a document section tree.", "op, doc_id, path, query, limit", "Section hierarchy, detail, content, or bounded blocks", 'section(op="tree", doc_id="doc_...", max_depth=3)', "section_tools.py"),
  defineTool("ingest_documents", "document", "High-frequency PDF ingest shortcut with background-job semantics.", "file_paths, async_mode, use_marker, ocr_enabled, ocr_language", "Job id and per-file progress without blocking stdio", 'ingest_documents(file_paths=["/papers/source.pdf"])', "document_tools.py"),
  defineTool("list_documents", "document", "List persisted documents and their basic readiness metadata.", "none", "Bounded document inventory", "list_documents()", "document_tools.py"),
  defineTool("parse_pdf_structure", "document", "Run the configured structured PDF extractor; held engines fail closed.", "pdf_path, output_dir, async_mode", "Structured parse job or explicit backend diagnostic", 'parse_pdf_structure(pdf_path="/papers/source.pdf")', "document_tools.py"),
  defineTool("fetch_document_asset", "document", "Read one table, figure, section, or bounded full-text asset.", "doc_id, asset_type, asset_id, max_chars", "TextContent, ImageContent, or artifact pointer", 'fetch_document_asset(doc_id="doc_...", asset_type="figure", asset_id="fig_1")', "document_tools.py"),

  defineTool("evidence", "citation", "Evidence facade for find, verify, bundle, locate, health, and claim promotion.", "op, doc_id, query, ref, wiki_root", "Bounded evidence response or persisted canonical pack", 'evidence(op="find", doc_id="doc_...", query="primary outcome")', "document_tools.py"),
  defineTool("citation_bundle", "citation", "Export verified evidence as JSON, Markdown, or Foam.", "doc_id, query, span_id, output_format, wiki_root", "Bounded inline preview or persisted exact-quote bundle", 'citation_bundle(doc_id="doc_...", output_format="foam", wiki_root="/wiki")', "document_tools.py"),
  defineTool("find_evidence_spans", "citation", "Find indexed spans; large quotes return explicit noncanonical previews.", "doc_id, query, span_id, span_kinds, limit", "Canonical small AssetRefs or asset-ref-preview-v1", 'find_evidence_spans(doc_id="doc_...", query="outcome")', "document_tools.py"),
  defineTool("verify_citation_ref", "citation", "Fail-closed verification of an exact span AssetRef.", "ref", "Locator, quote, hash, revision, and type verification", "verify_citation_ref(ref=asset_ref)", "document_tools.py"),

  defineTool("docx", "docx", "DOCX facade for ingest, read, save, list, delete, and validate.", "op, file_path, doc_id, dfm_content, output_path", "DFM content, validation, or guarded writeback", 'docx(op="ingest", file_path="/docs/source.docx")', "docx_tools.py"),
  defineTool("docx_table", "docx", "Bridge DOCX tables and charts to A2T contexts.", "op, doc_id, block_id, table_id", "TableContext, chart data, or edit plan", 'docx_table(op="to_context", doc_id="docx_...", block_id="tbl_1")', "docx_tools.py"),
  defineTool("docx_table_edit_plan", "docx", "Plan structural table changes before writeback.", "doc_id, block_id, table_id, target_rows, target_columns", "Risk-aware non-destructive edit plan", 'docx_table_edit_plan(doc_id="docx_...", block_id="tbl_1")', "docx_tools.py"),
  defineTool("ingest_docx", "docx", "Ingest DOCX/DOCM or LibreOffice-converted legacy office sources.", "file_path", "Stable DocxIR, DFM, assets, and source identity", 'ingest_docx(file_path="/docs/source.docx")', "docx_tools.py"),
  defineTool("get_docx_content", "docx", "Read full DFM or one locator-rich DOCX block.", "doc_id, block_id", "Bounded DFM with Word-origin locators", 'get_docx_content(doc_id="docx_...", block_id="p_12")', "docx_tools.py"),
  defineTool("save_docx", "docx", "Write DFM back through stale-source and integrity guards.", "doc_id, dfm_content, output_path, force, track_changes", "Validated DOCX plus optional revision sidecar", 'save_docx(doc_id="docx_...", dfm_content=edited, output_path="/out/review.docx")', "docx_tools.py"),

  defineTool("table_data", "table", "Read and mutate A2T rows and cells.", "operation, table_id, row_id, column_name, value, filters", "Stable row/cell operation result", 'table_data(operation="query_rows", table_id="tbl_...")', "table_tools.py"),
  defineTool("table_cite", "table", "Attach and inspect cell-level AssetRefs; main adds canonical read pages.", "operation, table_id, row_id, column_name, refs", "Stored references and citation coverage", 'table_cite(operation="add", table_id="tbl_...", row_id="row_1", column_name="outcome", refs=[ref])', "table_tools.py"),
  defineTool("table_draft", "table", "Create, resume, update, and commit durable table drafts.", "operation, draft_id, title, proposed_columns, rows", "Recoverable draft lifecycle", 'table_draft(operation="create", title="Outcome review", intent="comparison")', "table_tools.py"),
  defineTool("table_manage", "table", "Create, list, preview, render, delete, and evolve A2T tables.", "operation, intent, title, columns, table_id, format", "Table metadata or durable render artifact", 'table_manage(operation="preview", table_id="tbl_...")', "table_tools.py"),
  defineTool("table_history", "table", "Read table audit history and token accounting.", "operation, table_id, limit", "Bounded change trail", 'table_history(operation="changes", table_id="tbl_...")', "table_tools.py"),
  defineTool("plan_table", "table", "Plan an A2T schema or template before creation.", "operation, question, doc_ids, hints, template_name", "Schema proposal with source mapping", 'plan_table(operation="schema", question="Compare primary outcomes", doc_ids=["doc_..."])', "table_tools.py"),

  defineTool("job", "job", "Job facade for status, list, and cancellation.", "op, job_id, active_only", "Background job lifecycle state", 'job(op="get", job_id="job_...")', "job_tools.py"),
  defineTool("get_job_status", "job", "Read progress, warnings, results, and artifacts for one job.", "job_id", "Current job state and artifact paths", 'get_job_status(job_id="job_...")', "job_tools.py"),
  defineTool("list_jobs", "job", "List active or historical background jobs.", "active_only", "Bounded job inventory", "list_jobs(active_only=true)", "job_tools.py"),
  defineTool("convert_document", "job", "Convert PDF, DOCX, and Markdown through guarded existing paths.", "source, target_format, output_path, mode, async_mode", "Converted artifact or background job", 'convert_document(source="/docs/source.docx", target_format="pdf")', "document_tools.py"),

  defineTool("knowledge", "knowledge", "Opt-in LightRAG consult and export facade.", "op, query, mode, format, verify_references", "Discovery answer or graph summary; evidence remains authoritative", 'knowledge(op="consult", query="What differs?", verify_references=true)', "knowledge_tools.py"),
  defineTool("discover_sources", "knowledge", "Discover document and knowledge sources suitable for a table.", "query, doc_ids, include_kg, limit", "Source candidates for A2T planning", 'discover_sources(query="primary outcomes")', "table_tools.py"),
  defineTool("etl_profile", "knowledge", "List, inspect, load, detect, and activate ETL profiles.", "op, name, json_path, pdf_path, doc_id", "Validated profile metadata or active selection", 'etl_profile(op="detect", doc_id="doc_...")', "profile_tools.py"),
];

const landing = document.getElementById("landing");
const docsReader = document.getElementById("docs-reader");
const mainContent = document.getElementById("main-content");
const skipLink = document.querySelector(".skip-link");
const nav = document.getElementById("page-nav");
const filterInput = document.getElementById("nav-filter");
const docContent = document.getElementById("doc-content");
const pageOutline = document.getElementById("page-outline");
const pageTitle = document.getElementById("page-title");
const pageKicker = document.getElementById("page-kicker");
const sidebar = document.getElementById("sidebar");
const sidebarBackdrop = document.getElementById("sidebar-backdrop");
const navToggle = document.getElementById("nav-toggle");
const navClose = document.getElementById("nav-close");
const siteMenuToggle = document.getElementById("site-menu-toggle");
const siteNavigation = document.getElementById("site-navigation");
const toolSearch = document.getElementById("tool-search-input");
const toolCategories = document.getElementById("tool-category-list");
const toolList = document.getElementById("tool-list");
const toolResultStatus = document.getElementById("tool-result-status");
const copyStatus = document.getElementById("copy-status");
const languageControls = Array.from(document.querySelectorAll("[data-lang]"));
let activeLang = preferredLanguage();
let activeCategory = "all";
let selectedTool = "document";
let copyTimer;
let mermaidInitialized = false;
const mobileSiteMenu = window.matchMedia("(max-width: 920px)");
const mobileReaderSidebar = window.matchMedia("(max-width: 920px)");

if (markdownRenderer?.setOptions) {
  markdownRenderer.setOptions({ gfm: true, breaks: false });
}

function sanitizeRenderedHtml(html) {
  const template = document.createElement("template");
  template.innerHTML = html;
  const forbidden = new Set([
    "BASE",
    "EMBED",
    "FORM",
    "IFRAME",
    "LINK",
    "META",
    "OBJECT",
    "SCRIPT",
    "STYLE",
  ]);
  template.content.querySelectorAll("*").forEach((element) => {
    if (forbidden.has(element.tagName)) {
      element.remove();
      return;
    }
    Array.from(element.attributes).forEach((attribute) => {
      const name = attribute.name.toLowerCase();
      const value = attribute.value.trim();
      if (
        name.startsWith("on")
        || name === "srcdoc"
        || ((name === "href" || name === "src" || name === "xlink:href")
          && /^(?:javascript|vbscript|data):/i.test(value))
      ) {
        element.removeAttribute(attribute.name);
      }
    });
  });
  return template.innerHTML;
}

function preferredLanguage() {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (SUPPORTED_LANGUAGES.includes(stored)) {
      return stored;
    }
  } catch (_error) {
    // A privacy-constrained client can still use the in-memory selection.
  }
  return "zh";
}

function persistLanguage(lang) {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, lang);
  } catch (_error) {
    // Storage is optional.
  }
}

function pageBySlug(slug) {
  return DOC_PAGES.find((page) => page.slug === slug);
}

function pageText(page, field) {
  const localized = page?.[field + "ByLang"];
  return localized?.[activeLang] || page?.[field] || "";
}

function pageMatchesLanguage(page) {
  return page.lang === "all" || page.lang === activeLang;
}

function rawHash() {
  return window.location.hash || "";
}

function documentationSlug() {
  const hash = rawHash();
  if (!hash.startsWith("#/")) {
    return "";
  }
  return hash.slice(2).trim();
}

function isLandingRoute() {
  const slug = documentationSlug();
  return !slug || slug === "overview" || slug === "overview-zh";
}

function localizeStaticText() {
  document.documentElement.lang = activeLang === "zh" ? "zh-TW" : "en";
  const copy = UI_COPY[activeLang];
  document.querySelectorAll("[data-ui]").forEach((element) => {
    const key = element.dataset.ui;
    if (!copy[key]) {
      return;
    }
    if (key === "heroTitle") {
      element.innerHTML = copy[key];
    } else {
      element.textContent = copy[key];
    }
  });
  languageControls.forEach((control) => {
    const selected = control.dataset.lang === activeLang;
    control.classList.toggle("active", selected);
    control.setAttribute("aria-pressed", String(selected));
  });
  if (toolSearch) {
    toolSearch.placeholder = activeLang === "zh"
      ? "搜尋 tool、operation 或輸出…"
      : "Search tool, operation, or output…";
  }
  if (filterInput) {
    filterInput.placeholder = activeLang === "zh"
      ? "PDF、DOCX、citation、VSIX..."
      : "PDF, DOCX, citation, VSIX...";
  }
}

function applyRuntimeStats() {
  ["hero-tool-count", "explorer-tool-count"].forEach((id) => {
    const target = document.getElementById(id);
    if (target) {
      target.textContent = String(DOC_STATS.tools);
    }
  });
  const command = document.getElementById("install-codex");
  if (command) {
    command.textContent =
      "codex mcp add asset-aware-mcp -- uv tool run --python 3.11 --from " +
      "asset-aware-mcp==" + DOC_STATS.version + " asset-aware-mcp";
  }
}

function categoryLabel(category) {
  if (category === "all") {
    return activeLang === "zh" ? "全部工具" : "All tools";
  }
  return CATEGORY_META[category]?.[activeLang] || category;
}

function categoryTools(category) {
  return TOOLS.filter((tool) => category === "all" || tool.category === category);
}

function matchingTools() {
  const query = (toolSearch?.value || "").trim().toLowerCase();
  return categoryTools(activeCategory).filter((tool) => {
    if (!query) {
      return true;
    }
    return [
      tool.name,
      tool.summary,
      tool.inputs,
      tool.outcome,
      tool.example,
      tool.module,
      categoryLabel(tool.category),
    ].join(" ").toLowerCase().includes(query);
  });
}

function renderToolCategories() {
  if (!toolCategories) {
    return;
  }
  const categories = ["all", ...Object.keys(CATEGORY_META)];
  toolCategories.replaceChildren();
  categories.forEach((category) => {
    const count = categoryTools(category).length;
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tool-category-button";
    button.dataset.category = category;
    button.classList.toggle("active", activeCategory === category);
    button.setAttribute("aria-pressed", String(activeCategory === category));
    const strong = document.createElement("strong");
    strong.textContent = categoryLabel(category);
    const number = document.createElement("b");
    number.textContent = String(count);
    const summary = document.createElement("span");
    summary.textContent = category === "all"
      ? (activeLang === "zh" ? "balanced public surface" : "balanced public surface")
      : CATEGORY_META[category].summary;
    button.append(strong, number, summary);
    button.addEventListener("click", () => {
      activeCategory = category;
      renderToolExplorer();
      toolCategories.querySelector(`[data-category="${category}"]`)?.focus();
    });
    toolCategories.append(button);
  });
}

function renderTool(name) {
  const tool = TOOLS.find((entry) => entry.name === name) || TOOLS[0];
  selectedTool = tool.name;
  const values = {
    "tool-detail-category": categoryLabel(tool.category),
    "tool-detail-name": tool.name,
    "tool-detail-summary": tool.summary,
    "tool-detail-module": tool.module,
    "tool-detail-inputs": tool.inputs,
    "tool-detail-outcome": tool.outcome,
    "tool-detail-example": tool.example,
  };
  Object.entries(values).forEach(([id, value]) => {
    const target = document.getElementById(id);
    if (target) {
      target.textContent = value;
    }
  });
  toolList?.querySelectorAll(".tool-option").forEach((button) => {
    const selected = button.dataset.tool === tool.name;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
  });
}

function renderToolList() {
  if (!toolList || !toolResultStatus) {
    return;
  }
  const matches = matchingTools();
  toolResultStatus.textContent = activeLang === "zh"
    ? matches.length + " 個 tools"
    : matches.length + " tools";
  toolList.replaceChildren();
  if (!matches.length) {
    const empty = document.createElement("p");
    empty.className = "tool-empty";
    empty.textContent = activeLang === "zh"
      ? "沒有符合條件的工具。清除搜尋或切換分類。"
      : "No matching tools. Clear the search or change category.";
    toolList.append(empty);
    return;
  }
  if (!matches.some((tool) => tool.name === selectedTool)) {
    selectedTool = matches[0].name;
  }
  matches.forEach((tool) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tool-option";
    button.dataset.tool = tool.name;
    button.setAttribute("role", "option");
    button.setAttribute("aria-selected", String(selectedTool === tool.name));
    button.classList.toggle("active", selectedTool === tool.name);
    button.textContent = tool.name;
    button.addEventListener("click", () => renderTool(tool.name));
    toolList.append(button);
  });
  renderTool(selectedTool);
}

function renderToolExplorer() {
  renderToolCategories();
  renderToolList();
}

function syncSiteMenuAccessibility(open = document.body.classList.contains("site-menu-open")) {
  const readerRoute = document.body.classList.contains("reader-page");
  const hidden = readerRoute || (mobileSiteMenu.matches && !open);
  if (siteMenuToggle) {
    siteMenuToggle.hidden = readerRoute;
  }
  siteNavigation?.toggleAttribute("inert", hidden);
  if (hidden) {
    siteNavigation?.setAttribute("aria-hidden", "true");
  } else {
    siteNavigation?.removeAttribute("aria-hidden");
  }
}

function closeSiteMenu(restoreFocus = false) {
  const wasOpen = document.body.classList.contains("site-menu-open");
  document.body.classList.remove("site-menu-open");
  siteMenuToggle?.setAttribute("aria-expanded", "false");
  syncSiteMenuAccessibility(false);
  if (restoreFocus && wasOpen) {
    siteMenuToggle?.focus();
  }
}

function openSiteMenu() {
  if (document.body.classList.contains("reader-page")) {
    return;
  }
  document.body.classList.add("site-menu-open");
  siteMenuToggle?.setAttribute("aria-expanded", "true");
  syncSiteMenuAccessibility(true);
}

function syncSidebarAccessibility(open = sidebar?.classList.contains("open") ?? false) {
  const hidden = mobileReaderSidebar.matches && !open;
  sidebar?.toggleAttribute("inert", hidden);
  if (hidden) {
    sidebar?.setAttribute("aria-hidden", "true");
  } else {
    sidebar?.removeAttribute("aria-hidden");
  }
  if (mobileReaderSidebar.matches && open) {
    sidebar?.setAttribute("role", "dialog");
    sidebar?.setAttribute("aria-modal", "true");
  } else {
    sidebar?.removeAttribute("role");
    sidebar?.removeAttribute("aria-modal");
  }
}

function closeSidebar(restoreFocus = false) {
  const wasOpen = sidebar?.classList.contains("open") ?? false;
  sidebar?.classList.remove("open");
  document.body.classList.remove("nav-open");
  if (sidebarBackdrop) {
    sidebarBackdrop.hidden = true;
  }
  navToggle?.setAttribute("aria-expanded", "false");
  syncSidebarAccessibility(false);
  if (restoreFocus && wasOpen) {
    navToggle?.focus();
  }
}

function openSidebar() {
  sidebar?.classList.add("open");
  document.body.classList.add("nav-open");
  if (sidebarBackdrop) {
    sidebarBackdrop.hidden = false;
  }
  navToggle?.setAttribute("aria-expanded", "true");
  syncSidebarAccessibility(true);
  navClose?.focus();
}

function visibleDocumentationPages() {
  return DOC_PAGES.filter((page) =>
    pageMatchesLanguage(page) && !["overview", "overview-zh"].includes(page.slug)
  );
}

function renderNav() {
  if (!nav) {
    return;
  }
  const query = (filterInput?.value || "").trim().toLowerCase();
  const pages = visibleDocumentationPages().filter((page) => {
    if (!query) {
      return true;
    }
    const source = activeLang === "en"
      ? (ENGLISH_PAGE_CONTENT[page.slug] || "")
      : (embeddedContent[page.slug] || "");
    return [
      pageText(page, "title"),
      pageText(page, "blurb"),
      source,
    ].join(" ").toLowerCase().includes(query);
  });
  const current = documentationSlug();
  nav.replaceChildren();
  const count = document.createElement("p");
  count.className = "nav-result-count";
  count.textContent = activeLang === "zh"
    ? pages.length + " 個頁面"
    : pages.length + " pages";
  nav.append(count);
  NAV_GROUPS.forEach((group) => {
    const grouped = pages.filter((page) => page.audience === group);
    if (!grouped.length) {
      return;
    }
    const section = document.createElement("section");
    section.className = "nav-section";
    const title = document.createElement("h2");
    title.className = "nav-section-title";
    title.textContent = GROUP_COPY[activeLang][group] || group;
    section.append(title);
    grouped.forEach((page) => {
      const link = document.createElement("a");
      link.className = "page-link";
      link.classList.toggle("active", page.slug === current);
      link.href = "#/" + page.slug;
      const strong = document.createElement("strong");
      strong.textContent = pageText(page, "title");
      const blurb = document.createElement("span");
      blurb.textContent = pageText(page, "blurb");
      link.append(strong, blurb);
      link.addEventListener("click", closeSidebar);
      section.append(link);
    });
    nav.append(section);
  });
  if (!pages.length) {
    const empty = document.createElement("p");
    empty.className = "nav-empty";
    empty.textContent = activeLang === "zh"
      ? "沒有符合篩選條件的頁面。"
      : "No pages match this filter.";
    nav.append(empty);
  }
}

function slugifyHeading(text, index) {
  const slug = text.toLowerCase()
    .replace(/[^\p{Letter}\p{Number}\s-]/gu, "")
    .trim()
    .replace(/\s+/g, "-");
  return slug || "section-" + index;
}

function renderOutline() {
  if (!pageOutline || !docContent) {
    return;
  }
  const headings = Array.from(docContent.querySelectorAll("h2, h3"));
  pageOutline.replaceChildren();
  if (!headings.length) {
    pageOutline.hidden = true;
    return;
  }
  const panel = document.createElement("div");
  panel.className = "outline-panel";
  const title = document.createElement("strong");
  title.className = "outline-title";
  title.textContent = activeLang === "zh" ? "本頁內容" : "On this page";
  const outlineNav = document.createElement("nav");
  outlineNav.className = "outline-nav";
  outlineNav.setAttribute("aria-label", title.textContent);
  panel.append(title, outlineNav);
  pageOutline.append(panel);
  headings.forEach((heading, index) => {
    if (!heading.id) {
      heading.id = slugifyHeading(heading.textContent || "", index);
    }
    const link = document.createElement("a");
    link.href = "#" + heading.id;
    link.textContent = heading.textContent || "";
    link.className = heading.tagName === "H3" ? "outline-link h3" : "outline-link";
    link.addEventListener("click", (event) => {
      // A bare heading hash would replace the reader's #/slug route and make
      // the router return to the landing page. Keep the route intact while
      // preserving the expected in-page navigation and keyboard focus.
      event.preventDefault();
      heading.tabIndex = -1;
      heading.scrollIntoView({ block: "start" });
      heading.focus({ preventScroll: true });
    });
    outlineNav.append(link);
  });
  pageOutline.hidden = false;
}

async function renderMermaidBlocks() {
  if (!window.mermaid || !docContent) {
    return;
  }
  const blocks = Array.from(docContent.querySelectorAll("pre code.language-mermaid"));
  if (!blocks.length) {
    return;
  }
  blocks.forEach((block) => {
    const container = document.createElement("div");
    container.className = "mermaid";
    container.textContent = block.textContent || "";
    block.parentElement?.replaceWith(container);
  });
  if (!mermaidInitialized) {
    window.mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });
    mermaidInitialized = true;
  }
  try {
    await window.mermaid.run({ nodes: docContent.querySelectorAll(".mermaid") });
  } catch (error) {
    console.warn("Mermaid rendering skipped:", error);
  }
}

async function renderDocumentation(slug) {
  const page = pageBySlug(slug);
  if (!page || !docContent) {
    window.location.hash = "#/getting-started";
    return;
  }
  landing.hidden = true;
  docsReader.hidden = false;
  document.body.classList.remove("landing-page");
  document.body.classList.add("reader-page");
  closeSiteMenu();
  pageTitle.textContent = pageText(page, "title");
  pageKicker.textContent = GROUP_COPY[activeLang][page.audience] || page.audience;
  const markdown = activeLang === "en"
    ? ENGLISH_PAGE_CONTENT[page.slug]
    : embeddedContent[page.slug];
  if (!markdown) {
    docContent.innerHTML =
      "<h1>" + pageText(page, "title") + "</h1><p>" +
      (activeLang === "zh"
        ? "此頁尚未包含在網站 payload，請重新執行文件 builder。"
        : "This page is missing from the site payload. Run the docs builder again.") +
      "</p>";
  } else if (markdownRenderer?.parse) {
    docContent.innerHTML = sanitizeRenderedHtml(markdownRenderer.parse(markdown));
  } else {
    const pre = document.createElement("pre");
    pre.textContent = markdown;
    docContent.replaceChildren(pre);
  }
  const firstHeading = docContent.querySelector("h1");
  if (firstHeading) {
    firstHeading.remove();
  }
  docContent.querySelectorAll("a").forEach((link) => {
    const sourceHref = link.getAttribute("href") || "";
    if (/^https?:\/\//i.test(sourceHref)) {
      link.target = "_blank";
      link.rel = "noreferrer noopener";
    }
  });
  docContent.querySelectorAll("table").forEach((table) => {
    const wrapper = document.createElement("div");
    wrapper.className = "table-scroll";
    wrapper.tabIndex = 0;
    wrapper.setAttribute(
      "aria-label",
      activeLang === "zh" ? "可水平捲動的表格" : "Horizontally scrollable table",
    );
    table.before(wrapper);
    wrapper.append(table);
  });
  docContent.querySelectorAll("pre").forEach((block) => {
    if (block.scrollWidth > block.clientWidth) {
      block.tabIndex = 0;
      block.setAttribute(
        "aria-label",
        activeLang === "zh" ? "可水平捲動的程式碼" : "Horizontally scrollable code",
      );
    }
  });
  renderNav();
  renderOutline();
  await renderMermaidBlocks();
  window.scrollTo({ top: 0, behavior: "auto" });
}

function renderLanding() {
  landing.hidden = false;
  docsReader.hidden = true;
  document.body.classList.add("landing-page");
  document.body.classList.remove("reader-page");
  closeSidebar();
  syncSiteMenuAccessibility();
  renderToolExplorer();
  const hash = rawHash();
  if (hash && !hash.startsWith("#/")) {
    let target = null;
    try {
      target = document.getElementById(decodeURIComponent(hash.slice(1)));
    } catch (_error) {
      // Malformed URL escapes are not a valid landing target.
    }
    window.requestAnimationFrame(() => target?.scrollIntoView({ block: "start" }));
  }
}

function renderRoute() {
  if (isLandingRoute()) {
    renderLanding();
  } else {
    renderDocumentation(documentationSlug());
  }
}

function showCopyStatus(message) {
  if (!copyStatus) {
    return;
  }
  copyStatus.textContent = message;
  copyStatus.classList.add("visible");
  window.clearTimeout(copyTimer);
  copyTimer = window.setTimeout(() => copyStatus.classList.remove("visible"), 1600);
}

async function copyTarget(targetId) {
  const target = document.getElementById(targetId);
  const value = target?.textContent?.trim();
  if (!value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(value);
    showCopyStatus(activeLang === "zh" ? "已複製" : "Copied");
  } catch (_error) {
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(target);
    selection?.removeAllRanges();
    selection?.addRange(range);
    showCopyStatus(activeLang === "zh" ? "已選取，請手動複製" : "Selected; copy manually");
  }
}

languageControls.forEach((control) => {
  control.addEventListener("click", () => {
    const next = control.dataset.lang;
    if (!SUPPORTED_LANGUAGES.includes(next)) {
      return;
    }
    activeLang = next;
    persistLanguage(next);
    localizeStaticText();
    renderToolExplorer();
    renderNav();
    if (!isLandingRoute()) {
      renderDocumentation(documentationSlug());
    }
  });
});

siteMenuToggle?.addEventListener("click", () => {
  if (document.body.classList.contains("site-menu-open")) {
    closeSiteMenu();
  } else {
    openSiteMenu();
  }
});
skipLink?.addEventListener("click", (event) => {
  event.preventDefault();
  mainContent?.scrollIntoView({ block: "start" });
  mainContent?.focus({ preventScroll: true });
});
document.querySelectorAll("#site-navigation a").forEach((link) => {
  link.addEventListener("click", closeSiteMenu);
});
navToggle?.addEventListener("click", () => {
  if (sidebar?.classList.contains("open")) {
    closeSidebar();
  } else {
    openSidebar();
  }
});
navClose?.addEventListener("click", () => closeSidebar(true));
sidebarBackdrop?.addEventListener("click", () => closeSidebar(true));
sidebar?.addEventListener("keydown", (event) => {
  if (event.key !== "Tab" || !mobileReaderSidebar.matches || !sidebar.classList.contains("open")) {
    return;
  }
  const focusable = Array.from(sidebar.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )).filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    last?.focus();
    event.preventDefault();
  } else if (!event.shiftKey && document.activeElement === last) {
    first?.focus();
    event.preventDefault();
  }
});
filterInput?.addEventListener("input", renderNav);
toolSearch?.addEventListener("input", renderToolList);
toolList?.addEventListener("keydown", (event) => {
  if (!["ArrowDown", "ArrowUp"].includes(event.key)) {
    return;
  }
  const options = Array.from(toolList.querySelectorAll(".tool-option"));
  const current = Math.max(0, options.indexOf(document.activeElement));
  const direction = event.key === "ArrowDown" ? 1 : -1;
  const next = (current + direction + options.length) % options.length;
  options[next]?.focus();
  event.preventDefault();
});
document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-copy-target]");
  if (button) {
    copyTarget(button.dataset.copyTarget);
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeSidebar(true);
    closeSiteMenu(true);
  }
});
mobileSiteMenu.addEventListener("change", () => {
  if (!mobileSiteMenu.matches) {
    closeSiteMenu();
  } else {
    syncSiteMenuAccessibility();
  }
});
mobileReaderSidebar.addEventListener("change", () => {
  closeSidebar();
  syncSidebarAccessibility();
});
window.addEventListener("hashchange", renderRoute);

document.addEventListener("DOMContentLoaded", () => {
  syncSiteMenuAccessibility();
  syncSidebarAccessibility();
  localizeStaticText();
  applyRuntimeStats();
  renderToolExplorer();
  renderNav();
  renderRoute();
});
