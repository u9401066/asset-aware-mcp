#!/usr/bin/env python3
"""Audit release/CI/Cline harness parity.

This check intentionally uses simple text assertions so it can catch workflow
drift before a release path silently skips a production-grade gate.
"""

from __future__ import annotations

from pathlib import Path


def require_absent(paths: list[str]) -> list[str]:
    return [
        f"{path}: non Asset-Aware harness asset must not be present"
        for path in paths
        if Path(path).exists()
    ]


def require_text(path: str, needles: list[str]) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    return [f"{path}: missing {needle!r}" for needle in needles if needle not in text]


def require_count(path: str, needle: str, minimum: int) -> str | None:
    count = Path(path).read_text(encoding="utf-8").count(needle)
    if count < minimum:
        return f"{path}: expected at least {minimum} occurrence(s) of {needle!r}, got {count}"
    return None


def main() -> int:
    errors: list[str] = []

    errors.extend(
        require_absent(
            [
                ".github/hooks/copilot-tool-policy.json",
                ".github/hooks/pipeline-enforcer.json",
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

    errors.extend(
        require_text(
            ".github/workflows/release.yml",
            [
                "uv run pytest",
                'NODE_VERSION: "24"',
                "actions/checkout@v6",
                "astral-sh/setup-uv@v8.1.0",
                "actions/setup-node@v6",
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
                "npm run test:ci",
                "xvfb-run -a npm run test:install-smoke -- --require-activation",
                "cross-platform-smoke",
                "release-preflight",
                "Verify release secrets are configured before publishing",
                "Package VSIX before publishing PyPI",
                "Docker smoke import",
                "needs: publish-pypi",
                "needs: release-preflight",
                "Verify PyPI package is available",
                "npx vsce package --no-dependencies --out",
                "Audit packaged VSIX artifact",
                "--packagePath",
                "actions/upload-artifact@v7",
                "actions/download-artifact@v8",
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
                "actions/checkout@v6",
                "astral-sh/setup-uv@v8.1.0",
                "actions/setup-node@v6",
                "actions/upload-artifact@v7",
                "npm run test:ci",
                "xvfb-run -a npm run test:install-smoke -- --require-activation",
            ],
        )
    )
    ci_count_error = require_count(".github/workflows/ci.yml", "npm run test:ci", 3)
    if ci_count_error:
        errors.append(ci_count_error)

    errors.extend(
        require_text(
            "scripts/release.sh",
            [
                "uv run pytest",
                "python3 scripts/check_cline_skills.py",
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
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
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
                "npm run sync-assets:check",
                "npm run test:install-smoke",
                "docker build",
                "docker run",
            ],
        )
    )
    errors.extend(
        require_text(
            ".clinerules/workflows/release-publish.md",
            [
                "VSIX install/activation smoke is required",
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
                'git tag -a "v$VERSION"',
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
                "MCP Tools (50 total)",
                "Document ETL (14)",
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
                "blob/master/CHANGELOG.md",
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
