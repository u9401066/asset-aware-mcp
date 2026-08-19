#!/usr/bin/env python3
"""Audit release-facing metadata and built artifacts."""

from __future__ import annotations

import argparse
import json
import re
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_SDIST_BYTES = 5 * 1024 * 1024
MAX_WHEEL_BYTES = 5 * 1024 * 1024
REQUIRED_PYTHON_PACKAGE_FILES = [
    "src/server.py",
    "src/application/ingest_worker.py",
    "src/presentation/server.py",
    "src/presentation/diagnostics.py",
    "src/presentation/markdown_utils.py",
]
REQUIRED_CONSOLE_SCRIPT = "asset-aware-mcp = src.server:main"
REQUIREMENT_CHOICES = ("metadata", "python", "vsix", "all")


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
        for bad in ["blob/master", "raw/master"]:
            if bad in text:
                errors.append(f"{path}: contains stale {bad!r} link")
    return errors


def check_public_doc_versions(version: str) -> list[str]:
    """Keep release-facing README copy pinned to the current package version."""
    required = {
        "README.md": [f"## v{version} "],
        "README.zh-TW.md": [f"## v{version} "],
        "vscode-extension/README.md": [
            f"## What's New in v{version}",
            f"asset-aware-mcp/v{version}/resources/banner.png",
        ],
    }
    errors: list[str] = []
    for path, needles in required.items():
        text = (ROOT / path).read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                errors.append(f"{path}: missing current-version marker {needle!r}")
    return errors


def artifact_paths(version: str) -> dict[str, Path]:
    """Return the canonical release artifact paths for a project version."""
    return {
        "sdist": ROOT / "dist" / f"asset_aware_mcp-{version}.tar.gz",
        "wheel": ROOT / "dist" / f"asset_aware_mcp-{version}-py3-none-any.whl",
        "vsix": ROOT / "vscode-extension" / f"asset-aware-mcp-{version}.vsix",
    }


def required_artifact_kinds(requirement: str) -> tuple[str, ...]:
    """Resolve a CLI requirement into the artifacts that must be present."""
    if requirement == "metadata":
        return ()
    if requirement == "python":
        return ("sdist", "wheel")
    if requirement == "vsix":
        return ("vsix",)
    if requirement == "all":
        return ("sdist", "wheel", "vsix")
    raise ValueError(f"Unknown artifact requirement: {requirement}")


def check_required_artifacts(version: str, requirement: str) -> list[str]:
    """Fail closed when an artifact selected by ``requirement`` is absent."""
    paths = artifact_paths(version)
    return [
        f"{paths[kind]}: required {kind} artifact not found"
        for kind in required_artifact_kinds(requirement)
        if not paths[kind].is_file()
    ]


def missing_required_files(names: list[str]) -> list[str]:
    missing: list[str] = []
    for required in REQUIRED_PYTHON_PACKAGE_FILES:
        if not any(name == required or name.endswith(f"/{required}") for name in names):
            missing.append(required)
    return missing


def check_sdist(version: str) -> list[str]:
    sdist = artifact_paths(version)["sdist"]
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
    missing = missing_required_files(names)
    if missing:
        errors.append(f"{sdist}: missing required file(s): {', '.join(missing)}")
    for fragment in forbidden:
        count = sum(1 for name in names if fragment in name)
        if count:
            errors.append(
                f"{sdist}: contains {count} forbidden path(s) matching {fragment}"
            )
    return errors


def check_wheel(version: str) -> list[str]:
    wheel = artifact_paths(version)["wheel"]
    errors: list[str] = []
    if wheel.stat().st_size > MAX_WHEEL_BYTES:
        errors.append(f"{wheel}: too large ({wheel.stat().st_size} bytes)")
    with zipfile.ZipFile(wheel) as zf:
        names = zf.namelist()
        entry_points = [
            name for name in names if name.endswith(".dist-info/entry_points.txt")
        ]
        if entry_points:
            entry_points_text = zf.read(entry_points[0]).decode("utf-8")
        else:
            entry_points_text = ""
    missing = missing_required_files(names)
    if missing:
        errors.append(f"{wheel}: missing required file(s): {', '.join(missing)}")
    if not entry_points:
        errors.append(f"{wheel}: missing dist-info/entry_points.txt")
    elif REQUIRED_CONSOLE_SCRIPT not in entry_points_text:
        errors.append(f"{wheel}: missing console script {REQUIRED_CONSOLE_SCRIPT!r}")
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
    vsix = artifact_paths(version)["vsix"]
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
    root_generated_media = [
        name
        for name in names
        if re.fullmatch(r"extension/[^/]+\.(?:png|jpe?g|webp)", name, re.IGNORECASE)
    ]
    if root_generated_media:
        errors.append(
            f"{vsix}: contains generated media at extension root: "
            + ", ".join(root_generated_media)
        )
    banner = f"raw.githubusercontent.com/u9401066/asset-aware-mcp/v{version}/resources/banner.png"
    if banner not in readme:
        errors.append(f"{vsix}: README banner is not pinned to v{version}")
    if "blob/master" in readme or "raw/master" in readme:
        errors.append(f"{vsix}: README contains stale master-branch links")
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


def audit_release(requirement: str) -> list[str]:
    """Audit metadata and every artifact selected by ``requirement``."""
    errors: list[str] = []
    version = read_project_version()
    errors.extend(check_versions())
    errors.extend(check_links())
    errors.extend(check_public_doc_versions(version))
    errors.extend(check_required_artifacts(version, requirement))

    required = required_artifact_kinds(requirement)
    paths = artifact_paths(version)
    if "sdist" in required and paths["sdist"].is_file():
        errors.extend(check_sdist(version))
    if "wheel" in required and paths["wheel"].is_file():
        errors.extend(check_wheel(version))
    if "vsix" in required and paths["vsix"].is_file():
        errors.extend(check_vsix(version))
    return errors


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit release metadata and required built artifacts."
    )
    parser.add_argument(
        "--require",
        choices=REQUIREMENT_CHOICES,
        default="metadata",
        help=(
            "Required artifact set: metadata only (default), Python sdist/wheel, "
            "VSIX, or all artifacts."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    version = read_project_version()
    errors = audit_release(args.require)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Release artifact audit OK ({version}; required: {args.require})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
