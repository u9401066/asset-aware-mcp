#!/usr/bin/env python3
"""Audit release/CI/Cline harness parity.

This check intentionally uses simple text assertions so it can catch workflow
drift before a release path silently skips a production-grade gate.
"""

from __future__ import annotations

from pathlib import Path


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
        require_text(
            ".github/workflows/release.yml",
            [
                "uv run pytest",
                "python3 scripts/audit_release_harness.py",
                "python3 scripts/audit_release_artifacts.py",
                "npm run test:ci",
                "xvfb-run -a npm run test:install-smoke -- --require-activation",
                "npx vsce package --no-dependencies",
                "--packagePath",
                "tag_name:",
                "target_commitish:",
            ],
        )
    )
    errors.extend(
        require_text(
            ".github/workflows/ci.yml",
            [
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
