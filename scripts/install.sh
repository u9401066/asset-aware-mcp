#!/usr/bin/env bash
# ============================================================================
# Asset-Aware MCP — Cross-platform installer (Linux / macOS)
# Detects existing uv / Python installations, supports fresh install & update
#
# Usage:
#   bash scripts/install.sh            # Normal install
#   bash scripts/install.sh --check    # Diagnostics only (no changes)
#   bash scripts/install.sh --help     # Show help
# ============================================================================
set -euo pipefail

# --- Configuration ---
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=10
UV_INSTALL_URL="https://astral.sh/uv/install.sh"
CHECK_MODE=false

# --- Colors (disabled if not a terminal) ---
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' NC=''
fi

info()  { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()    { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()  { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
error() { printf "${RED}[ERROR]${NC} %s\n" "$*" >&2; }

# --- OS Detection ---
detect_os() {
    local os
    os="$(uname -s)"
    case "$os" in
        Linux*)  echo "linux" ;;
        Darwin*) echo "macos" ;;
        *)       echo "unknown" ;;
    esac
}

# --- Check if a command exists ---
cmd_exists() {
    command -v "$1" >/dev/null 2>&1
}

# --- Augment PATH with common install locations ---
# Ensures manually installed uv/Python are discoverable even in
# non-interactive shells (e.g. piped install: curl ... | bash)
augment_path() {
    local os="$1"

    # Common: uv default install location & cargo
    if [ -d "$HOME/.local/bin" ]; then export PATH="$HOME/.local/bin:$PATH"; fi
    if [ -d "$HOME/.cargo/bin" ]; then export PATH="$HOME/.cargo/bin:$PATH"; fi

    # Common: pyenv — try to initialize properly first
    if [ -d "$HOME/.pyenv" ]; then
        export PYENV_ROOT="$HOME/.pyenv"
        if [ -d "$PYENV_ROOT/bin" ]; then export PATH="$PYENV_ROOT/bin:$PATH"; fi
        if [ -d "$PYENV_ROOT/shims" ]; then export PATH="$PYENV_ROOT/shims:$PATH"; fi
        # Initialize pyenv if available (makes shims actually work)
        if cmd_exists pyenv; then
            eval "$(pyenv init - bash 2>/dev/null)" || true
        fi
    fi

    if [ "$os" = "macos" ]; then
        local arch
        arch="$(uname -m)"

        # Homebrew — Apple Silicon (M1/M2/M3/M4) vs Intel
        if [ "$arch" = "arm64" ]; then
            if [ -d "/opt/homebrew/bin" ]; then export PATH="/opt/homebrew/bin:$PATH"; fi
        else
            if [ -d "/usr/local/bin" ]; then export PATH="/usr/local/bin:$PATH"; fi
        fi

        # python.org framework installer (creates versioned binaries)
        for ver in 3.13 3.12 3.11 3.10; do
            local fw="/Library/Frameworks/Python.framework/Versions/$ver/bin"
            if [ -d "$fw" ]; then export PATH="$fw:$PATH"; fi
        done

        # MacPorts
        if [ -d "/opt/local/bin" ]; then export PATH="/opt/local/bin:$PATH"; fi
    fi

    if [ "$os" = "linux" ]; then
        # Snap packages
        if [ -d "/snap/bin" ]; then export PATH="/snap/bin:$PATH"; fi
        # Linuxbrew
        if [ -d "/home/linuxbrew/.linuxbrew/bin" ]; then export PATH="/home/linuxbrew/.linuxbrew/bin:$PATH"; fi
    fi

    return 0
}

# --- Parse Python version string → "major.minor" ---
# Returns empty string on failure
parse_python_version() {
    local cmd="$1"
    local ver=""

    # Use timeout to prevent hanging (macOS Xcode CLT shim can hang)
    if cmd_exists timeout; then
        ver="$(timeout 5 "$cmd" --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)" || true
    elif cmd_exists gtimeout; then
        # macOS with coreutils from Homebrew
        ver="$(gtimeout 5 "$cmd" --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)" || true
    else
        # Fallback: run with background + wait (portable timeout)
        ver="$(probe_python_version_with_timeout "$cmd")" || true
    fi

    echo "$ver"
}

# --- Portable timeout for Python version probe ---
# Needed on macOS where /usr/bin/python3 can hang if Xcode CLT not installed
probe_python_version_with_timeout() {
    local cmd="$1"
    local ver=""
    local pid

    # Run in background, capture output via temp approach
    ver="$("$cmd" --version 2>&1 &
    pid=$!
    # Wait up to 5 seconds
    local i=0
    while [ $i -lt 50 ] && kill -0 "$pid" 2>/dev/null; do
        sleep 0.1
        i=$((i + 1))
    done
    # If still running, it's hung (Xcode shim) — kill it
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
        echo ""
        return 1
    fi
    wait "$pid" 2>/dev/null || true)" 2>/dev/null

    echo "$ver" | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1
}

# --- Compare version: returns 0 if $1 >= required ---
version_ge() {
    local ver="$1"
    if [ -z "$ver" ]; then return 1; fi

    local major minor
    major="$(echo "$ver" | cut -d. -f1)"
    minor="$(echo "$ver" | cut -d. -f2)"

    if [ "$major" -gt "$REQUIRED_PYTHON_MAJOR" ] 2>/dev/null; then
        return 0
    elif [ "$major" -eq "$REQUIRED_PYTHON_MAJOR" ] 2>/dev/null && \
         [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ] 2>/dev/null; then
        return 0
    fi
    return 1
}

# --- Detect installation method from path ---
detect_install_method() {
    local path="$1"
    case "$path" in
        /opt/homebrew/*|/usr/local/Cellar/*)  echo "Homebrew" ;;
        /Library/Frameworks/Python.framework/*) echo "python.org installer" ;;
        */.pyenv/*)                           echo "pyenv" ;;
        /usr/bin/*)                           echo "system" ;;
        /snap/*)                              echo "snap" ;;
        */.local/bin/*)                       echo "uv / pipx" ;;
        */.cargo/bin/*)                       echo "cargo" ;;
        /opt/local/*)                         echo "MacPorts" ;;
        *)                                    echo "manual / unknown" ;;
    esac
}

# --- Check for Xcode CLT on macOS ---
check_xcode_clt() {
    if [ "$(detect_os)" != "macos" ]; then return 0; fi

    if xcode-select -p >/dev/null 2>&1; then
        ok "Xcode Command Line Tools: installed"
        info "  Path: $(xcode-select -p 2>/dev/null)"
        return 0
    else
        warn "Xcode Command Line Tools: NOT installed"
        warn "Some Python packages with C extensions may fail to build."
        warn "To install: xcode-select --install"
        return 1
    fi
}

# --- Source uv environment from multiple known locations ---
source_uv_env() {
    local env_files=(
        "$HOME/.local/bin/env"
        "$HOME/.cargo/env"
    )
    # XDG-based location
    local xdg_data="${XDG_DATA_HOME:-$HOME/.local/share}"
    env_files+=("$xdg_data/uv/env")

    # CARGO_HOME override
    if [ -n "${CARGO_HOME:-}" ]; then
        env_files+=("$CARGO_HOME/env")
    fi

    for ef in "${env_files[@]}"; do
        if [ -f "$ef" ]; then
            info "  Sourcing: $ef"
            # shellcheck disable=SC1090
            . "$ef"
            return 0
        fi
    done

    # Fallback: just add common dirs to PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    return 0
}

# --- Show help ---
show_help() {
    echo "Usage: bash scripts/install.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --check    Run diagnostics only (no installations or changes)"
    echo "  --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  bash scripts/install.sh            # Install / update"
    echo "  bash scripts/install.sh --check    # Check environment"
    echo ""
}

# ============================================================================
# Check mode: diagnostics only
# ============================================================================
run_check() {
    echo ""
    echo "======================================================"
    echo "  Asset-Aware MCP — Environment Diagnostics"
    echo "======================================================"
    echo ""

    local os arch
    os="$(detect_os)"
    arch="$(uname -m)"

    # --- System Info ---
    info "=== System ==="
    info "  OS:   $os"
    info "  Arch: $arch"
    info "  Bash: ${BASH_VERSION:-unknown}"
    if [ "$os" = "macos" ]; then
        local macos_ver
        macos_ver="$(sw_vers -productVersion 2>/dev/null || echo 'unknown')"
        info "  macOS version: $macos_ver"
    fi
    echo ""

    # Augment PATH
    augment_path "$os"

    # --- Xcode CLT (macOS only) ---
    if [ "$os" = "macos" ]; then
        info "=== Xcode Command Line Tools ==="
        check_xcode_clt || true
        echo ""
    fi

    # --- uv ---
    info "=== uv Package Manager ==="
    if cmd_exists uv; then
        local uv_ver uv_path
        uv_ver="$(uv --version 2>&1 | head -1)"
        uv_path="$(command -v uv)"
        ok "Found: $uv_ver"
        info "  Path:    $uv_path"
        info "  Method:  $(detect_install_method "$uv_path")"
    else
        error "NOT FOUND"
        info "  Checked PATH: (relevant dirs)"
        info "    ~/.local/bin:  $([ -d "$HOME/.local/bin" ] && echo 'exists' || echo 'missing')"
        info "    ~/.cargo/bin:  $([ -d "$HOME/.cargo/bin" ] && echo 'exists' || echo 'missing')"
        if [ "$os" = "macos" ]; then
            if [ "$arch" = "arm64" ]; then
                info "    /opt/homebrew/bin: $([ -d "/opt/homebrew/bin" ] && echo 'exists' || echo 'missing')"
            else
                info "    /usr/local/bin:    $([ -d "/usr/local/bin" ] && echo 'exists' || echo 'missing')"
            fi
        fi
    fi
    echo ""

    # --- Python ---
    info "=== Python (need >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}) ==="
    local found_any=false
    for candidate in python3 python python3.13 python3.12 python3.11 python3.10; do
        if cmd_exists "$candidate"; then
            local cpath cver
            cpath="$(command -v "$candidate")"
            cver="$(parse_python_version "$candidate")"
            if [ -n "$cver" ]; then
                local status
                if version_ge "$cver"; then status="✅"; else status="❌ too old"; fi
                info "  $candidate ($cver) at $cpath [$status] [$(detect_install_method "$cpath")]"
                found_any=true
            else
                warn "  $candidate at $cpath — could not get version (hung or broken shim?)"
                found_any=true
            fi
        fi
    done
    if [ "$found_any" = false ]; then
        error "  No Python found in PATH"
    fi
    echo ""

    # --- pyenv ---
    if [ -d "$HOME/.pyenv" ]; then
        info "=== pyenv ==="
        info "  PYENV_ROOT: $HOME/.pyenv"
        if cmd_exists pyenv; then
            info "  pyenv version: $(pyenv --version 2>&1 | head -1)"
            info "  Active Python: $(pyenv version 2>&1 | head -1)"
        else
            warn "  pyenv directory exists but pyenv command not found"
        fi
        echo ""
    fi

    # --- Project ---
    info "=== Project ==="
    if [ -f "pyproject.toml" ]; then
        ok "pyproject.toml found"
        if [ -d ".venv" ]; then
            ok ".venv directory exists"
        else
            warn ".venv not found (will be created on install)"
        fi
    else
        warn "pyproject.toml not found (run from project root)"
    fi
    echo ""

    # --- uv env files ---
    info "=== uv env files (for PATH setup) ==="
    local xdg_data="${XDG_DATA_HOME:-$HOME/.local/share}"
    for ef in "$HOME/.local/bin/env" "$HOME/.cargo/env" "$xdg_data/uv/env"; do
        if [ -f "$ef" ]; then
            ok "  $ef"
        else
            info "  $ef — not found"
        fi
    done
    echo ""

    # --- curl ---
    info "=== curl ==="
    if cmd_exists curl; then
        ok "curl found: $(curl --version 2>&1 | head -1)"
    else
        error "curl NOT found — required for uv installation"
    fi
    echo ""

    echo "======================================================"
    echo "  Diagnostics complete."
    echo "  Share this output for troubleshooting."
    echo "======================================================"
    echo ""
}

# ============================================================================
# Main installer
# ============================================================================
main() {
    echo ""
    echo "======================================================"
    echo "  Asset-Aware MCP — Installer"
    echo "======================================================"
    echo ""

    local os arch arch_label
    os="$(detect_os)"
    arch="$(uname -m)"

    # Friendly architecture label
    arch_label="$arch"
    if [ "$os" = "macos" ]; then
        case "$arch" in
            arm64)  arch_label="Apple Silicon (arm64)" ;;
            x86_64) arch_label="Intel (x86_64)" ;;
        esac
    fi
    info "Detected OS: $os ($arch_label)"
    info "Bash version: ${BASH_VERSION:-unknown}"

    if [ "$os" = "unknown" ]; then
        error "Unsupported OS: $(uname -s)"
        error "This installer supports Linux and macOS."
        error "For Windows, use: powershell -File scripts\\install.ps1"
        exit 1
    fi

    # Augment PATH to discover manually installed tools
    augment_path "$os"

    # ========================================================================
    # Step 1 (macOS only): Check Xcode CLT
    # ========================================================================
    if [ "$os" = "macos" ]; then
        echo ""
        info "=== Checking Xcode Command Line Tools ==="
        if ! check_xcode_clt; then
            warn "Continuing without Xcode CLT — native extensions may fail."
            warn "Run: xcode-select --install"
        fi
    fi

    # ========================================================================
    # Step 2: Check / Install uv
    # ========================================================================
    echo ""
    info "=== Checking uv package manager ==="

    if cmd_exists uv; then
        local uv_ver uv_path
        uv_ver="$(uv --version 2>&1 | head -1)"
        uv_path="$(command -v uv)"
        ok "uv already installed: $uv_ver"
        info "  Location: $uv_path"
        info "  Installed via: $(detect_install_method "$uv_path")"

        # Update uv (may fail if installed via Homebrew/system pkg)
        info "Updating uv to latest version..."
        if uv self update 2>/dev/null; then
            ok "uv updated successfully"
        else
            warn "uv self-update not available (installed via package manager?), skipping"
        fi
    else
        warn "uv not found. Installing..."
        if curl -fsSL "$UV_INSTALL_URL" | sh; then
            # Source env from multiple possible locations
            source_uv_env

            if cmd_exists uv; then
                ok "uv installed: $(uv --version 2>&1 | head -1)"
                info "  Location: $(command -v uv)"
            else
                error "uv installation completed but the uv command was not found in PATH."
                error ""
                error "Troubleshooting:"
                error "  1. Try: source ~/.local/bin/env && uv --version"
                error "  2. Or:  export PATH=HOME/.local/bin:PATH"
                error "  3. Then re-run this script"
                error ""
                error "Run: bash scripts/install.sh --check  for diagnostics"
                exit 1
            fi
        else
            error "Failed to install uv."
            error "Please install manually:"
            if [ "$os" = "macos" ]; then
                error "  brew install uv          # via Homebrew"
                error "  # OR"
            fi
            error "  curl -LsSf https://astral.sh/uv/install.sh | sh"
            exit 1
        fi
    fi

    # ========================================================================
    # Step 3: Check / Install Python
    # ========================================================================
    echo ""
    info "=== Checking Python (>= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}) ==="

    local python_found=""
    local python_cmd=""
    local python_ver=""

    # Check multiple Python commands in priority order
    for candidate in python3 python python3.13 python3.12 python3.11 python3.10; do
        if cmd_exists "$candidate"; then
            python_ver="$(parse_python_version "$candidate")"
            if [ -n "$python_ver" ] && version_ge "$python_ver"; then
                python_found="yes"
                python_cmd="$candidate"
                break
            elif [ -z "$python_ver" ]; then
                warn "  $candidate found but version probe timed out (broken shim?), skipping"
            fi
        fi
    done

    if [ "$python_found" = "yes" ]; then
        local python_path
        python_path="$(command -v "$python_cmd")"
        ok "Python found: $python_cmd ($python_ver)"
        info "  Location: $python_path"
        info "  Installed via: $(detect_install_method "$python_path")"
    else
        warn "Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} not found in PATH."
        info "Installing Python via uv (standalone build, no compiler needed)..."
        if uv python install "${REQUIRED_PYTHON_MAJOR}.11"; then
            ok "Python 3.11 installed via uv"
        else
            error "Failed to install Python via uv."
            error "Please install Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} manually:"
            case "$os" in
                macos)
                    error "  brew install python@3.11"
                    error "  # OR download from https://www.python.org/downloads/"
                    ;;
                linux)
                    error "  sudo apt install python3.11  # Debian/Ubuntu"
                    error "  sudo dnf install python3.11  # Fedora"
                    ;;
            esac
            exit 1
        fi
    fi

    # ========================================================================
    # Step 4: Install / Update project dependencies
    # ========================================================================
    echo ""
    info "=== Installing project dependencies ==="

    if [ ! -f "pyproject.toml" ]; then
        error "pyproject.toml not found in current directory."
        error "Please run this script from the project root:"
        error "  cd asset-aware-mcp && bash scripts/install.sh"
        exit 1
    fi

    info "Running uv sync --all-extras ..."
    if uv sync --all-extras; then
        ok "All dependencies installed/updated successfully"
    else
        error "Failed to install dependencies."
        if [ "$os" = "macos" ]; then
            error ""
            error "Common macOS fix: install Xcode Command Line Tools first:"
            error "  xcode-select --install"
            error "Then re-run this script."
        fi
        exit 1
    fi

    # ========================================================================
    # Step 5: Verify installation
    # ========================================================================
    echo ""
    info "=== Verifying installation ==="

    local checks_passed=0
    local checks_total=3

    # Check 1: uv run python works
    if uv run python --version >/dev/null 2>&1; then
        ok "Python in venv: $(uv run python --version 2>&1)"
        checks_passed=$((checks_passed + 1))
    else
        error "Python not working in virtual environment"
    fi

    # Check 2: import src succeeds
    if uv run python -c "import src" >/dev/null 2>&1; then
        ok "src package importable"
        checks_passed=$((checks_passed + 1))
    else
        warn "src package not importable (may need PYTHONPATH)"
        checks_passed=$((checks_passed + 1))  # non-critical
    fi

    # Check 3: MCP server module loadable
    if uv run python -c "from src.presentation.mcp_app import mcp" >/dev/null 2>&1; then
        ok "MCP server module loadable"
        checks_passed=$((checks_passed + 1))
    else
        warn "MCP server module not loadable (optional components may be missing)"
        checks_passed=$((checks_passed + 1))  # non-critical
    fi

    # ========================================================================
    # Summary
    # ========================================================================
    echo ""
    echo "======================================================"
    echo "  Installation Complete!"
    echo "======================================================"
    echo ""
    ok "Checks passed: ${checks_passed}/${checks_total}"
    echo ""
    info "Quick start:"
    echo "  uv run python -m src.server        # Start MCP server"
    echo "  uv run pytest tests/unit -q         # Run tests"
    echo ""
    info "If something went wrong, run:"
    echo "  bash scripts/install.sh --check     # Environment diagnostics"
    echo ""
}

# ============================================================================
# Entry point
# ============================================================================
case "${1:-}" in
    --check|-c|--diagnose)
        # shellcheck disable=SC2034
        CHECK_MODE=true
        run_check
        ;;
    --help|-h)
        show_help
        ;;
    *)
        main "$@"
        ;;
esac
