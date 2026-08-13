#!/bin/bash
# =============================================================================
# Asset-Aware MCP - 發布準備腳本
# =============================================================================
set -euo pipefail

echo "🚀 Asset-Aware MCP Release Preparation"
echo "========================================"

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 專案根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PUSH_TAG=false
case "${1:-}" in
    "") ;;
    --push-tag) PUSH_TAG=true ;;
    --help|-h)
        echo "Usage: scripts/release.sh [--push-tag]"
        echo "  default:    run every pre-tag gate without creating a tag"
        echo "  --push-tag: create and push the verified annotated release tag"
        exit 0
        ;;
    *)
        echo -e "${RED}ERROR: unknown argument: $1${NC}" >&2
        exit 2
        ;;
esac

ensure_clean_worktree() {
    local status
    status="$(git status --porcelain=v1 --untracked-files=all)"
    if [[ -n "$status" ]]; then
        echo -e "${RED}ERROR: release requires a clean worktree:${NC}" >&2
        echo "$status" >&2
        return 1
    fi
}

# =============================================================================
# 0. Repository and release identity safety
# =============================================================================
echo -e "\n${YELLOW}🔒 Step 0: Repository Safety${NC}"

ensure_clean_worktree

CURRENT_BRANCH="$(git symbolic-ref --quiet --short HEAD || true)"
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo -e "${RED}ERROR: releases must run from main (current: ${CURRENT_BRANCH:-detached HEAD}).${NC}" >&2
    exit 1
fi

REMOTE_HEAD="$(git ls-remote --symref origin HEAD)"
DEFAULT_BRANCH="$(awk '$1 == "ref:" {sub("refs/heads/", "", $2); print $2; exit}' <<<"$REMOTE_HEAD")"
if [[ "$DEFAULT_BRANCH" != "main" ]]; then
    echo -e "${RED}ERROR: origin default branch must be main (current: ${DEFAULT_BRANCH:-unknown}).${NC}" >&2
    exit 1
fi

git fetch --quiet origin "+refs/heads/main:refs/remotes/origin/main"
LOCAL_SHA="$(git rev-parse HEAD)"
REMOTE_MAIN_SHA="$(git rev-parse refs/remotes/origin/main)"
if [[ "$LOCAL_SHA" != "$REMOTE_MAIN_SHA" ]]; then
    echo -e "${RED}ERROR: local main must exactly match origin/main before tagging.${NC}" >&2
    echo "  local:       $LOCAL_SHA" >&2
    echo "  origin/main: $REMOTE_MAIN_SHA" >&2
    exit 1
fi

PYTHON_PACKAGE_VERSION="$(python3 scripts/get_version.py --strict-semver)"
VSCODE_VERSION="$(node -p "require('./vscode-extension/package.json').version")"
RELEASE_TAG="v${PYTHON_PACKAGE_VERSION}"

if [[ "$PYTHON_PACKAGE_VERSION" != "$VSCODE_VERSION" ]]; then
    echo -e "${RED}ERROR: Python and VSIX versions do not match.${NC}" >&2
    echo "  Python: $PYTHON_PACKAGE_VERSION" >&2
    echo "  VSIX:   $VSCODE_VERSION" >&2
    exit 1
fi

if git show-ref --verify --quiet "refs/tags/$RELEASE_TAG"; then
    echo -e "${RED}ERROR: local tag already exists: $RELEASE_TAG${NC}" >&2
    exit 1
fi
if git ls-remote --exit-code --tags origin "refs/tags/$RELEASE_TAG" >/dev/null 2>&1; then
    echo -e "${RED}ERROR: remote tag already exists: $RELEASE_TAG${NC}" >&2
    exit 1
fi

python3 scripts/audit_release_artifacts.py --require metadata

echo -e "${GREEN}✓ Clean main at origin/main; release identity is $RELEASE_TAG${NC}"

# =============================================================================
# 0.1 Dependency lock and vulnerability gates
# =============================================================================
echo -e "\n${YELLOW}🔐 Step 0.1: Dependency Security${NC}"

uv lock --check
uvx --from uv==0.12.3 uv audit \
    --preview-features audit-command --frozen --python-version 3.10
npm --prefix vscode-extension audit --package-lock-only --audit-level=low

echo -e "${GREEN}✓ Dependency locks and vulnerability audits passed${NC}"

# =============================================================================
# 1. 靜態分析
# =============================================================================
echo -e "\n${YELLOW}📋 Step 1: Static Analysis${NC}"

echo "Running ruff..."
uv run ruff check .
uv run ruff format --check .

echo "Running mypy..."
uv run mypy src/ --ignore-missing-imports

echo "Running Bandit medium/high security scan..."
uv run bandit -q -r src -x tests --severity-level medium

echo -e "${GREEN}✓ Static analysis passed${NC}"

# =============================================================================
# 2. 測試
# =============================================================================
echo -e "\n${YELLOW}🧪 Step 2: Running Tests${NC}"

uv run pytest

echo -e "${GREEN}✓ Tests passed${NC}"

echo -e "\n${YELLOW}🤖 Step 2.1: Cline Harness Checks${NC}"

python3 scripts/check_cline_skills.py
python3 scripts/audit_release_harness.py

echo -e "${GREEN}✓ Cline harness checks passed${NC}"

# =============================================================================
# 3. Python 套件建置
# =============================================================================
echo -e "\n${YELLOW}📦 Step 3: Building Python Package${NC}"

# 清理舊的建置
rm -rf -- dist/ build/ ./*.egg-info/

# 建置套件
uv build
python3 scripts/audit_release_artifacts.py --require python
python3 scripts/smoke_built_wheel.py

echo "Built packages:"
ls -la dist/

echo -e "${GREEN}✓ Python package built${NC}"

# =============================================================================
# 4. VS Code 擴展建置
# =============================================================================
echo -e "\n${YELLOW}🧩 Step 4: Building VS Code Extension${NC}"

cd vscode-extension

# 安裝依賴並執行 extension CI（包含 VSIX contents guard）
npm ci
npm run sync-assets:check
npm run test:ci

# VSIX 安裝/更新 smoke；Linux 若有 xvfb 則要求 activation smoke
if [[ "$(uname -s)" == "Linux" ]] && command -v xvfb-run >/dev/null 2>&1; then
    xvfb-run -a npm run test:install-smoke -- --require-activation
else
    npm run test:install-smoke
fi

# 打包
npx vsce package --no-dependencies

echo "Built VSIX:"
ls -la -- ./*.vsix

cd ..

echo -e "${GREEN}✓ VS Code extension built${NC}"

python3 scripts/audit_release_artifacts.py --require all

# =============================================================================
# 4.1 Docker Smoke
# =============================================================================
echo -e "\n${YELLOW}🐳 Step 4.1: Docker Smoke${NC}"

docker build -t asset-aware-mcp:smoke .
docker run --rm asset-aware-mcp:smoke doctor --json
docker run --rm asset-aware-mcp:smoke list-tools --json
uv run python scripts/smoke_mcp_stdio.py -- docker run --rm -i asset-aware-mcp:smoke

echo -e "${GREEN}✓ Docker smoke passed${NC}"

# =============================================================================
# 5. 檢查清單
# =============================================================================
echo -e "\n${YELLOW}✅ Step 5: Pre-release Checklist${NC}"

check_file() {
    if [ -f "$1" ]; then
        echo -e "  ${GREEN}✓${NC} $1"
    else
        echo -e "  ${RED}✗${NC} $1 (missing)"
        return 1
    fi
}

echo "Required files:"
check_file "README.md"
check_file "README.zh-TW.md"
check_file "LICENSE"
check_file "CHANGELOG.md"
check_file "pyproject.toml"
check_file "vscode-extension/package.json"
check_file "vscode-extension/README.md"
check_file "vscode-extension/resources/icon.png"

# =============================================================================
# 6. 版本資訊
# =============================================================================
echo -e "\n${YELLOW}📌 Version Information${NC}"

echo "  Python package: v$PYTHON_PACKAGE_VERSION"
echo "  VS Code extension: v$VSCODE_VERSION"

git diff --check
ensure_clean_worktree

# =============================================================================
# 完成
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Release verification complete!${NC}"
echo -e "${GREEN}========================================${NC}"

if [[ "$PUSH_TAG" != true ]]; then
    echo -e "\n${YELLOW}No tag was created (safe default).${NC}"
    echo "To start the release workflow after reviewing these results:"
    echo "  scripts/release.sh --push-tag"
    exit 0
fi

echo -e "\n${YELLOW}🏷️  Creating and pushing $RELEASE_TAG${NC}"
git tag -a "$RELEASE_TAG" -m "Release $RELEASE_TAG"
git push origin "refs/tags/$RELEASE_TAG"

echo -e "${GREEN}✓ $RELEASE_TAG pushed. GitHub Actions now owns PyPI, VSIX, and GitHub Release publishing.${NC}"
