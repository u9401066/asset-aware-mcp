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
    heroLead: "From PDF and DOCX to citation-ready spans, tables, figures, and Foam wikis. MCP SDK 2 keeps sources, locators, and hashes verifiable end to end.",
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
    heroLead: "從 PDF、DOCX 到 citation-ready spans、表格、圖像與 Foam wiki。MCP SDK 2 讓來源、locator 與 hash 一路可驗證。",
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
Use stable row identifiers and cell-level AssetRefs so every comparison can return to its source.`,
  "llm-wiki": `## Export a portable wiki
Agent asset and evidence exports can create Foam-compatible indexes, notes, anchors, tables, figures, and media. These files remain readable Markdown while retaining embedded provenance records.

## Check evidence health
Run wiki health checks before promoting claims, and keep unresolved or stale references visible for review.`,
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
A release candidate must pass lint, formatting, types, full tests, documentation checks, security audits, package audits, VSIX tests, and artifact verification. Install and activation smoke tests validate the production extension path.

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
  defineTool("document", "document", "Primary document facade for PDF preflight, ingest, audits, retrieval, and asset export.", "op, pdf_path, doc_id, file_paths, output_dir", "Read-only preflight, background ingest, or deterministic agent assets", 'document(op="export_assets", doc_id="doc_...", output_dir="agent-assets")', "document_tools.py"),
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
  defineTool("table_cite", "table", "Attach and inspect cell-level AssetRefs.", "operation, table_id, row_id, column_name, refs", "Citation coverage and verified cell provenance", 'table_cite(operation="add", table_id="tbl_...", row_id="row_1", column_name="outcome", refs=[ref])', "table_tools.py"),
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
