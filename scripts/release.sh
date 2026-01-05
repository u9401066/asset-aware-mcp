#!/bin/bash
# =============================================================================
# Asset-Aware MCP - 發布準備腳本
# =============================================================================
set -e

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

# =============================================================================
# 1. 靜態分析
# =============================================================================
echo -e "\n${YELLOW}📋 Step 1: Static Analysis${NC}"

echo "Running ruff..."
uv run ruff check src/
uv run ruff format src/

echo "Running mypy..."
uv run mypy src/ --ignore-missing-imports

echo -e "${GREEN}✓ Static analysis passed${NC}"

# =============================================================================
# 2. 測試
# =============================================================================
echo -e "\n${YELLOW}🧪 Step 2: Running Tests${NC}"

uv run pytest tests/unit -v --tb=short

echo -e "${GREEN}✓ Tests passed${NC}"

# =============================================================================
# 3. Python 套件建置
# =============================================================================
echo -e "\n${YELLOW}📦 Step 3: Building Python Package${NC}"

# 清理舊的建置
rm -rf dist/ build/ *.egg-info/

# 建置套件
uv build

echo "Built packages:"
ls -la dist/

echo -e "${GREEN}✓ Python package built${NC}"

# =============================================================================
# 4. VS Code 擴展建置
# =============================================================================
echo -e "\n${YELLOW}🧩 Step 4: Building VS Code Extension${NC}"

cd vscode-extension

# 安裝依賴
npm install

# 編譯
npm run compile

# 打包
npx vsce package --no-dependencies

echo "Built VSIX:"
ls -la *.vsix

cd ..

echo -e "${GREEN}✓ VS Code extension built${NC}"

# =============================================================================
# 5. 檢查清單
# =============================================================================
echo -e "\n${YELLOW}✅ Step 5: Pre-release Checklist${NC}"

check_file() {
    if [ -f "$1" ]; then
        echo -e "  ${GREEN}✓${NC} $1"
    else
        echo -e "  ${RED}✗${NC} $1 (missing)"
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

PYTHON_VERSION=$(grep 'version = ' pyproject.toml | head -1 | sed 's/.*"\(.*\)".*/\1/')
VSCODE_VERSION=$(grep '"version"' vscode-extension/package.json | head -1 | sed 's/.*"\([0-9.]*\)".*/\1/')

echo "  Python package: v$PYTHON_VERSION"
echo "  VS Code extension: v$VSCODE_VERSION"

if [ "$PYTHON_VERSION" != "$VSCODE_VERSION" ]; then
    echo -e "  ${YELLOW}⚠ Warning: Version mismatch!${NC}"
fi

# =============================================================================
# 完成
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Release preparation complete!${NC}"
echo -e "${GREEN}========================================${NC}"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "  1. PyPI (Test):   uv publish --repository testpypi"
echo "  2. PyPI (Prod):   uv publish"
echo "  3. VS Code:       cd vscode-extension && npx vsce publish"
echo "  4. GitHub:        git tag v$PYTHON_VERSION && git push --tags"
