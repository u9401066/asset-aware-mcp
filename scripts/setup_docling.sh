#!/usr/bin/env bash
# ============================================================================
# Asset-Aware MCP — Docling engine installer (Linux / macOS)
#
# Thin wrapper that finds a Python interpreter (python3 or python) and runs the
# cross-platform setup_docling.py. Lets any agent install the isolated Docling
# engine with a single command regardless of how Python is named on the box.
#
# Usage:
#   bash scripts/setup_docling.sh            # install / repair
#   bash scripts/setup_docling.sh --check    # diagnostics only
#   bash scripts/setup_docling.sh --force    # recreate from scratch
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "[ERROR] No Python interpreter found (tried python3, python)." >&2
    echo "        Install Python 3.12+ from https://www.python.org/downloads/" >&2
    echo "        or install uv from https://astral.sh/uv, then re-run." >&2
    exit 1
fi

exec "$PY" "$SCRIPT_DIR/setup_docling.py" "$@"
