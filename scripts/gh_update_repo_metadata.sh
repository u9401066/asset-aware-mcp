#!/usr/bin/env bash
# Update GitHub repo description and topics.
# Usage: ./scripts/gh_update_repo_metadata.sh
set -euo pipefail

REPO="${GH_REPO:-u9401066/asset-aware-mcp}"

DESCRIPTION="Turn PDF, DOCX, tables, and figures into citation-ready reusable agent assets and Foam/LightRAG wikis — MCP SDK 2 server plus VS Code extension"
HOMEPAGE="https://u9401066.github.io/asset-aware-mcp/#/overview-zh"

TOPICS=(
  ai
  agent-assets
  citations
  document-processing
  document-ai
  docx
  etl
  foam
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

echo "Updating $REPO metadata"
gh repo edit "$REPO" --description "$DESCRIPTION" --homepage "$HOMEPAGE"
gh repo edit "$REPO" --remove-topic fastmcp || true
gh repo edit "$REPO" --add-topic "$(IFS=,; echo "${TOPICS[*]}")"
