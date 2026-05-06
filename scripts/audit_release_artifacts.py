#!/usr/bin/env python3
"""Audit release-facing metadata and built artifacts."""

from __future__ import annotations

import json
import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_SDIST_BYTES = 5 * 1024 * 1024
MAX_WHEEL_BYTES = 5 * 1024 * 1024


def read_project_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    in_project = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue
        if in_project and (match := re.match(r'version\s*=\s*"([^"]+)"$', line)):
            return match.group(1)
    raise ValueError("Could not find [project].version")


def read_regex(path: str, pattern: str) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"{path}: pattern not found: {pattern}")
    return match.group(1)


def read_uv_lock_project_version() -> str:
    text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    match = re.search(
        r'name\s*=\s*"asset-aware-mcp"\s*\nversion\s*=\s*"([^"]+)"',
        text,
    )
    if not match:
        raise ValueError("uv.lock: asset-aware-mcp package version not found")
    return match.group(1)


def check_versions() -> list[str]:
    version = read_project_version()
    package_json = json.loads(
        (ROOT / "vscode-extension/package.json").read_text(encoding="utf-8")
    )
    package_lock = json.loads(
        (ROOT / "vscode-extension/package-lock.json").read_text(encoding="utf-8")
    )
    versions = {
        "pyproject.toml": version,
        "src/__init__.py": read_regex(
            "src/__init__.py", r'__version__\s*=\s*"([^"]+)"'
        ),
        "Dockerfile": read_regex("Dockerfile", r'version="([^"]+)"'),
        "uv.lock": read_uv_lock_project_version(),
        "vscode-extension/package.json": package_json["version"],
        "vscode-extension/package-lock.json": package_lock["version"],
        "vscode-extension/package-lock root": package_lock["packages"][""]["version"],
    }
    unique = set(versions.values())
    if len(unique) == 1:
        return []
    return [f"version mismatch: {versions}"]


def check_links() -> list[str]:
    errors: list[str] = []
    for path in [
        "pyproject.toml",
        "vscode-extension/README.md",
        "README.md",
        "README.zh-TW.md",
    ]:
        text = (ROOT / path).read_text(encoding="utf-8")
        for bad in ["blob/main", "raw/main"]:
            if bad in text:
                errors.append(f"{path}: contains stale {bad!r} link")
    return errors


def check_sdist(version: str) -> list[str]:
    sdist = ROOT / "dist" / f"asset_aware_mcp-{version}.tar.gz"
    if not sdist.exists():
        print(f"[skip] sdist not found: {sdist}")
        return []
    errors: list[str] = []
    if sdist.stat().st_size > MAX_SDIST_BYTES:
        errors.append(f"{sdist}: too large ({sdist.stat().st_size} bytes)")
    forbidden = [
        "/vscode-extension/",
        "/.github/",
        "/.cline/",
        "/.clinerules/",
        "/tests/",
        "/docs/diagrams/",
        "/docs/images/",
    ]
    with tarfile.open(sdist) as tar:
        names = tar.getnames()
    for fragment in forbidden:
        count = sum(1 for name in names if fragment in name)
        if count:
            errors.append(
                f"{sdist}: contains {count} forbidden path(s) matching {fragment}"
            )
    return errors


def check_wheel(version: str) -> list[str]:
    wheel = ROOT / "dist" / f"asset_aware_mcp-{version}-py3-none-any.whl"
    if not wheel.exists():
        print(f"[skip] wheel not found: {wheel}")
        return []
    errors: list[str] = []
    if wheel.stat().st_size > MAX_WHEEL_BYTES:
        errors.append(f"{wheel}: too large ({wheel.stat().st_size} bytes)")
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
    forbidden_prefixes = [
        "tests/",
        "vscode-extension/",
        ".github/",
        ".cline/",
        ".clinerules/",
    ]
    for prefix in forbidden_prefixes:
        count = sum(1 for name in names if name.startswith(prefix))
        if count:
            errors.append(f"{wheel}: contains {count} forbidden path(s) under {prefix}")
    return errors


def check_vsix(version: str) -> list[str]:
    vsix = ROOT / "vscode-extension" / f"asset-aware-mcp-{version}.vsix"
    if not vsix.exists():
        print(f"[skip] VSIX not found: {vsix}")
        return []
    errors: list[str] = []
    with zipfile.ZipFile(vsix) as zf:
        names = zf.namelist()
        package = json.loads(zf.read("extension/package.json"))
        readme = zf.read("extension/readme.md").decode("utf-8")
    if package["version"] != version:
        errors.append(f"{vsix}: package version {package['version']} != {version}")
    test_files = [name for name in names if name.startswith("extension/out/test/")]
    if test_files:
        errors.append(f"{vsix}: contains compiled tests: {', '.join(test_files)}")
    banner = f"raw.githubusercontent.com/u9401066/asset-aware-mcp/v{version}/resources/banner.png"
    if banner not in readme:
        errors.append(f"{vsix}: README banner is not pinned to v{version}")
    if "blob/main" in readme or "raw/main" in readme:
        errors.append(f"{vsix}: README contains stale main-branch links")
    forbidden_harness_fragments = [
        "/resources/repo-assets/asset-aware/.github/hooks/",
        "/resources/repo-assets/asset-aware/.github/zotero-research-workflow.md",
        "/resources/repo-assets/asset-aware/.github/agents/research.agent.md",
        "/resources/repo-assets/asset-aware/scripts/hooks/copilot/",
        "/resources/repo-assets/asset-aware/.claude/skills/pubmed-",
        "/resources/repo-assets/asset-aware/.claude/skills/zotero-keeper-harness/",
        "/resources/repo-assets/asset-aware/.claude/skills/pipeline-persistence/",
        "/resources/repo-assets/asset-aware/.cline/skills/pubmed-search-mcp-harness/",
        "/resources/repo-assets/asset-aware/.cline/skills/zotero-keeper-harness/",
        "/resources/repo-assets/asset-aware/.codex/skills/pubmed-search-mcp-harness/",
        "/resources/repo-assets/asset-aware/.codex/skills/zotero-keeper-harness/",
        "/resources/repo-assets/asset-aware/.clinerules/workflows/pubmed-",
        "/resources/repo-assets/asset-aware/.clinerules/workflows/zotero-",
    ]
    non_asset_harness = [
        name
        for name in names
        if any(fragment in name for fragment in forbidden_harness_fragments)
    ]
    if non_asset_harness:
        errors.append(
            f"{vsix}: contains non Asset-Aware harness assets: "
            + ", ".join(non_asset_harness)
        )
    return errors


def main() -> int:
    errors: list[str] = []
    version = read_project_version()
    errors.extend(check_versions())
    errors.extend(check_links())
    errors.extend(check_sdist(version))
    errors.extend(check_wheel(version))
    errors.extend(check_vsix(version))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Release artifact audit OK ({version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
