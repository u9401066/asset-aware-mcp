"""Regression tests for MCP endpoint inventory scripts."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "src" / "presentation" / "tools"
RESOURCES_DIR = ROOT / "src" / "presentation" / "resources"


def _count_modules(directory: Path, pattern: str) -> tuple[int, int]:
    total = 0
    modules = 0
    for path in sorted(directory.glob("*.py")):
        if path.name == "__init__.py":
            continue
        count = len(re.findall(pattern, path.read_text(encoding="utf-8")))
        if count == 0:
            continue
        total += count
        modules += 1
    return total, modules


def test_count_tools_shell_skips_helper_modules() -> None:
    if os.name == "nt":
        pytest.skip(
            "shell count script is covered by POSIX CI; use PowerShell on Windows"
        )
    if shutil.which("bash") is None:
        pytest.skip("bash is not available on this platform")

    expected_tools, expected_tool_modules = _count_modules(TOOLS_DIR, r"@mcp\.tool\(\)")
    expected_resources, expected_resource_modules = _count_modules(
        RESOURCES_DIR,
        r"@mcp\.resource\(",
    )

    result = subprocess.run(
        ["bash", "scripts/count_tools.sh"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "citation_support" not in result.stdout
    assert "Default public tools: 30 tools (balanced surface)" in result.stdout
    assert (
        f"Decorator inventory:        {expected_tools} tools in {expected_tool_modules} modules"
        in result.stdout
    )
    assert (
        f"Total resources:            {expected_resources} resources in {expected_resource_modules} modules"
        in result.stdout
    )


def test_count_tools_powershell_skips_helper_modules_when_available() -> None:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        return

    expected_tools, expected_tool_modules = _count_modules(TOOLS_DIR, r"@mcp\.tool\(\)")
    result = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/count_tools.ps1",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "citation_support" not in result.stdout
    assert "Default public tools: 30 tools (balanced surface)" in result.stdout
    assert (
        f"Decorator inventory:        {expected_tools} tools in {expected_tool_modules} modules"
        in result.stdout
    )
