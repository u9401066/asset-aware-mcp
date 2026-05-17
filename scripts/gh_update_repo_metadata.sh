#!/usr/bin/env bash
# Update GitHub repo description and topics.
# Usage: ./scripts/gh_update_repo_metadata.sh
set -euo pipefail

REPO="${GH_REPO:-u9401066/asset-aware-mcp}"

DESCRIPTION="Asset-Aware MCP Server for AI agents: precise PDF/DOCX assets, A2T tables, structural pointers, 30 public tools / 13 resources, 63 legacy tools, segmentation, OCR, and LightRAG"

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

echo "Updating $REPO metadata"
gh repo edit "$REPO" --description "$DESCRIPTION"
gh repo edit "$REPO" --add-topic "$(IFS=,; echo "${TOPICS[*]}")"
