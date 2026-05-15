"""Regression tests that keep the human docs aligned with MCP code."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from scripts import build_docs_site

ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "src" / "presentation" / "tools"
RESOURCES_DIR = ROOT / "src" / "presentation" / "resources"
WIKI_DIR = ROOT / "docs" / "wiki"
SITE_CONTENT_DIR = ROOT / "docs" / "site-content"
PRIVATE_USE_RE = re.compile(r"[\ue000-\uf8ff]")


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


def _tool_names_by_module() -> dict[str, list[str]]:
    modules: dict[str, list[str]] = {}
    for path in sorted(TOOLS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = [
            node.name
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef)
            and any(
                _is_mcp_decorator(decorator, "tool")
                for decorator in node.decorator_list
            )
        ]
        if names:
            modules[path.name] = names
    return modules


def _resource_uris_by_module() -> dict[str, dict[str, str]]:
    modules: dict[str, dict[str, str]] = {}
    for path in sorted(RESOURCES_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        resources: dict[str, str] = {}
        for node in tree.body:
            if not isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if not _is_mcp_decorator(decorator, "resource"):
                    continue
                uri_arg = decorator.args[0]
                if not isinstance(uri_arg, ast.Constant) or not isinstance(
                    uri_arg.value, str
                ):
                    raise AssertionError(
                        f"{path.name}:{node.name} resource URI must be a string literal"
                    )
                resources[node.name] = uri_arg.value
        if resources:
            modules[path.name] = resources
    return modules


def _markdown_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    pattern = re.compile(r"^## `([^`]+)`[^\n]*\n(?P<body>.*?)(?=^## `|\Z)", re.M | re.S)
    for match in pattern.finditer(markdown):
        sections[match.group(1)] = match.group("body")
    return sections


def _project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if match is None:
        raise AssertionError("pyproject.toml must define [project].version")
    return match.group(1)


def _assert_no_text_corruption(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "\ufffd" not in text, path
    assert not PRIVATE_USE_RE.search(text), path


def test_mcp_tools_reference_matches_registered_tools() -> None:
    markdown = (WIKI_DIR / "MCP-Tools.md").read_text(encoding="utf-8")
    sections = _markdown_sections(markdown)

    documented = {
        module: re.findall(r"^\| `([^`]+)` \|", body, flags=re.M)
        for module, body in sections.items()
    }

    assert documented == _tool_names_by_module()


def test_mcp_resources_reference_matches_registered_resources() -> None:
    markdown = (WIKI_DIR / "MCP-Resources.md").read_text(encoding="utf-8")
    sections = _markdown_sections(markdown)

    documented: dict[str, dict[str, str]] = {}
    for module, body in sections.items():
        rows = re.findall(r"^\| `(resource_[^`]+)` \| `([^`]+)` \|", body, flags=re.M)
        documented[module] = dict(rows)

    assert documented == _resource_uris_by_module()


def test_start_here_navigation_matches_design_notes() -> None:
    start_slugs = [
        page.slug for page in build_docs_site.PAGES if page.audience == "start"
    ]

    assert start_slugs == [
        "overview",
        "overview-zh",
        "getting-started",
        "vs-code-extension",
        "workflow-chapters",
    ]


def test_docs_page_metadata_is_product_ready() -> None:
    slugs = [page.slug for page in build_docs_site.PAGES]
    assert len(slugs) == len(set(slugs))

    valid_audiences = {"start", "user", "developer", "reference"}
    for page in build_docs_site.PAGES:
        assert page.audience in valid_audiences, page.slug
        assert page.lang in {"en", "zh", "all"}, page.slug
        if page.lang == "all":
            assert page.title_zh, page.slug
            assert page.blurb_zh, page.slug
        if page.source is not None:
            assert (WIKI_DIR / page.source).is_file(), page.slug
        values = [
            page.title,
            page.blurb,
            page.title_zh or "",
            page.blurb_zh or "",
            page.metadata()["title"],
            page.metadata()["blurb"],
            page.metadata().get("titleByLang", {}).get("zh", ""),
            page.metadata().get("blurbByLang", {}).get("zh", ""),
        ]
        for value in values:
            assert "\ufffd" not in value, page.slug
            assert not PRIVATE_USE_RE.search(value), page.slug


def test_docs_site_builder_outputs_are_constructible() -> None:
    outputs = build_docs_site.build_outputs()

    content_js = outputs[ROOT / "docs" / "site-content.js"]
    assert ROOT / "docs" / "site-content" / "workflow-chapters.md" in outputs
    assert '"slug": "workflow-chapters"' in content_js
    assert "Docs IA And UX Spec" in content_js


def test_overview_docs_show_current_project_version() -> None:
    version = _project_version()

    paths = [
        WIKI_DIR / "Home.md",
        SITE_CONTENT_DIR / "overview.md",
        SITE_CONTENT_DIR / "overview-zh.md",
        ROOT / "scripts" / "build_docs_site.py",
    ]

    for path in paths:
        assert f"`{version}`" in path.read_text(encoding="utf-8"), path


def test_docs_site_payload_exposes_current_endpoint_stats() -> None:
    stats = build_docs_site.endpoint_stats()

    assert stats == {
        "version": _project_version(),
        "tools": sum(len(names) for names in _tool_names_by_module().values()),
        "resources": sum(
            len(resources) for resources in _resource_uris_by_module().values()
        ),
        "endpoints": 75,
    }

    content_js = (ROOT / "docs" / "site-content.js").read_text(encoding="utf-8")
    assert "window.ASSET_AWARE_DOC_STATS" in content_js
    assert f'"tools": {stats["tools"]}' in content_js
    assert f'"resources": {stats["resources"]}' in content_js
    assert f'"endpoints": {stats["endpoints"]}' in content_js


def test_docs_shell_uses_current_metrics_and_has_no_known_text_corruption() -> None:
    paths = [
        ROOT / "docs" / "index.html",
        ROOT / "docs" / "site.js",
        ROOT / "docs" / "site-content.js",
        WIKI_DIR / "Home.md",
        WIKI_DIR / "Workflow-Chapters.md",
        WIKI_DIR / "Design-And-UX.md",
        WIKI_DIR / "Getting-Started.md",
        WIKI_DIR / "Knowledge-Graph.md",
    ]

    for path in paths:
        _assert_no_text_corruption(path)
        text = path.read_text(encoding="utf-8")
        assert "59 個 tool" not in text, path
        assert "<dt>59</dt>" not in text, path
        assert "<dt>72</dt>" not in text, path

    version = _project_version()
    index_html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    site_js = (ROOT / "docs" / "site.js").read_text(encoding="utf-8")
    assert '<dt id="tool-metric-value">62</dt>' in index_html
    assert '<dt id="endpoint-metric-value">75</dt>' in index_html
    assert '<a class="skip-link" href="#doc-content">' in index_html
    assert "20260515-docs-chapters" in index_html
    assert "KG / RAG" in index_html
    assert f'version: "{version}"' in site_js


def test_homepage_is_chapter_oriented_and_kept_short() -> None:
    home = (WIKI_DIR / "Home.md").read_text(encoding="utf-8")

    for label in ["Path 1", "Path 2", "Path 3", "Path 4"]:
        assert label in home
    assert "Chapter 1" not in home
    assert "[流程章節](Workflow-Chapters)" in home
    assert len(home.splitlines()) <= 90


def test_english_overview_matches_chapter_ia() -> None:
    overview = build_docs_site.EN_OVERVIEW

    assert "Workflow Chapters" in overview
    assert "Docs IA And UX Spec" in overview
    assert "Design / UX Notes" not in overview
    assert "human-facing UX" not in overview


def test_workflow_chapters_do_not_document_nonexistent_public_ops() -> None:
    workflow = (WIKI_DIR / "Workflow-Chapters.md").read_text(encoding="utf-8")
    getting_started = (WIKI_DIR / "Getting-Started.md").read_text(encoding="utf-8")
    pdf_workflow = (WIKI_DIR / "PDF-Document-Workflow.md").read_text(encoding="utf-8")
    consolidation = (WIKI_DIR / "MCP-Tool-Consolidation.md").read_text(encoding="utf-8")

    assert 'document(op="ocr")' not in workflow
    assert 'section(op="tree")' not in workflow
    assert "ocr_pdf_document" in workflow
    assert "公開工具沒有 `require_marker` 參數" in getting_started
    assert "公開工具沒有 `require_marker` 參數" in pdf_workflow
    assert "A2T create/delete/list/preview/resume/render/schema ops" in consolidation


def test_sidebar_and_design_spec_match_product_ia() -> None:
    sidebar = (WIKI_DIR / "_Sidebar.md").read_text(encoding="utf-8")
    design_page = next(
        page for page in build_docs_site.PAGES if page.slug == "design-ux"
    )

    assert "[Workflow Chapters](Workflow-Chapters)" in sidebar
    assert "[Docs IA And UX Spec](Design-And-UX)" in sidebar
    assert design_page.audience == "developer"
    assert design_page.metadata()["title"] == "Docs IA And UX Spec"


def test_docs_links_point_to_known_pages_and_assets() -> None:
    known_slugs = {page.slug for page in build_docs_site.PAGES}
    pages_and_shell = [
        ROOT / "docs" / "index.html",
        *sorted(SITE_CONTENT_DIR.glob("*.md")),
    ]

    for path in pages_and_shell:
        text = path.read_text(encoding="utf-8")
        for slug in re.findall(r'href="#/([^"#]+)"|\]\(#/([^"#]+)\)', text):
            target = next(part for part in slug if part)
            assert target in known_slugs, (path, target)

    for path in sorted(WIKI_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for asset in re.findall(r"\]\(assets/([^)]+)\)", text):
            assert (WIKI_DIR / "assets" / asset).is_file(), (path, asset)
