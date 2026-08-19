#!/usr/bin/env bash
# Check or idempotently synchronize GitHub repository metadata.
# Usage: ./scripts/gh_update_repo_metadata.sh [--check|--apply]
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

DESCRIPTION="Turn PDF, DOCX, tables, and figures into citation-ready reusable agent assets and Foam/LightRAG wikis — MCP SDK 2 server plus VS Code extension"
# The repository homepage should open the redesigned product landing. README
# documentation links intentionally deep-link to the generated reader instead.
HOMEPAGE="https://u9401066.github.io/asset-aware-mcp/"

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

check_metadata() {
  local actual_description actual_homepage actual_topics expected_topics

  actual_description="$(gh api "repos/$REPO" --jq '.description // ""')"
  actual_homepage="$(gh api "repos/$REPO" --jq '.homepage // ""')"
  actual_topics="$(gh api -H "Accept: application/vnd.github+json" \
    "repos/$REPO/topics" --jq '.names[]' | LC_ALL=C sort)"
  expected_topics="$(printf '%s\n' "${TOPICS[@]}" | LC_ALL=C sort)"

  local drift=0
  if [[ "$actual_description" != "$DESCRIPTION" ]]; then
    echo "ERROR: $REPO description drift" >&2
    drift=1
  fi
  if [[ "$actual_homepage" != "$HOMEPAGE" ]]; then
    echo "ERROR: $REPO homepage drift" >&2
    drift=1
  fi
  if [[ "$actual_topics" != "$expected_topics" ]]; then
    echo "ERROR: $REPO topics drift" >&2
    drift=1
  fi
  if ((drift != 0)); then
    echo "Run with --apply using a repo-scoped token with Administration write permission." >&2
    return 1
  fi

  echo "GitHub repository metadata is synchronized: $REPO"
}

if [[ "$MODE" == "--apply" ]]; then
  echo "Synchronizing $REPO description, homepage, and canonical topics"
  gh api --method PATCH "repos/$REPO" \
    -f "description=$DESCRIPTION" \
    -f "homepage=$HOMEPAGE" >/dev/null

  topic_args=(--method PUT "repos/$REPO/topics")
  for topic in "${TOPICS[@]}"; do
    topic_args+=(-f "names[]=$topic")
  done
  gh api -H "Accept: application/vnd.github+json" "${topic_args[@]}" >/dev/null
fi

check_metadata
