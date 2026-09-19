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
    largeSpanCopy: "Large spans use an explicit asset-ref-preview-v1 over MCP with canonical_asset_ref=false. The exact quote and self-verifying AssetRef remain in the persisted citation or agent-asset bundle.",
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
    largeSpanCopy: "大型 span 的 MCP 回應只提供 asset-ref-preview-v1，且 canonical_asset_ref=false；完整 exact quote 與可自我驗證 AssetRef 留在持久化 citation / agent-asset bundle。",
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

New revisions create new snapshots. Existing notes are verified and never replaced; modified or unexpected files stop reuse. Put human synthesis in adjacent notes. A new citation style for the same revision requires a separate wiki directory. The 20,000-cell and 128 MiB limits reject incomplete exports. Interrupted publication retains files and reports reconciliation_required. Full academic CSL formatting and rendered verification remain separate work.

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
  "citation-provenance": `## Preserve exact evidence
A canonical AssetRef ties an exact quote to document identity, revision, line or character ranges, context, and hashes. Verification fails closed when the current source no longer matches those fields.

## Distinguish previews
A bounded asset-ref-preview-v1 response is not canonical and must not be submitted as a verification reference.`,
  "a2t-tables": `## Build reusable tables
Plan schemas, manage tables, query stable rows, attach cell citations, and use durable drafts for interrupted work. Table history records changes while render operations produce reusable artifacts.

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
