#!/usr/bin/env python3
"""Audit release/CI/Cline harness parity.

This check intentionally uses simple text assertions so it can catch workflow
drift before a release path silently skips a production-grade gate.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def is_git_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", path],
        cwd=ROOT,
        check=False,
    )
    return result.returncode == 0


def require_absent(paths: list[str]) -> list[str]:
    return [
        f"{path}: non Asset-Aware harness asset must not be present"
        for path in paths
        if Path(path).exists() and not is_git_ignored(path)
    ]


def require_text(path: str, needles: list[str]) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    return [f"{path}: missing {needle!r}" for needle in needles if needle not in text]


def require_absent_text(path: str, needles: list[str]) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    return [
        f"{path}: forbidden retired harness text {needle!r}"
        for needle in needles
        if needle in text
    ]


def require_count(path: str, needle: str, minimum: int) -> str | None:
    count = Path(path).read_text(encoding="utf-8").count(needle)
    if count < minimum:
        return f"{path}: expected at least {minimum} occurrence(s) of {needle!r}, got {count}"
    return None


def require_exact_count(path: str, needle: str, expected: int) -> str | None:
    count = Path(path).read_text(encoding="utf-8").count(needle)
    if count != expected:
        return (
            f"{path}: expected exactly {expected} occurrence(s) of "
            f"{needle!r}, got {count}"
        )
    return None


def require_guard_per_occurrence(path: str, subject: str, guard: str) -> str | None:
    """Require every security-sensitive action occurrence to carry its guard."""
    text = Path(path).read_text(encoding="utf-8")
    subject_count = text.count(subject)
    guard_count = text.count(guard)
    if guard_count < subject_count:
        return (
            f"{path}: expected {guard!r} for all {subject_count} occurrence(s) of "
            f"{subject!r}, got {guard_count}"
        )
    return None


def main() -> int:
    errors: list[str] = []

    errors.extend(
        require_absent(
            [
                ".github/hooks/copilot-tool-policy.json",
                ".github/hooks/pipeline-enforcer.json",
                ".github/agents/research.agent.md",
                ".github/zotero-research-workflow.md",
                ".claude/skills/pipeline-persistence",
                ".claude/skills/zotero-keeper-harness",
                ".claude/skills/pubmed-export-citations",
                ".claude/skills/pubmed-fulltext-access",
                ".claude/skills/pubmed-gene-drug-research",
                ".claude/skills/pubmed-mcp-tools-reference",
                ".claude/skills/pubmed-multi-source-search",
                ".claude/skills/pubmed-paper-exploration",
                ".claude/skills/pubmed-pico-search",
                ".claude/skills/pubmed-quick-search",
                ".claude/skills/pubmed-systematic-search",
                ".cline/skills/pubmed-search-mcp-harness",
                ".cline/skills/zotero-keeper-harness",
                ".codex/skills/pubmed-search-mcp-harness",
                ".codex/skills/zotero-keeper-harness",
                ".clinerules/00-zotero-project.md",
                ".clinerules/10-zotero-python.md",
                ".clinerules/20-zotero-vscode-extension.md",
                ".clinerules/30-zotero-research-workflow.md",
                ".clinerules/40-zotero-release.md",
                ".clinerules/50-pubmed-project.md",
                ".clinerules/60-pubmed-python.md",
                ".clinerules/70-pubmed-mcp-tools.md",
                ".clinerules/80-pubmed-release.md",
                ".clinerules/workflows/pubmed-full-check.md",
                ".clinerules/workflows/pubmed-mcp-setup.md",
                ".clinerules/workflows/pubmed-release-publish.md",
                ".clinerules/workflows/pubmed-skills-audit.md",
                ".clinerules/workflows/zotero-full-check.md",
                ".clinerules/workflows/zotero-mcp-setup.md",
                ".clinerules/workflows/zotero-release-publish.md",
                ".clinerules/workflows/zotero-skills-audit.md",
                "scripts/hooks/copilot",
            ]
        )
    )
    errors.extend(
        require_text(
            ".gitignore",
            [
                ".github/hooks/",
                ".github/agents/research.agent.md",
                ".claude/skills/zotero-keeper-harness/",
                ".cline/skills/pubmed-search-mcp-harness/",
                ".codex/skills/zotero-keeper-harness/",
                "scripts/hooks/copilot/",
            ],
        )
    )
    retired_harness_text = [
        ".github/zotero-research-workflow.md",
        "Build or refresh a Foam-compatible LLM wiki from Zotero",
        "Use Zotero tools",
        "Use PubMed tools",
        "Use PubMed Search MCP tools",
        "Zotero imports",
        "Zotero key",
        "Zotero:ABC123",
        "PMID:12345678",
        "PubMed discovery",
    ]
    for harness_path in [
        ".cline/skills/llm-wiki-builder/SKILL.md",
        ".codex/skills/llm-wiki-builder/SKILL.md",
        ".clinerules/35-foam-llm-wiki.md",
        ".clinerules/workflows/llm-wiki-build.md",
    ]:
        errors.extend(require_absent_text(harness_path, retired_harness_text))

    errors.extend(
        require_text(
            ".github/workflows/release.yml",
            [
                "uv run pytest",
                "python3 scripts/build_docs_site.py --check",
                "uv run bandit -q -r src -x tests --severity-level medium",
                'NODE_VERSION: "24"',
                "permissions:",
                "contents: read",
                "concurrency:",
                "cancel-in-progress: false",
                "persist-credentials: false",
                "enable-cache: false",
                "package-manager-cache: false",
                "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "astral-sh/setup-uv@ae62891fec2bb8e7d6c99fc78c9fec3a63790f8d",
                'version: "0.12.3"',
                "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
                "python3 scripts/audit_release_harness.py",
                "uv run zizmor --persona=regular --min-severity high .github/workflows",
                "python3 scripts/audit_release_artifacts.py --require all",
                "python3 scripts/audit_release_artifacts.py --require python",
                "python3 scripts/smoke_built_wheel.py",
                "npm run test:ci",
                "xvfb-run -a npm run test:install-smoke -- --require-activation",
                "cross-platform-smoke",
                "release-preflight",
                "fetch-depth: 0",
                "must be an annotated tag",
                'git merge-base --is-ancestor "$TAG_COMMIT_SHA" origin/main',
                "Verify Marketplace publish rights before publishing",
                "npx --no-install vsce verify-pat u9401066",
                "npm audit --package-lock-only --audit-level=low",
                "Package VSIX before publishing PyPI",
                "Smoke built wheel runtime before publishing",
                "Docker smoke diagnostics",
                "asset-aware-mcp doctor --json",
                "asset-aware-mcp list-tools --json",
                "scripts/smoke_mcp_stdio.py",
                "needs: publish-pypi",
                "needs: release-preflight",
                "Verify PyPI package is available",
                "timeout 90s uvx --refresh",
                "npx vsce package --no-dependencies --out",
                "Audit packaged VSIX artifact",
                "--packagePath",
                "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
                "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
                "RELEASE_INPUT_VERSION: ${{ inputs.version }}",
                "RELEASE_EVENT_NAME: ${{ github.event_name }}",
                "tag_name:",
                "target_commitish:",
            ],
        )
    )
    errors.extend(
        require_text(
            ".github/workflows/ci.yml",
            [
                "sync-assets:check",
                'NODE_VERSION: "24"',
                "concurrency:",
                "cancel-in-progress: true",
                "persist-credentials: false",
                "enable-cache: false",
                "package-manager-cache: false",
                "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
                "astral-sh/setup-uv@ae62891fec2bb8e7d6c99fc78c9fec3a63790f8d",
                "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
                "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
                "npm run test:ci",
                "xvfb-run -a npm run test:install-smoke -- --require-activation",
                "python310-mcp-smoke",
                "uv sync --frozen --python 3.10",
                "uv run --python 3.10 pytest tests/test_mcp_tools.py",
                "tests/integration/test_pdf_asset_stdio_e2e.py",
                "-v --timeout=180 --junitxml=junit-integration.xml",
                "npm-security",
                "npm audit --package-lock-only --audit-level=low",
                "uv run zizmor --persona=regular --min-severity high .github/workflows",
                'if [ "$status" != "success" ]',
                'exit "$failed"',
            ],
        )
    )
    ci_count_error = require_count(".github/workflows/ci.yml", "npm run test:ci", 3)
    if ci_count_error:
        errors.append(ci_count_error)
    for guarded_path, guarded_text in [
        (
            ".github/workflows/ci.yml",
            "tests/integration/test_pdf_asset_stdio_e2e.py",
        ),
        (
            "tests/integration/test_pdf_asset_stdio_e2e.py",
            "@pytest.mark.timeout(180)",
        ),
    ]:
        exact_guard_error = require_exact_count(guarded_path, guarded_text, 1)
        if exact_guard_error:
            errors.append(exact_guard_error)

    for workflow_path in [
        ".github/workflows/ci.yml",
        ".github/workflows/release.yml",
        ".github/workflows/dependency-security.yml",
        ".github/workflows/project-hygiene.yml",
    ]:
        for subject, guard in [
            ("uses: actions/checkout@", "persist-credentials: false"),
            ("uses: astral-sh/setup-uv@", "enable-cache: false"),
            ("uses: astral-sh/setup-uv@", 'version: "0.12.3"'),
            ("uses: actions/setup-node@", "package-manager-cache: false"),
        ]:
            guard_error = require_guard_per_occurrence(workflow_path, subject, guard)
            if guard_error:
                errors.append(guard_error)

    errors.extend(
        require_text(
            ".github/workflows/dependency-security.yml",
            [
                "permissions:",
                "contents: read",
                "persist-credentials: false",
                "enable-cache: false",
                "package-manager-cache: false",
                "uv audit --preview-features audit-command --frozen",
                "npm audit --package-lock-only --audit-level=low",
            ],
        )
    )
    errors.extend(
        require_text(
            ".github/workflows/project-hygiene.yml",
            [
                "schedule:",
                'cron: "43 6 * * 3"',
                "permissions:",
                "contents: read",
                "issues: write",
                "if: github.repository == 'u9401066/asset-aware-mcp'",
                "persist-credentials: false",
                "enable-cache: false",
                'version: "0.12.3"',
                "package-manager-cache: false",
                'uv sync --frozen --python "$PYTHON_VERSION"',
                "python3 scripts/build_docs_site.py --check",
                "python3 scripts/audit_release_artifacts.py --require metadata",
                "npm --prefix vscode-extension run sync-assets:check",
                "tests/unit/test_docs_site_reference_sync.py",
                "tests/unit/test_public_docs_hygiene.py",
                "python3 scripts/audit_release_harness.py",
                "./scripts/gh_sync_labels.sh --apply",
                "./scripts/gh_sync_labels.sh --check",
                "./scripts/gh_update_repo_metadata.sh --apply",
                "./scripts/gh_update_repo_metadata.sh --check",
                "PROJECT_HYGIENE_TOKEN",
                "Check-only:",
            ],
        )
    )
    project_hygiene_repo_guard_error = require_exact_count(
        ".github/workflows/project-hygiene.yml",
        "if: github.repository == 'u9401066/asset-aware-mcp'",
        2,
    )
    if project_hygiene_repo_guard_error:
        errors.append(project_hygiene_repo_guard_error)
    for script_path in [
        "scripts/gh_update_repo_metadata.sh",
        "scripts/gh_sync_labels.sh",
    ]:
        errors.extend(require_text(script_path, ["--check", "--apply"]))

    release_contents_read_error = require_count(
        ".github/workflows/release.yml", "contents: read", 2
    )
    if release_contents_read_error:
        errors.append(release_contents_read_error)

    errors.extend(
        require_text(
            "scripts/release.sh",
            [
                "uv run pytest",
                "python3 scripts/build_docs_site.py --check",
                "python3 scripts/check_cline_skills.py",
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
                "python3 scripts/smoke_built_wheel.py",
                "npm run sync-assets:check",
                "npm run test:ci",
                "npm run test:install-smoke -- --require-activation",
                "docker build",
                "docker run",
                "git tag -a",
            ],
        )
    )
    errors.extend(
        require_text(
            ".clinerules/workflows/full-check.md",
            [
                "python3 scripts/build_docs_site.py --check",
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
                "python3 scripts/smoke_built_wheel.py",
                "npm --prefix vscode-extension run sync-assets:check",
                "npm run test:install-smoke",
                "docker build",
                "docker run",
                "scripts/smoke_mcp_stdio.py",
            ],
        )
    )
    errors.extend(
        require_text(
            ".clinerules/workflows/release-publish.md",
            [
                "VSIX install/activation smoke is required",
                "python3 scripts/build_docs_site.py --check",
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
                'git tag -a "v$(python3 scripts/get_version.py --strict-semver)"',
            ],
        )
    )
    errors.extend(
        require_text(
            "vscode-extension/.vscodeignore",
            [
                "out/test/**",
            ],
        )
    )
    errors.extend(
        require_text(
            "vscode-extension/src/test/packageContents.ts",
            [
                "resources/repo-assets/asset-aware/AGENTS.md",
                "resources/repo-assets/asset-aware/.cline/skills/asset-aware-mcp-harness/SKILL.md",
                "resources/repo-assets/asset-aware/.cline/skills/llm-wiki-builder/SKILL.md",
                "resources/repo-assets/asset-aware/.codex/skills/llm-wiki-builder/SKILL.md",
                "resources/repo-assets/asset-aware/.clinerules/35-foam-llm-wiki.md",
            ],
        )
    )
    errors.extend(
        require_text(
            "vscode-extension/package.json",
            [
                "sync-assets",
                "sync-assets:check",
                "assetAwareMcp.configureExternalMcp",
                "assetAwareMcp.installAssistantAssets",
            ],
        )
    )
    errors.extend(
        require_text(
            "vscode-extension/README.md",
            [
                "MCP Tools (30 public tools)",
                "The default surface is `balanced`",
                "find_evidence_spans",
                "verify_citation_ref",
            ],
        )
    )
    errors.extend(
        require_text(
            "README.md",
            [
                "find_evidence_spans",
                "verify_citation_ref",
            ],
        )
    )
    errors.extend(
        require_text(
            "pyproject.toml",
            [
                "[tool.hatch.build.targets.sdist]",
                "blob/main/CHANGELOG.md",
            ],
        )
    )
    errors.extend(
        require_text(
            "Dockerfile",
            [
                "uv export --quiet",
                "requirements.txt",
            ],
        )
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("Release harness audit OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
