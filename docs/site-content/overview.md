<!-- Generated from embedded overview by scripts/build_docs_site.py -->

# Asset-Aware MCP Docs

![Asset-Aware MCP architecture overview](wiki/assets/overview-architecture.jpg)

Asset-Aware MCP is a citation-ready document workflow server for AI agents. The
site is built for human readers first: choose a task, follow the workflow, then
drop into the complete reference pages when you need exact tools, resources, or
code locations.

<div class="path-grid">
  <section class="path-card">
    <p class="card-kicker">First run</p>
    <h3>Start the server</h3>
    <p>Install dependencies, configure an MCP client, and verify the VS Code extension or stdio server.</p>
    <p><a href="#/getting-started">Getting Started</a> · <a href="#/vs-code-extension">VSIX / MCP Setup</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Document workflows</p>
    <h3>Handle PDF, DOCX, and tables</h3>
    <p>Pick the workflow you need instead of starting from a raw tool list.</p>
    <p><a href="#/pdf-workflow">PDF</a> · <a href="#/docx-dfm-workflow">DOCX/DFM</a> · <a href="#/a2t-tables">A2T</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Reference</p>
    <h3>Check the public MCP surface</h3>
    <p>Use the complete tools/resources pages when you need exact names and contracts.</p>
    <p><a href="#/mcp-tools">MCP Tools</a> · <a href="#/mcp-resources">Resources</a> · <a href="#/code-map">Code Map</a></p>
  </section>
  <section class="path-card">
    <p class="card-kicker">Design rationale</p>
    <h3>Why the site is arranged this way</h3>
    <p>Read the human-facing UX decisions behind navigation, layout, and completeness.</p>
    <p><a href="#/design-ux">Design / UX Notes</a></p>
  </section>
</div>

| Item | Current Status |
|---|---|
| Latest code version | `0.6.32` |
| Runtime | Python `>=3.10`, managed with `uv` |
| MCP endpoints | 62 tools and 13 resources, 75 endpoints total |
| PDF backend | PyMuPDF by default; Marker has been on security hold since `0.6.28` |
| DOCX | DOCX/DOC/DFM round trip, Track Changes, LibreOffice conversion, strict validation |
| Knowledge graph | LightRAG (`lightrag-hku`) with Ollama/OpenAI-compatible backends and verified citation bundles |
| VS Code extension | Native MCP provider plus Cline/Codex/Copilot config merge, harness sync, and artifact/citation viewer |

## Reading Path

Start with [Getting Started](#/getting-started), then choose the workflow you
need: [PDF](#/pdf-workflow), [DOCX/DFM](#/docx-dfm-workflow),
[Citation Provenance](#/citation-provenance), [A2T Tables](#/a2t-tables), or
[Knowledge Graph](#/knowledge-graph).

Developers should read [Architecture](#/architecture), [MCP Tools](#/mcp-tools),
[MCP Resources](#/mcp-resources), [Code Map](#/code-map), and
[Release And Testing](#/release-testing). The site design rationale is documented
in [Design And UX Notes](#/design-ux).

## Source Of Truth

This site is generated from `docs/wiki/**`. Tool and resource counts come from
`./scripts/count_tools.sh`, not from memory or old diagrams.
