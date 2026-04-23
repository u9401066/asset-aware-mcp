#!/usr/bin/env python3
"""Print the project version from pyproject.toml.

Used by release workflows (including Cline workflows) to avoid fragile shell
parsing and quoting issues.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
PYPROJECT_PATH = Path("pyproject.toml")


def read_project_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    in_project = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue

        if not in_project:
            continue

        match = re.match(r'version\s*=\s*"([^"]+)"\s*$', line)
        if match:
            return match.group(1)

    raise ValueError("Could not find [project].version in pyproject.toml")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-semver",
        action="store_true",
        help="Require strict X.Y.Z numeric semantic versioning.",
    )
    args = parser.parse_args()

    try:
        version = read_project_version(PYPROJECT_PATH)
    except Exception as exc:  # pragma: no cover - simple CLI helper
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.strict_semver and not SEMVER_RE.fullmatch(version):
        print(f"ERROR: invalid version (expected X.Y.Z): {version}", file=sys.stderr)
        return 3

    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
