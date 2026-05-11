param(
    [string]$ToolsDir = "src/presentation/tools",
    [string]$ResourcesDir = "src/presentation/resources"
)

$ErrorActionPreference = "Stop"

function Count-Pattern {
    param(
        [string]$Path,
        [string]$Pattern
    )
    $matches = Select-String -Path $Path -Pattern $Pattern -AllMatches
    return ($matches | ForEach-Object { $_.Matches.Count } | Measure-Object -Sum).Sum
}

Write-Host "MCP endpoint inventory"
Write-Host "======================"
Write-Host ""

$totalTools = 0
$toolModules = 0
Write-Host "Tools (by module):"
Get-ChildItem -Path $ToolsDir -Filter "*.py" |
    Where-Object { $_.Name -ne "__init__.py" } |
    Sort-Object Name |
    ForEach-Object {
        $count = Count-Pattern -Path $_.FullName -Pattern "@mcp\.tool\(\)"
        if ($count -eq 0) {
            return
        }
        "{0,-25} {1,2} tools" -f ($_.BaseName + ":"), $count
        $script:totalTools += $count
        $script:toolModules += 1
    }
Write-Host ("{0,-25} {1,2} tools in {2} modules" -f "TOTAL:", $totalTools, $toolModules)
Write-Host ""

$totalResources = 0
$resourceModules = 0
Write-Host "Resources (by module):"
Get-ChildItem -Path $ResourcesDir -Filter "*.py" |
    Where-Object { $_.Name -ne "__init__.py" } |
    Sort-Object Name |
    ForEach-Object {
        $count = Count-Pattern -Path $_.FullName -Pattern "@mcp\.resource\("
        if ($count -eq 0) {
            return
        }
        "{0,-25} {1,2} resources" -f ($_.BaseName + ":"), $count
        $script:totalResources += $count
        $script:resourceModules += 1
    }
Write-Host ("{0,-25} {1,2} resources in {2} modules" -f "TOTAL:", $totalResources, $resourceModules)
Write-Host ""

Write-Host "Summary:"
Write-Host "  Total tools:      $totalTools tools in $toolModules modules"
Write-Host "  Total resources:  $totalResources resources in $resourceModules modules"
Write-Host "  Grand total:      $($totalTools + $totalResources) MCP endpoints"
