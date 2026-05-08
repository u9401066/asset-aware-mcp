"""Static import-boundary checks for the layered architecture."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


def _imports(module_path: Path) -> list[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def _python_files(package: str) -> list[Path]:
    return [
        path
        for path in (SRC / package).rglob("*.py")
        if "__pycache__" not in path.parts
    ]


def test_application_layer_does_not_import_presentation() -> None:
    offenders = [
        f"{path.relative_to(ROOT)} imports {module}"
        for path in _python_files("application")
        for module in _imports(path)
        if module == "src.presentation" or module.startswith("src.presentation.")
    ]
    assert offenders == []


def test_domain_layer_has_no_outer_layer_imports() -> None:
    forbidden = ("src.application", "src.infrastructure", "src.presentation")
    offenders = [
        f"{path.relative_to(ROOT)} imports {module}"
        for path in _python_files("domain")
        for module in _imports(path)
        if module.startswith(forbidden)
    ]
    assert offenders == []


def test_infrastructure_layer_imports_only_application_ports() -> None:
    allowed_application_ports = {"src.application.worker_runner"}
    forbidden = ("src.application", "src.presentation")
    offenders = [
        f"{path.relative_to(ROOT)} imports {module}"
        for path in _python_files("infrastructure")
        for module in _imports(path)
        if module.startswith(forbidden) and module not in allowed_application_ports
    ]
    assert offenders == []
