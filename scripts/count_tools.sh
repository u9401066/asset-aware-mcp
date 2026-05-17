#!/bin/bash
# Count public MCP tools plus the legacy decorator inventory.
# Usage: ./scripts/count_tools.sh
# Windows: powershell -NoProfile -ExecutionPolicy Bypass -File scripts/count_tools.ps1

set -euo pipefail

TOOLS_DIR="src/presentation/tools"
RESOURCES_DIR="src/presentation/resources"
PYTHON_BIN="${PYTHON:-python}"

default_public_tools="$(
    "$PYTHON_BIN" - <<'PY'
import json
import os
import subprocess
import sys

env = os.environ.copy()
env.pop("ASSET_AWARE_MCP_ENABLE_LEGACY_TOOLS", None)
env["ASSET_AWARE_MCP_TOOL_SURFACE"] = "balanced"

try:
    output = subprocess.check_output(
        [sys.executable, "-m", "src.server", "list-tools", "--json"],
        env=env,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    print(len(json.loads(output)["tools"]))
except Exception:
    from src.presentation.tool_surface import BALANCED_TOOLS

    print(len(BALANCED_TOOLS))
PY
)"

echo "MCP endpoint inventory"
echo "======================"
echo ""
echo "Default public tools: ${default_public_tools} tools (balanced surface)"
echo ""

echo "Decorator inventory (by module):"
total_tools=0
module_count=0

for file in "$TOOLS_DIR"/*.py; do
    if [ -f "$file" ] && [ "$(basename "$file")" != "__init__.py" ]; then
        module=$(basename "$file" .py)
        count=$(grep -c '@mcp.tool()' "$file" 2>/dev/null || true)
        count=${count:-0}
        if [ "$count" -eq 0 ]; then
            continue
        fi
        printf "%-25s %2d tools\n" "$module:" "$count"
        total_tools=$((total_tools + count))
        module_count=$((module_count + 1))
    fi
done
printf "%-25s %2d tools in %d modules\n" "TOTAL:" "$total_tools" "$module_count"
echo ""

echo "Resources (by module):"
total_resources=0
resource_module_count=0

for file in "$RESOURCES_DIR"/*.py; do
    if [ -f "$file" ] && [ "$(basename "$file")" != "__init__.py" ]; then
        module=$(basename "$file" .py)
        count=$(grep -c '@mcp.resource(' "$file" 2>/dev/null || true)
        count=${count:-0}
        if [ "$count" -eq 0 ]; then
            continue
        fi
        printf "%-25s %2d resources\n" "$module:" "$count"
        total_resources=$((total_resources + count))
        resource_module_count=$((resource_module_count + 1))
    fi
done
printf "%-25s %2d resources in %d modules\n" "TOTAL:" "$total_resources" "$resource_module_count"
echo ""

echo "Summary:"
echo "  Default public tools:       $default_public_tools tools (balanced surface)"
echo "  Decorator inventory:        $total_tools tools in $module_count modules"
echo "  Total resources:            $total_resources resources in $resource_module_count modules"
echo "  Public MCP endpoints:       $((default_public_tools + total_resources)) endpoints"
echo "  Legacy decorator endpoints: $((total_tools + total_resources)) endpoints"
echo ""
