# ============================================================================
# Asset-Aware MCP - Docling engine installer (Windows PowerShell)
#
# Thin wrapper that finds a Python interpreter (python / py / python3) and runs
# the cross-platform setup_docling.py. Lets any agent install the isolated
# Docling engine with a single command on Windows.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_docling.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\setup_docling.ps1 -Args --check
#   powershell -ExecutionPolicy Bypass -File scripts\setup_docling.ps1 -Args --force
# ============================================================================
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$py = $null
foreach ($candidate in @("python", "py", "python3")) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $py = $candidate
        break
    }
}

if (-not $py) {
    Write-Host "[ERROR] No Python interpreter found (tried python, py, python3)." -ForegroundColor Red
    Write-Host "        Install Python 3.12+ from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "        or install uv from https://astral.sh/uv, then re-run." -ForegroundColor Red
    exit 1
}

$setupScript = Join-Path $ScriptDir "setup_docling.py"
& $py $setupScript @args
exit $LASTEXITCODE
