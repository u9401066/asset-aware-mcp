#!/usr/bin/env bash
# gh_update_issue_or_pr.sh — Batch update issue/PR body and labels
# Usage:
#   ./scripts/gh_update_issue_or_pr.sh issue  42 --body "new body" --add-label bug
#   ./scripts/gh_update_issue_or_pr.sh pr     10 --body-file body.md --add-label enhancement
#   ./scripts/gh_update_issue_or_pr.sh issues 1,2,3 --add-label "v0.7.0"
set -euo pipefail

REPO="${GH_REPO:-u9401066/asset-aware-mcp}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <type> <numbers> [gh options...]

Arguments:
  type      issue | pr | issues | prs
  numbers   Single number or comma-separated list (e.g. 1,2,3)
  options   Any flags accepted by 'gh issue edit' / 'gh pr edit':
              --body TEXT          Set body text
              --body-file FILE     Set body from file
              --title TEXT         Set title
              --add-label LABEL    Add label (repeatable)
              --remove-label LABEL Remove label (repeatable)
              --add-assignee USER  Add assignee
              --milestone NAME     Set milestone

Examples:
  # Update single issue body
  $(basename "$0") issue 42 --body "Updated description"

  # Add label to multiple issues
  $(basename "$0") issues 1,2,3 --add-label "v0.7.0"

  # Update PR body from file + add label
  $(basename "$0") pr 10 --body-file docs/pr-body.md --add-label enhancement

  # Batch close stale issues (combine with gh flags)
  for i in 5 6 7; do gh issue close \$i -R $REPO; done
EOF
  exit 1
}

[[ $# -lt 2 ]] && usage

TYPE="$1"; shift
NUMBERS="$1"; shift

# Determine gh sub-command
case "$TYPE" in
  issue|issues) CMD="issue" ;;
  pr|prs)       CMD="pr" ;;
  *)            echo "❌ Unknown type: $TYPE (use issue/pr/issues/prs)" && exit 1 ;;
esac

# Split comma-separated numbers
IFS=',' read -ra NUMS <<< "$NUMBERS"

SUCCESS=0
FAIL=0

for NUM in "${NUMS[@]}"; do
  NUM=$(echo "$NUM" | tr -d ' ')
  echo "🔄 Updating $CMD #$NUM ..."
  if gh "$CMD" edit "$NUM" -R "$REPO" "$@"; then
    echo "   ✅ $CMD #$NUM updated"
    ((SUCCESS++))
  else
    echo "   ❌ $CMD #$NUM failed"
    ((FAIL++))
  fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Success: $SUCCESS  ❌ Failed: $FAIL  📊 Total: ${#NUMS[@]}"
