#!/usr/bin/env bash
# gh_update_repo_metadata.sh — Update GitHub repo description & topics
# Usage: ./scripts/gh_update_repo_metadata.sh
set -euo pipefail

REPO="${GH_REPO:-u9401066/asset-aware-mcp}"

# ── Description ──────────────────────────────────────────────────────
DESCRIPTION="Asset-Aware MCP Server — AI Agent precisely accesses tables, figures, sections from PDFs + .docx round-trip editing (DFM) with 47 tools / 13 resources, segmentation export, layout overlay, OCR preprocessing, knowledge graph (LightRAG)"

# ── Topics ───────────────────────────────────────────────────────────
TOPICS=(
  ai
  document-processing
  docx
  etl
  fastmcp
  knowledge-graph
  layout-analysis
  lightrag
  llm
  mcp
  mcp-server
  medical
  ocr
  pdf
  python
  rag
  segmentation
)

echo "📝 Updating repo description..."
gh repo edit "$REPO" --description "$DESCRIPTION"

echo "🏷️  Updating topics..."
gh repo edit "$REPO" $(printf -- '--add-topic %s ' "${TOPICS[@]}")

echo ""
echo "✅ Done. Verify at: https://github.com/$REPO"
echo ""
echo "📋 Current state:"
gh repo view "$REPO" --json description,repositoryTopics --jq '{description, topics: [.repositoryTopics[].name]}'
