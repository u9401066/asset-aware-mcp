#!/usr/bin/env python3
"""Build the committed GitHub Pages documentation payload."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
WIKI_DIR = DOCS_DIR / "wiki"
CONTENT_DIR = DOCS_DIR / "site-content"
CONTENT_JS = DOCS_DIR / "site-content.js"


@dataclass(frozen=True)
class Page:
    slug: str
    group: str
    lang: str
    audience: str
    title: str
    blurb: str
    source: str | None = None
    title_zh: str | None = None
    blurb_zh: str | None = None

    def metadata(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "slug": self.slug,
            "group": self.group,
            "lang": self.lang,
            "audience": self.audience,
            "title": self.title,
            "blurb": self.blurb,
            "file": f"site-content/{self.slug}.md",
        }
        if self.title_zh:
            payload["titleByLang"] = {"zh": self.title_zh}
        if self.blurb_zh:
            payload["blurbByLang"] = {"zh": self.blurb_zh}
        return payload


PAGES = [
    Page(
        "overview",
        "overview",
        "en",
        "start",
        "Overview",
        "Project positioning, endpoint inventory, and documentation map.",
    ),
    Page(
        "overview-zh",
        "overview",
        "zh",
        "start",
        "總覽",
        "專案定位、endpoint 盤點與文件地圖。",
        "Home.md",
    ),
    Page(
        "getting-started",
        "getting-started",
        "all",
        "start",
        "Getting Started",
        "Install, configure, and verify the MCP server quickly.",
        "Getting-Started.md",
        "開始使用",
        "快速安裝、設定並驗證 MCP server。",
    ),
    Page(
        "vs-code-extension",
        "vs-code-extension",
        "all",
        "start",
        "VS Code Extension And MCP Setup",
        "VSIX setup, MCP provider, and AI-client config merge.",
        "VS-Code-Extension-And-MCP-Setup.md",
        "VS Code Extension 與 MCP 設定",
        "VSIX setup、MCP provider 與 AI-client config merge。",
    ),
    Page(
        "design-ux",
        "design-ux",
        "all",
        "start",
        "Design And UX Notes",
        "Human-facing information architecture, layout, and completeness rules.",
        "Design-And-UX.md",
        "設計與 UX 說明",
        "面向人類閱讀的資訊架構、版面與完整性規則。",
    ),
    Page(
        "architecture",
        "architecture",
        "all",
        "developer",
        "Architecture",
        "DDD layers, runtime surfaces, and data flow.",
        "Architecture.md",
        "架構",
        "DDD 分層、runtime surface 與資料流。",
    ),
    Page(
        "mcp-tools",
        "mcp-tools",
        "all",
        "reference",
        "MCP Tools",
        "Complete 62-tool public MCP surface by module.",
        "MCP-Tools.md",
        "MCP 工具",
        "依 module 整理的完整 62-tool MCP surface。",
    ),
    Page(
        "mcp-resources",
        "mcp-resources",
        "all",
        "reference",
        "MCP Resources",
        "Document and table resource URI contracts.",
        "MCP-Resources.md",
        "MCP Resources",
        "Document 與 table resource URI contract。",
    ),
    Page(
        "pdf-workflow",
        "pdf-workflow",
        "all",
        "user",
        "PDF Document Workflow",
        "PDF ingest, OCR, layout, segmentation, and assets.",
        "PDF-Document-Workflow.md",
        "PDF 文件工作流",
        "PDF ingest、OCR、layout、segmentation 與 assets。",
    ),
    Page(
        "docx-dfm-workflow",
        "docx-dfm-workflow",
        "all",
        "user",
        "DOCX DFM Workflow",
        "DOCX/DOC round trips, DFM editing, and validation.",
        "DOCX-DFM-Workflow.md",
        "DOCX / DFM 工作流",
        "DOCX/DOC round trip、DFM 編輯與驗證。",
    ),
    Page(
        "citation-provenance",
        "citation-provenance",
        "all",
        "user",
        "Citation Provenance",
        "AssetRef, locator, hash, and evidence span rules.",
        "Citation-Provenance.md",
        "引用與來源追溯",
        "AssetRef、locator、hash 與 evidence span 規則。",
    ),
    Page(
        "a2t-tables",
        "a2t-tables",
        "all",
        "user",
        "A2T Tables",
        "TableContext design, citation cells, drafts, and rendering.",
        "A2T-Tables.md",
        "A2T 表格",
        "TableContext、cell citation、draft 與 rendering。",
    ),
    Page(
        "knowledge-graph",
        "knowledge-graph",
        "all",
        "user",
        "Knowledge Graph",
        "LightRAG/Ollama/OpenAI knowledge graph setup and usage.",
        "Knowledge-Graph.md",
        "知識圖譜",
        "LightRAG/Ollama/OpenAI knowledge graph 設定與使用。",
    ),
    Page(
        "background-jobs",
        "background-jobs",
        "all",
        "user",
        "Background Jobs",
        "Async job lifecycle, progress, cancellation, and artifacts.",
        "Background-Jobs.md",
        "背景工作",
        "Async job lifecycle、progress、cancel 與 artifacts。",
    ),
    Page(
        "etl-profiles",
        "etl-profiles",
        "all",
        "user",
        "ETL Profiles",
        "Built-in and custom ETL profile behavior.",
        "ETL-Profiles.md",
        "ETL Profiles",
        "內建與自訂 ETL profile 行為。",
    ),
    Page(
        "git-harness-hygiene",
        "git-harness-hygiene",
        "all",
        "developer",
        "Git Harness Hygiene",
        "Local skip-worktree policy for VSIX-managed harness assets.",
        "Git-Harness-Hygiene.md",
        "Git Harness Hygiene",
        "VSIX-managed harness assets 的本機 skip-worktree policy。",
    ),
    Page(
        "developer-guide",
        "developer-guide",
        "all",
        "developer",
        "Developer Guide",
        "Implementation boundaries, tests, docs, and extension sync.",
        "Developer-Guide.md",
        "開發者指南",
        "Implementation boundary、測試、文件與 extension sync。",
    ),
    Page(
        "release-testing",
        "release-testing",
        "all",
        "developer",
        "Release And Testing",
        "Release gates, focused tests, VSIX checks, and artifact audits.",
        "Release-And-Testing.md",
        "Release 與測試",
        "Release gates、focused tests、VSIX checks 與 artifact audits。",
    ),
    Page(
        "code-map",
        "code-map",
        "all",
        "developer",
        "Code Map",
        "Where each major capability lives in the repository.",
        "Code-Map.md",
        "程式碼地圖",
        "各主要能力在 repo 內的落點。",
    ),
]

SLUG_BY_WIKI_STEM = {
    Path(page.source).stem: page.slug for page in PAGES if page.source is not None
}

EN_OVERVIEW = """# Asset-Aware MCP Docs

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
| Latest code version | `0.6.29` |
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
"""


def transform_markdown(markdown: str) -> str:
    markdown = markdown.replace("](assets/", "](wiki/assets/")

    def replace_link(match: re.Match[str]) -> str:
        label = match.group(1)
        target = match.group(2)
        if re.match(r"^[a-z]+://|^#|^mailto:", target, flags=re.IGNORECASE):
            return match.group(0)
        if target.startswith(("wiki/assets/", "assets/")):
            return match.group(0)

        stem = Path(target).stem
        slug = SLUG_BY_WIKI_STEM.get(stem)
        if slug is None:
            return match.group(0)
        return f"[{label}](#/{slug})"

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, markdown)


def page_markdown(page: Page) -> str:
    if page.source is None:
        body = EN_OVERVIEW
    else:
        body = (WIKI_DIR / page.source).read_text(encoding="utf-8")
    body = transform_markdown(body).rstrip()
    return (
        f"<!-- Generated from {page.source or 'embedded overview'} "
        "by scripts/build_docs_site.py -->\n\n"
        f"{body}\n"
    )


def build_outputs() -> dict[Path, str]:
    content: dict[str, str] = {}
    outputs: dict[Path, str] = {}

    for page in PAGES:
        markdown = page_markdown(page)
        content[page.slug] = markdown
        outputs[CONTENT_DIR / f"{page.slug}.md"] = markdown

    pages_payload = [page.metadata() for page in PAGES]
    js = (
        "window.ASSET_AWARE_DOC_PAGES = "
        f"{json.dumps(pages_payload, ensure_ascii=False, indent=2)};\n"
        "window.ASSET_AWARE_DOC_PAGE_CONTENT = "
        f"{json.dumps(content, ensure_ascii=False, indent=2)};\n"
    )
    outputs[CONTENT_JS] = js
    return outputs


def write_outputs(outputs: dict[Path, str]) -> None:
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def check_outputs(outputs: dict[Path, str]) -> int:
    drifted: list[str] = []
    for path, expected in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            drifted.append(str(path.relative_to(ROOT)))

    if drifted:
        print("Docs site payload is out of date:")
        for path in drifted:
            print(f"  - {path}")
        print("Run: python3 scripts/build_docs_site.py")
        return 1

    print("Docs site payload is up to date.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="check generated docs site payload without writing files",
    )
    args = parser.parse_args()

    outputs = build_outputs()
    if args.check:
        return check_outputs(outputs)

    write_outputs(outputs)
    print(f"Wrote {len(outputs)} docs site files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
