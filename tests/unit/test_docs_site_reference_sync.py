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
        "design-ux",
    ]
