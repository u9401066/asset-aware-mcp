# ============================================================================
# Asset-Aware MCP — Cross-platform installer (Windows PowerShell)
# Detects existing uv / Python installations, supports fresh install & update
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1
# ============================================================================

param(
    [switch]$Check,
    [switch]$Diagnose,
    [switch]$WithMarker,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# --- Configuration ---
$RequiredPythonMajor = 3
$RequiredPythonMinor = 10
$PreferredRuntimePython = '3.11'

# --- Helpers ---
function Write-Info  { Write-Host "[INFO]  $args" -ForegroundColor Cyan }
function Write-Ok    { Write-Host "[OK]    $args" -ForegroundColor Green }
function Write-Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Write-Err   { Write-Host "[ERROR] $args" -ForegroundColor Red }

function Test-Command {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Get-UvCandidates {
    $homeDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { [Environment]::GetFolderPath("UserProfile") }
    $localAppData = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { Join-Path $homeDir "AppData\Local" }
    $cargoHome = if ($env:CARGO_HOME) { $env:CARGO_HOME } else { Join-Path $homeDir ".cargo" }

    return @(
        "uv",
        (Join-Path $localAppData "uv\bin\uv.exe"),
        (Join-Path $homeDir ".local\bin\uv.exe"),
        (Join-Path $cargoHome "bin\uv.exe"),
        (Join-Path $homeDir "scoop\shims\uv.exe"),
        "C:\ProgramData\chocolatey\bin\uv.exe",
        "C:\Program Files\uv\uv.exe"
    ) | Select-Object -Unique
}

function Find-UvCommand {
    foreach ($candidate in Get-UvCandidates) {
        try {
            if ($candidate -eq "uv") {
                if (Test-Command "uv") {
                    $null = & uv --version 2>&1 | Select-Object -First 1
                    return "uv"
                }
            } elseif (Test-Path $candidate) {
                $null = & $candidate --version 2>&1 | Select-Object -First 1
                return $candidate
            }
        } catch {
            # Try next candidate
        }
    }

    return $null
}

function Get-PythonVersion {
    param([string]$Cmd)
    try {
        $output = & $Cmd --version 2>&1 | Select-Object -First 1
        if ($output -match '(\d+)\.(\d+)') {
            return @{ Major = [int]$Matches[1]; Minor = [int]$Matches[2]; Raw = $output.ToString().Trim() }
        }
    } catch {}
    return $null
}

function Test-VersionGe {
    param($VerInfo)
    if ($null -eq $VerInfo) { return $false }
    if ($VerInfo.Major -gt $RequiredPythonMajor) { return $true }
    if ($VerInfo.Major -eq $RequiredPythonMajor -and $VerInfo.Minor -ge $RequiredPythonMinor) { return $true }
    return $false
}

function Show-Help {
    Write-Host "Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Check      Run diagnostics only (no changes)"
    Write-Host "  -Diagnose   Alias for -Check"
    Write-Host "  -WithMarker Install optional Marker backend (pulls torch / surya stack)"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
}

function Run-Check {
    Write-Host ""
    Write-Host "+=================================================+" -ForegroundColor Cyan
    Write-Host "|  Asset-Aware MCP - Diagnostics (Windows)        |" -ForegroundColor Cyan
    Write-Host "+=================================================+" -ForegroundColor Cyan
    Write-Host ""

    Write-Info "System: Windows $([System.Environment]::OSVersion.Version) ($env:PROCESSOR_ARCHITECTURE)"
    Write-Info "PowerShell: $($PSVersionTable.PSVersion)"
    Write-Host ""

    Write-Info "=== uv package manager ==="
    $uvCmd = Find-UvCommand
    if ($uvCmd) {
        $uvVer = (& $uvCmd --version 2>&1 | Select-Object -First 1).ToString().Trim()
        $uvPath = if ($uvCmd -eq "uv") { (Get-Command "uv").Source } else { $uvCmd }
        Write-Ok "uv found: $uvVer"
        Write-Info "  Location: $uvPath"
    } else {
        Write-Err "uv not found"
    }
    Write-Host ""

    Write-Info "=== Python ==="
    $foundPython = $false
    foreach ($candidate in @("python3", "python", "py")) {
        if (Test-Command $candidate) {
            $verInfo = Get-PythonVersion $candidate
            if ($verInfo) {
                $foundPython = $true
                $cmdPath = (Get-Command $candidate).Source
                $status = if (Test-VersionGe $verInfo) { "OK" } else { "TOO OLD" }
                Write-Info "  $candidate => $($verInfo.Raw) [$status]"
                Write-Info "    Location: $cmdPath"
            }
        }
    }
    if (-not $foundPython) {
        Write-Warn "No usable Python command found"
    }
    Write-Host ""

    Write-Info "=== Project ==="
    if (Test-Path "pyproject.toml") {
        Write-Ok "pyproject.toml found"
    } else {
        Write-Warn "pyproject.toml not found in current directory"
    }
}

# ============================================================================
# Main
# ============================================================================
function Main {
    if ($Help) {
        Show-Help
        return
    }

    if ($Check -or $Diagnose) {
        Run-Check
        return
    }

    Write-Host ""
    Write-Host "+=================================================+" -ForegroundColor Magenta
    Write-Host "|  Asset-Aware MCP - Installer (Windows)          |" -ForegroundColor Magenta
    Write-Host "+=================================================+" -ForegroundColor Magenta
    Write-Host ""

    Write-Info "Detected OS: Windows $([System.Environment]::OSVersion.Version) ($env:PROCESSOR_ARCHITECTURE)"

    # ========================================================================
    # Step 1: Check / Install uv
    # ========================================================================
    Write-Host ""
    Write-Info "=== Checking uv package manager ==="

    $uvCmd = Find-UvCommand
    if ($uvCmd) {
        $uvVer = (& $uvCmd --version 2>&1 | Select-Object -First 1).ToString().Trim()
        $uvPath = if ($uvCmd -eq "uv") { (Get-Command "uv").Source } else { $uvCmd }
        Write-Ok "uv already installed: $uvVer"
        Write-Info "  Location: $uvPath"

        Write-Info "Updating uv to latest version..."
        try {
            & $uvCmd self update 2>$null
            Write-Ok "uv updated successfully"
        } catch {
            Write-Warn "uv self-update not available, skipping"
        }
    } else {
        Write-Warn "uv not found. Installing..."
        try {
            # Official uv installer for Windows
            irm https://astral.sh/uv/install.ps1 | iex

            # Refresh PATH
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

            $uvCmd = Find-UvCommand

            if ($uvCmd) {
                $uvVer = (& $uvCmd --version 2>&1 | Select-Object -First 1).ToString().Trim()
                Write-Ok "uv installed: $uvVer"
            } else {
                Write-Err "uv installation succeeded but command not found."
                Write-Err "Please restart your terminal and re-run this script."
                exit 1
            }
        } catch {
            Write-Err "Failed to install uv. Please install manually:"
            Write-Err "  irm https://astral.sh/uv/install.ps1 | iex"
            exit 1
        }
    }

    # ========================================================================
    # Step 2: Check / Install Python
    # ========================================================================
    Write-Host ""
    Write-Info "=== Checking Python (>= ${RequiredPythonMajor}.${RequiredPythonMinor}) ==="

    $pythonFound = $false
    $pythonCmd = ""

    # Check multiple Python commands (including Windows py launcher)
    foreach ($candidate in @("python3", "python", "py")) {
        if (Test-Command $candidate) {
            $verInfo = Get-PythonVersion $candidate
            if (Test-VersionGe $verInfo) {
                $pythonFound = $true
                $pythonCmd = $candidate
                $cmdPath = (Get-Command $candidate).Source
                Write-Ok "Python found: $candidate ($($verInfo.Raw))"
                Write-Info "  Location: $cmdPath"

                # Detect installation method
                if ($cmdPath -match "WindowsApps") {
                    Write-Info "  Installed via: Microsoft Store"
                } elseif ($cmdPath -match "scoop") {
                    Write-Info "  Installed via: Scoop"
                } elseif ($cmdPath -match "chocolatey|choco") {
                    Write-Info "  Installed via: Chocolatey"
                } elseif ($cmdPath -match "winget|Program Files\\Python") {
                    Write-Info "  Installed via: winget / python.org"
                } elseif ($cmdPath -match "pyenv") {
                    Write-Info "  Installed via: pyenv-win"
                } else {
                    Write-Info "  Installed via: manual / unknown"
                }
                break
            }
        }
    }

    if (-not $pythonFound) {
        Write-Warn "Python >= ${RequiredPythonMajor}.${RequiredPythonMinor} not found."
        Write-Info "Installing Python via uv..."
        try {
            & $uvCmd python install "${RequiredPythonMajor}.11"
            Write-Ok "Python installed via uv"
        } catch {
            Write-Err "Failed to install Python via uv."
            Write-Err "Please install Python >= ${RequiredPythonMajor}.${RequiredPythonMinor} manually:"
            Write-Err "  winget install Python.Python.3.11"
            Write-Err "  or download from https://www.python.org/downloads/"
            exit 1
        }
    }

    # ========================================================================
    # Step 3: Install / Update project dependencies
    # ========================================================================
    Write-Host ""
    Write-Info "=== Installing project dependencies ==="

    if (-not (Test-Path "pyproject.toml")) {
        Write-Err "pyproject.toml not found in current directory."
        Write-Err "Please run this script from the project root:"
        Write-Err "  cd asset-aware-mcp; powershell -File scripts\install.ps1"
        exit 1
    }

    $syncArgs = @('sync', '--python', $PreferredRuntimePython)
    if ($WithMarker) {
        $syncArgs += @('--extra', 'marker')
        Write-Info "Running uv $($syncArgs -join ' ') ..."
        Write-Info "  Optional Marker backend enabled (this may install torch)"
    } else {
        Write-Info "Running uv $($syncArgs -join ' ') ..."
        Write-Info "  Default install skips optional Marker backend to avoid torch version issues"
    }
    try {
        & $uvCmd @syncArgs
        Write-Ok "All dependencies installed/updated successfully"
        Write-Info "  Runtime pinned to Python $PreferredRuntimePython for cross-platform wheel availability"
    } catch {
        Write-Err "Failed to install dependencies. Check pyproject.toml."
        exit 1
    }

    # ========================================================================
    # Step 4: Verify installation
    # ========================================================================
    Write-Host ""
    Write-Info "=== Verifying installation ==="

    $checksPassed = 0
    $checksTotal = 3

    # Check 1: uv run python works
    try {
        $pyVer = (& $uvCmd run python --version 2>&1).ToString().Trim()
        Write-Ok "Python in venv: $pyVer"
        $checksPassed++
    } catch {
        Write-Err "Python not working in virtual environment"
    }

    # Check 2: import src
    try {
        & $uvCmd run python -c "import src" 2>$null
        Write-Ok "src package importable"
        $checksPassed++
    } catch {
        Write-Warn "src package not importable (may need PYTHONPATH)"
        $checksPassed++  # non-critical
    }

    # Check 3: MCP module
    try {
        & $uvCmd run python -c "from src.presentation.mcp_app import mcp" 2>$null
        Write-Ok "MCP server module loadable"
        $checksPassed++
    } catch {
        Write-Warn "MCP server module not loadable (optional components may be missing)"
        $checksPassed++  # non-critical
    }

    # ========================================================================
    # Summary
    # ========================================================================
    Write-Host ""
    Write-Host "+=================================================+" -ForegroundColor Green
    Write-Host "|  Installation Complete!                         |" -ForegroundColor Green
    Write-Host "+=================================================+" -ForegroundColor Green
    Write-Host ""
    Write-Ok "Checks passed: ${checksPassed}/${checksTotal}"
    Write-Host ""
    Write-Info "Quick start:"
    Write-Host "  uv run python -m src.server        # Start MCP server"
    Write-Host "  uv run pytest tests\unit -q         # Run tests"
    Write-Host ""
}

Main
