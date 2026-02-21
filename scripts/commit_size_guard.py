"""Commit size guard: blocks commits with more than MAX_FILES changed files.

Exempt patterns (not counted): uv.lock, htmlcov/*, memory-bank/*
Usage: python scripts/commit_size_guard.py [--max N]

Exit 0 = OK, Exit 1 = too many files.
"""

from __future__ import annotations

import subprocess
import sys

MAX_FILES = 30

EXEMPT_PATTERNS = (
    "uv.lock",
    "htmlcov/",
    "memory-bank/",
)


def _is_exempt(path: str) -> bool:
    return any(
        path == pat if not pat.endswith("/") else path.startswith(pat)
        for pat in EXEMPT_PATTERNS
    )


def main() -> int:
    max_files = MAX_FILES
    args = sys.argv[1:]
    if "--max" in args:
        idx = args.index("--max")
        max_files = int(args[idx + 1])

    result = subprocess.run(  # noqa: S603
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"Warning: git diff failed: {result.stderr.strip()}")
        return 0

    staged = [f for f in result.stdout.strip().splitlines() if f and not _is_exempt(f)]
    count = len(staged)

    if count > max_files:
        print(f"❌ Commit size guard: {count} files staged (max {max_files})")
        print("   Split into smaller, focused commits.")
        print(f"   Exempt: {', '.join(EXEMPT_PATTERNS)}")
        print("   Bypass: git commit --no-verify")
        return 1

    print(f"✅ Commit size guard: {count}/{max_files} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
