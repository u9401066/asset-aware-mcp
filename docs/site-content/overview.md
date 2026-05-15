<!-- Generated from embedded overview by scripts/build_docs_site.py -->

# Asset-Aware MCP Docs

![Asset-Aware MCP architecture overview](wiki/assets/overview-architecture.jpg)

Asset-Aware MCP is a citation-ready document workflow server for AI agents. The
site is organized as chapters: start the runtime, choose a document workflow,
anchor claims to evidence, then use reference and release gates when you need
exact contracts.

<div class="path-grid">
  <section class="path-card">
    <p class="card-kicker">Path 1</p>
    <h3>Start the runtime</h3>
    <p>Install dependencies, configure an MCP client, and verify the VS Code extension or stdio server.</p>
    <p><a href="#/getting-started">Getting Started</a> · <a href="#/vs-code-extension">VSIX / MCP Setup</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 2</p>
    <h3>Choose a document workflow</h3>
    <p>Separate PDF, document sections, DOCX/DFM, and A2T tables before reading details.</p>
    <p><a href="#/workflow-chapters">Workflow Chapters</a> · <a href="#/pdf-workflow">PDF</a> · <a href="#/docx-dfm-workflow">DOCX</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 3</p>
    <h3>Anchor evidence</h3>
    <p>Keep claims tied to spans, locators, hashes, context, and citation bundles; LLM wiki is the presentation layer.</p>
    <p><a href="#/citation-provenance">Citation Provenance</a> · <a href="#/llm-wiki">LLM Wiki</a> · <a href="#/knowledge-graph">Knowledge Graph</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Path 4</p>
    <h3>Operate, reference, and release</h3>
    <p>Use background jobs, ETL profiles, exact tool/resource contracts, code locations, and release checks when preparing production changes.</p>
    <p><a href="#/tool-chooser">Tool Chooser</a> · <a href="#/mcp-tools">MCP Tools</a> · <a href="#/release-testing">Release</a></p>
  </section>
</div>

| Item | Current Status |
|---|---|
| Latest code version | `0.6.34` |
| Runtime | Python `>=3.10`, managed with `uv` |
| MCP endpoints | 62 tools and 13 resources, 75 endpoints total |
| PDF backend | PyMuPDF by default; Marker has been on security hold since `0.6.28` |
| DOCX | DOCX/DOC/DFM round trip, Track Changes, LibreOffice conversion, strict validation |
| RAG default | CPU `granite4.1:3b`; GPU hint `granite4.1:8b` |
| Knowledge graph | Opt-in LightRAG (`lightrag-hku`) with verified citation bundles |
| VS Code extension | Native MCP provider plus Cline/Codex/Copilot config merge, harness sync, and artifact/citation viewer |

## Reading Path

Start with [Getting Started](#/getting-started), then use
[Workflow Chapters](#/workflow-chapters) to choose PDF, DOCX/DFM, citation, A2T,
KG/RAG, or release checks. Maintainers can use [Docs IA And UX Spec](#/design-ux)
to keep future site changes consistent.

## Source Of Truth

This site is generated from `docs/wiki/**`. Tool and resource counts come from
`scripts/build_docs_site.py`, which parses the registered MCP decorators in
`src/presentation/tools/**` and `src/presentation/resources/**`.

## Launch Readiness

The GitHub Pages payload is treated as a release artifact. Before publishing,
run `scripts/build_docs_site.py --check` and
`tests/unit/test_docs_site_reference_sync.py` so the version, endpoint counts,
navigation metadata, image assets, and shell copy stay aligned with code.
