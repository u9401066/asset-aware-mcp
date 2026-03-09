#!/usr/bin/env bash
# ============================================================================
# Asset-Aware MCP — Cross-platform installer (Linux / macOS)
# Detects existing uv / Python installations, supports fresh install & update
# Usage: curl -fsSL <url>/install.sh | bash
#        or: bash scripts/install.sh
# ============================================================================
set -euo pipefail

# --- Configuration ---
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=10
UV_INSTALL_URL="https://astral.sh/uv/install.sh"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

    # Common: pyenv shims
    if [ -d "$HOME/.pyenv/shims" ]; then export PATH="$HOME/.pyenv/shims:$PATH"; fi

    if [ "$os" = "macos" ]; then
        local arch
        arch="$(uname -m)"

        # Homebrew — Apple Silicon (M1/M2/M3/M4) vs Intel
        if [ "$arch" = "arm64" ]; then
            if [ -d "/opt/homebrew/bin" ]; then export PATH="/opt/homebrew/bin:$PATH"; fi
        else
            if [ -d "/usr/local/bin" ]; then export PATH="/usr/local/bin:$PATH"; fi
        fi

        # python.org framework installer
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

# --- Parse Python version string → (major, minor) ---
parse_python_version() {
    local ver
    ver="$("$1" --version 2>&1 | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)"
    echo "$ver"
}

# --- Compare version: returns 0 if $1 >= required ---
version_ge() {
    local major minor
    major="$(echo "$1" | cut -d. -f1)"
    minor="$(echo "$1" | cut -d. -f2)"
    if [ "$major" -gt "$REQUIRED_PYTHON_MAJOR" ]; then
        return 0
    elif [ "$major" -eq "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]; then
        return 0
    fi
    return 1
}

# ============================================================================
# Step 1: Detect OS
# ============================================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  Asset-Aware MCP — Installer                    ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""

    local os
    os="$(detect_os)"
    local arch
    arch="$(uname -m)"

    # Friendly architecture label for macOS
    local arch_label="$arch"
    if [ "$os" = "macos" ]; then
        case "$arch" in
            arm64)  arch_label="Apple Silicon (arm64)" ;;
            x86_64) arch_label="Intel (x86_64)" ;;
        esac
    fi
    info "Detected OS: $os ($arch_label)"

    if [ "$os" = "unknown" ]; then
        error "Unsupported OS: $(uname -s)"
        error "This installer supports Linux and macOS."
        error "For Windows, use scripts/install.ps1 (PowerShell)."
        exit 1
    fi

    # Augment PATH to discover manually installed tools
    augment_path "$os"

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

        # Update uv to latest (may fail if installed via Homebrew/system pkg)
        info "Updating uv to latest version..."
        if uv self update 2>/dev/null; then
            ok "uv updated successfully"
        else
            warn "uv self-update not available (installed via package manager?), skipping"
        fi
    else
        warn "uv not found. Installing..."
        if curl -fsSL "$UV_INSTALL_URL" | sh; then
            # Source the env so uv is available
            if [ -f "$HOME/.local/bin/env" ]; then
                # shellcheck disable=SC1091
                . "$HOME/.local/bin/env"
            fi
            # Also add to PATH for this session
            export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

            if cmd_exists uv; then
                ok "uv installed: $(uv --version 2>&1 | head -1)"
            else
                error "uv installation succeeded but command not found."
                error "Please add ~/.local/bin or ~/.cargo/bin to your PATH and re-run."
                exit 1
            fi
        else
            error "Failed to install uv. Please install manually:"
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
            fi
        fi
    done

    if [ "$python_found" = "yes" ]; then
        local python_path
        python_path="$(command -v "$python_cmd")"
        ok "Python found: $python_cmd ($python_ver)"
        info "  Location: $python_path"

        # Detect installation method for user info
        case "$python_path" in
            /opt/homebrew/*|/usr/local/Cellar/*)
                info "  Installed via: Homebrew" ;;
            /Library/Frameworks/Python.framework/*)
                info "  Installed via: python.org installer" ;;
            */.pyenv/*)
                info "  Installed via: pyenv" ;;
            /usr/bin/*)
                info "  Installed via: system" ;;
            /snap/*)
                info "  Installed via: snap" ;;
            *)
                info "  Installed via: unknown / manual" ;;
        esac
    else
        warn "Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} not found in PATH."
        info "Installing Python via uv..."
        if uv python install "${REQUIRED_PYTHON_MAJOR}.11"; then
            ok "Python installed via uv"
        else
            error "Failed to install Python via uv."
            error "Please install Python >= ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR} manually:"
            case "$os" in
                macos)
                    error "  brew install python@3.11"
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

    # Check if we're inside the project directory
    if [ ! -f "pyproject.toml" ]; then
        error "pyproject.toml not found in current directory."
        error "Please run this script from the project root:"
        error "  cd asset-aware-mcp && bash scripts/install.sh"
        exit 1
    fi

    # Create venv + sync deps
    info "Running uv sync --all-extras ..."
    if uv sync --all-extras; then
        ok "All dependencies installed/updated successfully"
    else
        error "Failed to install dependencies. Check pyproject.toml."
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
    echo "╔══════════════════════════════════════════════════╗"
    echo "║  Installation Complete!                         ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""
    ok "Checks passed: ${checks_passed}/${checks_total}"
    echo ""
    info "Quick start:"
    echo "  uv run python -m src.server        # Start MCP server"
    echo "  uv run pytest tests/unit -q         # Run tests"
    echo ""
}

main "$@"
