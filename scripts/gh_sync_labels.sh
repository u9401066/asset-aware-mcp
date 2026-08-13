#!/usr/bin/env bash
# Idempotently synchronize the repository's workflow labels.
# Usage: ./scripts/gh_sync_labels.sh
set -euo pipefail

REPO="${GH_REPO:-u9401066/asset-aware-mcp}"

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

for spec in "${LABELS[@]}"; do
  IFS='|' read -r name color description <<<"$spec"
  gh label create "$name" \
    --repo "$REPO" \
    --color "$color" \
    --description "$description" \
    --force
done
