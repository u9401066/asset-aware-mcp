#!/usr/bin/env bash
# Check or idempotently synchronize the repository's workflow labels.
# Usage: ./scripts/gh_sync_labels.sh [--check|--apply]
set -euo pipefail

MODE="${1:---check}"
REPO="${GH_REPO:-u9401066/asset-aware-mcp}"

if [[ "$MODE" != "--check" && "$MODE" != "--apply" ]]; then
  echo "Usage: $0 [--check|--apply]" >&2
  exit 2
fi
if [[ ! "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
  echo "ERROR: GH_REPO must be an owner/repository pair" >&2
  exit 2
fi

LABELS=(
  "area:mcp|5319e7|MCP protocol, server, tools, resources, or clients"
  "area:pdf|1d76db|PDF extraction, OCR, layout, or preflight routing"
  "area:docx|0e8a16|DOCX, DFM, round-trip fidelity, or writeback"
  "area:wiki|8250df|Foam, LightRAG, knowledge graph, or reusable agent assets"
  "area:vsix|006b75|VS Code extension, packaging, installation, or UX"
  "area:ci|bfd4f2|CI, smoke tests, release gates, or automation"
  "dependencies|0366d6|Dependency updates and compatibility maintenance"
  "security|b60205|Security hardening, vulnerability, or supply-chain work"
  "provenance|0052cc|Citation locators, hashes, identity, or evidence integrity"
  "breaking-change|d93f0b|Requires a major-version migration by consumers"
  "release|fbca04|Release preparation, publishing, or post-release verification"
  "superseded|c5def5|Replaced by a newer implementation on the default branch"
  "needs-reproduction|f9d0c4|Needs a minimal reproducer or current-version confirmation"
  "priority:high|b60205|High-impact or release-blocking work"
)

if [[ "$MODE" == "--apply" ]]; then
  echo "Synchronizing managed labels in $REPO (unmanaged labels are preserved)"
  for spec in "${LABELS[@]}"; do
    IFS='|' read -r name color description <<<"$spec"
    gh label create "$name" \
      --repo "$REPO" \
      --color "$color" \
      --description "$description" \
      --force
  done
fi

label_json="$(gh label list \
  --repo "$REPO" \
  --limit 1000 \
  --json name,color,description)"

# GitHub label names are untrusted remote data. Parse them as JSON in Python;
# never place them in Bash array subscripts, which can trigger a second round
# of shell expansion on older supported Bash versions.
if ! printf '%s' "$label_json" | python3 -c '
import json
import sys

try:
    rows = json.load(sys.stdin)
    actual = {
        row["name"]: ((row.get("color") or "").lower(), row.get("description") or "")
        for row in rows
    }
except (json.JSONDecodeError, KeyError, TypeError) as exc:
    print(f"ERROR: invalid GitHub label response: {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

drift = False
for spec in sys.argv[1:]:
    name, color, description = spec.split("|", 2)
    current = actual.get(name)
    if current is None:
        print(f"ERROR: missing managed label: {name}", file=sys.stderr)
        drift = True
        continue
    if current[0] != color.lower():
        print(f"ERROR: label color drift: {name}", file=sys.stderr)
        drift = True
    if current[1] != description:
        print(f"ERROR: label description drift: {name}", file=sys.stderr)
        drift = True

raise SystemExit(1 if drift else 0)
' "${LABELS[@]}"; then
  echo "Run with --apply using a token with Issues write permission." >&2
  exit 1
fi

echo "Managed GitHub labels are synchronized: $REPO"
