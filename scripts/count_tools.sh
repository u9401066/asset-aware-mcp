#!/bin/bash
# Count MCP tools in the repository
# Usage: ./scripts/count_tools.sh

set -e

TOOLS_DIR="src/presentation/tools"
RESOURCES_DIR="src/presentation/resources"

echo "📊 MCP 工具統計"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Count tools per module
echo "🔧 Tools (by module):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
total_tools=0
module_count=0

for file in "$TOOLS_DIR"/*.py; do
    if [ -f "$file" ] && [ "$(basename "$file")" != "__init__.py" ]; then
        module=$(basename "$file" .py)
        count=$(grep -c '@mcp.tool()' "$file" 2>/dev/null || echo 0)
        printf "%-25s %2d tools\n" "$module:" "$count"
        total_tools=$((total_tools + count))
        module_count=$((module_count + 1))
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "%-25s %2d tools in %d modules\n" "📦 TOTAL:" "$total_tools" "$module_count"
echo ""

# Count resources per module
echo "📚 Resources (by module):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
total_resources=0
resource_module_count=0

for file in "$RESOURCES_DIR"/*.py; do
    if [ -f "$file" ] && [ "$(basename "$file")" != "__init__.py" ]; then
        module=$(basename "$file" .py)
        count=$(grep -c '@mcp.resource(' "$file" 2>/dev/null || echo 0)
        printf "%-25s %2d resources\n" "$module:" "$count"
        total_resources=$((total_resources + count))
        resource_module_count=$((resource_module_count + 1))
    fi
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "%-25s %2d resources in %d modules\n" "📦 TOTAL:" "$total_resources" "$resource_module_count"
echo ""

# Summary
echo "📋 Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Total tools:      $total_tools tools in $module_count modules"
echo "  Total resources:  $total_resources resources in $resource_module_count modules"
echo "  Grand total:      $((total_tools + total_resources)) MCP endpoints"
echo ""
