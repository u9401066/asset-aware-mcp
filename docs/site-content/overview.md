<!-- Generated from embedded overview by scripts/build_docs_site.py -->

# Asset-Aware MCP Docs

![Asset-Aware MCP architecture overview](wiki/assets/overview-architecture.jpg)

Asset-Aware MCP is a citation-ready document workflow server for AI agents. It
connects PDF ingestion, DOCX/DFM round trips, table work, figures, OCR,
LightRAG knowledge graphs, background jobs, and the VS Code extension while
preserving source identity, locators, hashes, and context.

| Item | Current Status |
|---|---|
| Latest code version | `0.6.27` |
| Runtime | Python `>=3.10`, managed with `uv` |
| MCP endpoints | 59 tools and 13 resources, 72 endpoints total |
| PDF backend | PyMuPDF by default; Marker is on security hold in `0.6.27` |
| DOCX | DOCX/DOC/DFM round trip, Track Changes, LibreOffice conversion, strict validation |
| Knowledge graph | LightRAG (`lightrag-hku`) with Ollama/OpenAI-compatible backends |
| VS Code extension | Native MCP provider plus Cline/Codex/Copilot config merge and harness sync |

## Reading Path

Start with [Getting Started](#/getting-started), then choose the workflow you
need: [PDF](#/pdf-workflow), [DOCX/DFM](#/docx-dfm-workflow),
[Citation Provenance](#/citation-provenance), [A2T Tables](#/a2t-tables), or
[Knowledge Graph](#/knowledge-graph).

Developers should read [Architecture](#/architecture), [MCP Tools](#/mcp-tools),
[MCP Resources](#/mcp-resources), [Code Map](#/code-map), and
[Release And Testing](#/release-testing).

## Source Of Truth

This site is generated from `docs/wiki/**`. Tool and resource counts come from
`./scripts/count_tools.sh`, not from memory or old diagrams.
