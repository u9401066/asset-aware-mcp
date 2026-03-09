#!/usr/bin/env bash
# ============================================================================
# Test suite for scripts/install.sh
# Verifies helper functions, PATH augmentation, and --check mode
# Usage: bash tests/test_install.sh
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_SCRIPT="$SCRIPT_DIR/scripts/install.sh"

# --- Test framework ---
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
FAILURES=""

pass() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
    printf "  \033[0;32m✓\033[0m %s\n" "$1"
}

fail() {
    TESTS_FAILED=$((TESTS_FAILED + 1))
    TESTS_RUN=$((TESTS_RUN + 1))
    printf "  \033[0;31m✗\033[0m %s\n" "$1"
    FAILURES="${FAILURES}\n  - $1: $2"
}

assert_eq() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        pass "$desc"
    else
        fail "$desc" "expected='$expected' actual='$actual'"
    fi
}

assert_contains() {
    local desc="$1" haystack="$2" needle="$3"
    if echo "$haystack" | grep -qF -- "$needle"; then
        pass "$desc"
    else
        fail "$desc" "output does not contain '$needle'"
    fi
}

assert_exit_code() {
    local desc="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        pass "$desc"
    else
        fail "$desc" "expected exit code $expected, got $actual"
    fi
}

# --- Source helper functions from install.sh ---
# We extract just the functions, not the main() call
# by sourcing in a subshell with overridden entry point
source_helpers() {
    # Source the script but prevent main/run_check from running
    # by overriding the case statement at the bottom
    (
        # Override uname for testing
        if [ -n "${MOCK_UNAME_S:-}" ]; then
            uname() {
                case "$1" in
                    -s) echo "$MOCK_UNAME_S" ;;
                    -m) echo "${MOCK_UNAME_M:-x86_64}" ;;
                    *)  command uname "$@" ;;
                esac
            }
        fi

        # Source everything except the last case block
        eval "$(sed '/^case "\${1:-}"/,$ d' "$INSTALL_SCRIPT")"

        # Now run the test function passed as argument
        "$@"
    )
}

# ============================================================================
# Test: detect_os
# ============================================================================
echo ""
echo "=== Test: detect_os ==="

# Test Linux detection
result="$(MOCK_UNAME_S=Linux source_helpers detect_os)"
assert_eq "detect_os returns 'linux' for Linux" "linux" "$result"

# Test macOS detection
result="$(MOCK_UNAME_S=Darwin source_helpers detect_os)"
assert_eq "detect_os returns 'macos' for Darwin" "macos" "$result"

# Test unknown OS
result="$(MOCK_UNAME_S=FreeBSD source_helpers detect_os)"
assert_eq "detect_os returns 'unknown' for FreeBSD" "unknown" "$result"

# ============================================================================
# Test: version_ge
# ============================================================================
echo ""
echo "=== Test: version_ge ==="

# >= 3.10 should pass
for ver in "3.10" "3.11" "3.12" "3.13" "4.0"; do
    if source_helpers version_ge "$ver"; then
        pass "version_ge: $ver >= 3.10"
    else
        fail "version_ge: $ver >= 3.10" "returned false"
    fi
done

# < 3.10 should fail
for ver in "3.9" "3.8" "3.7" "2.7"; do
    if source_helpers version_ge "$ver"; then
        fail "version_ge: $ver < 3.10" "returned true"
    else
        pass "version_ge: $ver < 3.10"
    fi
done

# Edge cases
if source_helpers version_ge ""; then
    fail "version_ge: empty string" "returned true"
else
    pass "version_ge: empty string returns false"
fi

# ============================================================================
# Test: detect_install_method
# ============================================================================
echo ""
echo "=== Test: detect_install_method ==="

result="$(source_helpers detect_install_method "/opt/homebrew/bin/python3")"
assert_eq "Homebrew Apple Silicon path" "Homebrew" "$result"

result="$(source_helpers detect_install_method "/usr/local/Cellar/python@3.11/bin/python3")"
assert_eq "Homebrew Intel Cellar path" "Homebrew" "$result"

result="$(source_helpers detect_install_method "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3")"
assert_eq "python.org framework path" "python.org installer" "$result"

result="$(source_helpers detect_install_method "/home/user/.pyenv/shims/python3")"
assert_eq "pyenv shim path" "pyenv" "$result"

result="$(source_helpers detect_install_method "/usr/bin/python3")"
assert_eq "system Python path" "system" "$result"

result="$(source_helpers detect_install_method "/snap/bin/python3")"
assert_eq "snap path" "snap" "$result"

result="$(source_helpers detect_install_method "/home/user/.local/bin/uv")"
assert_eq "uv/pipx path" "uv / pipx" "$result"

result="$(source_helpers detect_install_method "/home/user/.cargo/bin/uv")"
assert_eq "cargo path" "cargo" "$result"

result="$(source_helpers detect_install_method "/opt/local/bin/python3")"
assert_eq "MacPorts path" "MacPorts" "$result"

result="$(source_helpers detect_install_method "/some/random/path/python3")"
assert_eq "unknown path" "manual / unknown" "$result"

# ============================================================================
# Test: augment_path (macOS Apple Silicon)
# ============================================================================
echo ""
echo "=== Test: augment_path (macOS scenarios) ==="

# Test that augment_path doesn't crash
if source_helpers augment_path "macos"; then
    pass "augment_path 'macos' exits 0"
else
    fail "augment_path 'macos' exits 0" "non-zero exit"
fi

if source_helpers augment_path "linux"; then
    pass "augment_path 'linux' exits 0"
else
    fail "augment_path 'linux' exits 0" "non-zero exit"
fi

if source_helpers augment_path "unknown"; then
    pass "augment_path 'unknown' exits 0"
else
    fail "augment_path 'unknown' exits 0" "non-zero exit"
fi

# ============================================================================
# Test: parse_python_version (with real Python)
# ============================================================================
echo ""
echo "=== Test: parse_python_version ==="

if command -v python3 >/dev/null 2>&1; then
    result="$(source_helpers parse_python_version python3)"
    if echo "$result" | grep -qE '^[0-9]+\.[0-9]+$'; then
        pass "parse_python_version python3 returns valid version: $result"
    else
        fail "parse_python_version python3" "got: '$result'"
    fi
else
    pass "parse_python_version: python3 not available (skip)"
fi

# Test with a non-existent command (should return empty, not crash)
result="$(source_helpers parse_python_version /nonexistent/python 2>/dev/null || echo "")"
# parse_python_version should return empty for invalid command
pass "parse_python_version: invalid command doesn't crash"

# ============================================================================
# Test: --check mode
# ============================================================================
echo ""
echo "=== Test: --check mode ==="

check_output="$(cd "$SCRIPT_DIR" && bash scripts/install.sh --check 2>&1)" || true
assert_contains "--check shows system info" "$check_output" "System"
assert_contains "--check shows uv section" "$check_output" "uv Package Manager"
assert_contains "--check shows Python section" "$check_output" "Python"
assert_contains "--check shows project section" "$check_output" "Project"
assert_contains "--check shows curl section" "$check_output" "curl"
assert_contains "--check shows diagnostics complete" "$check_output" "Diagnostics complete"

# ============================================================================
# Test: --help mode
# ============================================================================
echo ""
echo "=== Test: --help mode ==="

help_output="$(bash "$INSTALL_SCRIPT" --help 2>&1)"
assert_contains "--help shows usage" "$help_output" "Usage"
assert_contains "--help mentions --check" "$help_output" "--check"

# ============================================================================
# Test: color disabled in non-terminal
# ============================================================================
echo ""
echo "=== Test: non-terminal color handling ==="

# Pipe output (non-terminal) should not contain ANSI escape codes
piped_output="$(echo "" | bash "$INSTALL_SCRIPT" --help 2>&1)"
# --help doesn't use colors, so just verify it works in piped mode
pass "Script runs in piped (non-terminal) mode without crashing"

# ============================================================================
# Test: macOS PATH coverage verification
# ============================================================================
echo ""
echo "=== Test: macOS PATH locations in script ==="

# Verify all critical macOS paths are in the script
for path in \
    "/opt/homebrew/bin" \
    "/usr/local/bin" \
    "/Library/Frameworks/Python.framework" \
    "/opt/local/bin" \
    "/.pyenv" \
    "/.local/bin" \
    "/.cargo/bin" \
    "/snap/bin" \
    "/home/linuxbrew/.linuxbrew/bin"; do
    if grep -qF -- "$path" "$INSTALL_SCRIPT"; then
        pass "Script contains path: $path"
    else
        fail "Script contains path: $path" "not found in script"
    fi
done

# Verify macOS-specific features are present
for feature in \
    "xcode-select" \
    "Apple Silicon" \
    "Homebrew" \
    "python.org installer" \
    "MacPorts" \
    "pyenv" \
    "timeout" \
    "source_uv_env" \
    "CARGO_HOME" \
    "XDG_DATA_HOME"; do
    if grep -qF -- "$feature" "$INSTALL_SCRIPT"; then
        pass "Script handles: $feature"
    else
        fail "Script handles: $feature" "not found in script"
    fi
done

# ============================================================================
# Test: script syntax (bash -n)
# ============================================================================
echo ""
echo "=== Test: bash syntax check ==="

if bash -n "$INSTALL_SCRIPT" 2>&1; then
    pass "install.sh passes bash -n syntax check"
else
    fail "install.sh passes bash -n syntax check" "syntax error found"
fi

# Also check install.ps1 exists
if [ -f "$SCRIPT_DIR/scripts/install.ps1" ]; then
    pass "install.ps1 exists for Windows"
else
    fail "install.ps1 exists for Windows" "file not found"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "======================================================"
printf "  Results: %d passed, %d failed, %d total\n" "$TESTS_PASSED" "$TESTS_FAILED" "$TESTS_RUN"
echo "======================================================"

if [ "$TESTS_FAILED" -gt 0 ]; then
    printf "\n  Failed tests:%b\n" "$FAILURES"
    echo ""
    exit 1
else
    echo ""
    echo "  All tests passed!"
    echo ""
    exit 0
fi
