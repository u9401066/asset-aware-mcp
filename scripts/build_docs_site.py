#!/usr/bin/env python3
"""Build the committed GitHub Pages documentation payload."""

from __future__ import annotations

import argparse
import ast
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
TOOLS_DIR = ROOT / "src" / "presentation" / "tools"
RESOURCES_DIR = ROOT / "src" / "presentation" / "resources"


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
        overrides = PAGE_COPY_OVERRIDES.get(self.slug, {})
        title = overrides.get("title", self.title)
        blurb = overrides.get("blurb", self.blurb)
        title_zh = overrides.get("title_zh", self.title_zh)
        blurb_zh = overrides.get("blurb_zh", self.blurb_zh)
        audience = overrides.get("audience", self.audience)
        payload: dict[str, Any] = {
            "slug": self.slug,
            "group": self.group,
            "lang": self.lang,
            "audience": audience,
            "title": title,
            "blurb": blurb,
            "file": f"site-content/{self.slug}.md",
        }
        if title_zh:
            payload["titleByLang"] = {"zh": title_zh}
        if blurb_zh:
            payload["blurbByLang"] = {"zh": blurb_zh}
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
        "workflow-chapters",
        "workflow-chapters",
        "all",
        "start",
        "Workflow Chapters",
        "Choose the right chapter before opening a detailed workflow page.",
        "Workflow-Chapters.md",
        "流程章節",
        "先選章節，再進入對應的詳細流程與 reference。",
    ),
    Page(
        "design-ux",
        "design-ux",
        "all",
        "developer",
        "Docs IA And UX Spec",
        "Maintainer-facing rules for docs information architecture, layout, and coverage.",
        "Design-And-UX.md",
        "文件站 IA / UX 規格",
        "給維護者使用的文件站資訊架構、版面與完整性規則。",
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
        "tool-chooser",
        "tool-chooser",
        "all",
        "reference",
        "Tool Chooser",
        "Task-oriented lookup for choosing the right MCP tool or resource.",
        "Tool-Chooser.md",
        "Tool Chooser",
        "依任務選擇正確 MCP tool 或 resource 的快速查表。",
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
        "document-sections",
        "document-sections",
        "all",
        "user",
        "Document Sections And Navigation",
        "Section tree, block navigation, source locator boundaries, and examples.",
        "Document-Sections-And-Navigation.md",
        "文件章節與導覽",
        "Section tree、block navigation、source locator 邊界與使用範例。",
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
        "evidence",
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
        "llm-wiki",
        "llm-wiki",
        "all",
        "evidence",
        "LLM Wiki Knowledge Base",
        "Foam-compatible LLM wiki workflow, evidence packs, examples, and health checks.",
        "LLM-Wiki-Knowledge-Base.md",
        "LLM Wiki 知識庫",
        "Foam-compatible LLM wiki 建置流程、evidence pack、簡單範例與 health check。",
    ),
    Page(
        "knowledge-graph",
        "knowledge-graph",
        "all",
        "evidence",
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
        "operations",
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
        "operations",
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
        "operations",
        "Release And Testing",
        "Release gates, focused tests, VSIX checks, and artifact audits.",
        "Release-And-Testing.md",
        "Release 與測試",
        "Release gates、focused tests、VSIX checks 與 artifact audits。",
    ),
    Page(
        "mcp-tool-consolidation",
        "mcp-tool-consolidation",
        "all",
        "developer",
        "MCP Tool Consolidation Plan",
        "Target 17-tool op-based surface and legacy direct-tool mapping.",
        "MCP-Tool-Consolidation.md",
        "MCP Tool 整併計畫",
        "目標 17-tool op-based surface 與 legacy direct-tool 對照表。",
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

PAGE_COPY_OVERRIDES: dict[str, dict[str, str]] = {
    "overview": {
        "title": "Overview",
        "blurb": "A short map of the product, workflow chapters, and verified code surface.",
    },
    "overview-zh": {
        "title": "總覽",
        "blurb": "產品定位、章節式導覽、目前 endpoint 數量與上線檢查。",
    },
    "getting-started": {
        "title_zh": "快速開始",
        "blurb_zh": "安裝、設定與第一輪 runtime 驗證。",
    },
    "workflow-chapters": {
        "title_zh": "流程章節",
        "blurb_zh": "先選章節，再進入對應的詳細流程與 reference。",
    },
    "vs-code-extension": {
        "title_zh": "VS Code Extension 與 MCP 設定",
        "blurb_zh": "VSIX setup、MCP provider，以及 Cline/Codex/Copilot 設定合併。",
    },
    "design-ux": {
        "title": "Docs IA And UX Spec",
        "blurb": "Maintainer-facing rules for docs information architecture, layout, and coverage.",
        "title_zh": "文件站 IA / UX 規格",
        "blurb_zh": "給維護者使用的文件站資訊架構、版面與完整性規則。",
    },
    "architecture": {
        "title_zh": "架構",
        "blurb_zh": "DDD layer、runtime surface 與資料流。",
    },
    "mcp-tools": {
        "title_zh": "MCP Tools",
        "blurb_zh": "依 module 對齊目前公開的 62-tool MCP surface。",
    },
    "mcp-resources": {
        "title_zh": "MCP Resources",
        "blurb_zh": "Document 與 table resource URI contract。",
    },
    "tool-chooser": {
        "title_zh": "Tool Chooser",
        "blurb_zh": "依任務選擇正確 MCP tool 或 resource 的快速查表。",
    },
    "pdf-workflow": {
        "title_zh": "PDF 文件流程",
        "blurb_zh": "PDF ingest、OCR、layout、segmentation、asset 與 background job。",
    },
    "document-sections": {
        "title_zh": "文件章節與導覽",
        "blurb_zh": "Section tree、block navigation、source locator 邊界與使用範例。",
    },
    "docx-dfm-workflow": {
        "title_zh": "DOCX / DFM 流程",
        "blurb_zh": "DOCX/DOC round trip、DFM 編輯與 strict validation。",
    },
    "citation-provenance": {
        "title_zh": "引用與證據來源",
        "blurb_zh": "AssetRef、locator、hash、CRAAP scaffold 與 evidence span 規則。",
    },
    "a2t-tables": {
        "title_zh": "A2T 表格",
        "blurb_zh": "TableContext、cell citation、draft、audit trail 與 rendering。",
    },
    "knowledge-graph": {
        "title_zh": "知識圖譜",
        "blurb_zh": "選用的 LightRAG/Ollama/OpenAI 設定，以及可驗證證據的 KG 使用方式。",
    },
    "llm-wiki": {
        "title_zh": "LLM Wiki 知識庫",
        "blurb_zh": "Foam-compatible LLM wiki 建置流程、evidence pack、簡單範例與 health check。",
    },
    "background-jobs": {
        "title_zh": "背景任務",
        "blurb_zh": "Async job lifecycle、progress、cancel 與 artifacts。",
    },
    "etl-profiles": {
        "title_zh": "ETL Profiles",
        "blurb_zh": "內建與自訂 ETL profile 的行為。",
    },
    "git-harness-hygiene": {
        "title_zh": "Git Harness Hygiene",
        "blurb_zh": "VSIX-managed harness assets 的 local skip-worktree policy。",
    },
    "developer-guide": {
        "title_zh": "開發者指南",
        "blurb_zh": "Implementation boundary、測試、文件與 extension sync。",
    },
    "release-testing": {
        "title_zh": "Release 與測試",
        "blurb_zh": "Release gates、focused tests、VSIX checks 與 artifact audits。",
    },
    "mcp-tool-consolidation": {
        "title_zh": "MCP Tool 整併計畫",
        "blurb_zh": "目標 17-tool op-based surface 與 legacy direct-tool 對照表。",
    },
    "code-map": {
        "title_zh": "Code Map",
        "blurb_zh": "每個主要能力在 repo 中的位置。",
    },
}

SLUG_BY_WIKI_STEM = {
    Path(page.source).stem: page.slug for page in PAGES if page.source is not None
}


def _is_mcp_decorator(decorator: ast.expr, name: str) -> bool:
    if not isinstance(decorator, ast.Call):
        return False
    func = decorator.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == name
        and isinstance(func.value, ast.Name)
        and func.value.id == "mcp"
    )


def endpoint_stats() -> dict[str, int | str]:
    tool_count = 0
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        tool_count += sum(
            1
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
            and any(
                _is_mcp_decorator(decorator, "tool")
                for decorator in node.decorator_list
            )
        )

    resource_count = 0
    for path in sorted(RESOURCES_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        resource_count += sum(
            1
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
            and any(
                _is_mcp_decorator(decorator, "resource")
                for decorator in node.decorator_list
            )
        )

    version_match = re.search(
        r'(?m)^version\s*=\s*"([^"]+)"',
        (ROOT / "pyproject.toml").read_text(encoding="utf-8"),
    )
    version = version_match.group(1) if version_match else "unknown"
    return {
        "version": version,
        "tools": tool_count,
        "resources": resource_count,
        "endpoints": tool_count + resource_count,
    }


EN_OVERVIEW = """# Asset-Aware MCP Docs

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
| Latest code version | `0.6.33` |
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
    stats_payload = endpoint_stats()
    js = (
        "window.ASSET_AWARE_DOC_PAGES = "
        f"{json.dumps(pages_payload, ensure_ascii=False, indent=2)};\n"
        "window.ASSET_AWARE_DOC_STATS = "
        f"{json.dumps(stats_payload, ensure_ascii=False, indent=2)};\n"
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
