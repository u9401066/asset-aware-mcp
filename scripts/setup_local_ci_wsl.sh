#!/usr/bin/env bash
# ============================================================================
# Provision the Ubuntu WSL distro that scripts/pretest.py uses for every
# ubuntu-latest CI job (static analysis, unit, integration/LibreOffice, Python
# minimum-version smoke, npm audits, Linux VSIX smoke, release `test`).
#
# Installs exactly what the workflows install on top of the runner image:
#   * every package named by `apt-get install` in .github/workflows/{ci,release}.yml
#   * uv at the version pinned for astral-sh/setup-uv
#   * the newest Node.js release of the NODE_VERSION major (what setup-node picks)
#   * a non-root `runner` user (uid 1001, like GitHub's runner) that owns the
#     job checkouts under /home/runner/aam-ci (fast ext4, not the /mnt/<drive>
#     9p mount, and never the Windows working tree or its .venv)
#
# Idempotent: re-running only installs or upgrades what is missing or stale.
#
# Usage (from Windows; run wsl.exe from an ASCII working directory):
#   python scripts/pretest.py --setup-wsl
#   wsl.exe -d Ubuntu-26.04 -u root --exec bash /mnt/e/path/to/repo/scripts/setup_local_ci_wsl.sh
#
# Environment overrides:
#   PRETEST_UBUNTU_VERSION  expected VERSION_ID (default 26.04 = ubuntu-latest)
#   PRETEST_CI_USER / PRETEST_CI_UID   job user (default runner / 1001)
#   PRETEST_APT_HTTPS=0     keep http:// apt mirrors (default rewrites the stock
#                           archive/security mirrors to https://; some networks
#                           reset plain-HTTP requests carrying APT's User-Agent)
# ============================================================================
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED_UBUNTU="${PRETEST_UBUNTU_VERSION:-26.04}"
CI_USER="${PRETEST_CI_USER:-runner}"
CI_UID="${PRETEST_CI_UID:-1001}"
APT_HTTPS="${PRETEST_APT_HTTPS:-1}"
CI_HOME="/home/${CI_USER}"

log() { printf '[setup-local-ci] %s\n' "$*"; }
die() { printf '[setup-local-ci] ERROR: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "run as root, e.g. wsl.exe -d Ubuntu-26.04 -u root --exec bash $0"
[ -f "$REPO_ROOT/.github/workflows/ci.yml" ] || die "cannot find .github/workflows/ci.yml under $REPO_ROOT"

# shellcheck disable=SC1091
. /etc/os-release
[ "${ID:-}" = "ubuntu" ] || die "expected Ubuntu, found ${PRETTY_NAME:-unknown}"
[ "${VERSION_ID:-}" = "$EXPECTED_UBUNTU" ] || die "expected Ubuntu $EXPECTED_UBUNTU (GitHub ubuntu-latest), found ${VERSION_ID:-unknown}"
case "$(uname -m)" in
    x86_64) ARCH_UV=x86_64-unknown-linux-gnu; ARCH_NODE=linux-x64 ;;
    aarch64) ARCH_UV=aarch64-unknown-linux-gnu; ARCH_NODE=linux-arm64 ;;
    *) die "unsupported architecture $(uname -m)" ;;
esac

# --- Requirements, read from the workflows so they cannot drift ------------
eval "$(python3 - "$REPO_ROOT" <<'PY'
import re
import shlex
import sys
from pathlib import Path

root = Path(sys.argv[1])
texts = [(root / ".github/workflows" / name).read_text(encoding="utf-8") for name in ("ci.yml", "release.yml")]
packages, lines = [], []
for text in texts:
    for match in re.finditer(r"apt-get install([^\n&;|]*)", text):
        tokens = match.group(1).split()
        if " ".join(tokens) not in lines:
            lines.append(" ".join(tokens))
        packages.extend(t for t in tokens if not t.startswith("-") and t not in packages)
uv = {m.group(1) for t in texts for m in re.finditer(r"setup-uv@[^\n]*\n(?:[ \t]+[^\n]*\n)*?[ \t]+version:\s*\"([^\"]+)\"", t)}
node = {m.group(1) for t in texts for m in re.finditer(r"^\s*NODE_VERSION:\s*\"(\d+)\"", t, re.M)}
python = {m.group(1) for t in texts for m in re.finditer(r"^\s*PYTHON_VERSION:\s*\"([\d.]+)\"", t, re.M)}
for label, values in (("uv", uv), ("NODE_VERSION", node), ("PYTHON_VERSION", python)):
    if len(values) != 1:
        sys.exit(f"echo 'ambiguous {label} pins in workflows: {sorted(values)}' >&2; exit 1")
print(f"APT_PACKAGES={shlex.quote(' '.join(packages))}")
print("APT_INSTALL_LINES=(" + " ".join(shlex.quote(line) for line in lines) + ")")
print(f"UV_VERSION={shlex.quote(uv.pop())}")
print(f"NODE_MAJOR={shlex.quote(node.pop())}")
print(f"PYTHON_VERSION={shlex.quote(python.pop())}")
PY
)"
log "workflow pins: uv ${UV_VERSION}, Node ${NODE_MAJOR}.x, Python ${PYTHON_VERSION}"
log "workflow apt packages: ${APT_PACKAGES}"

# --- 1. apt sources and packages ---------------------------------------------
SOURCES=/etc/apt/sources.list.d/ubuntu.sources
if [ "$APT_HTTPS" = "1" ] && [ -f "$SOURCES" ] && grep -Eq 'http://(archive|security)\.ubuntu\.com/' "$SOURCES"; then
    [ -f "$SOURCES.pretest-orig" ] || cp "$SOURCES" "$SOURCES.pretest-orig"
    sed -i -E 's#http://(archive|security)\.ubuntu\.com/#https://\1.ubuntu.com/#g' "$SOURCES"
    log "switched Ubuntu mirrors to https (backup: $SOURCES.pretest-orig)"
fi

UPDATE_LOG="$(mktemp)"
apt-get update 2>&1 | tee "$UPDATE_LOG"
if grep -Eq '^(W: Failed to fetch|E: )' "$UPDATE_LOG"; then
    rm -f "$UPDATE_LOG"
    die "apt-get update could not refresh every index; fix network/mirrors so LibreOffice matches the CI archive version"
fi
rm -f "$UPDATE_LOG"

# Base tools the gate itself needs (git checkout, downloads); present on GitHub's image.
BASE_PACKAGES="ca-certificates curl git xz-utils"
# shellcheck disable=SC2086
apt-get install -y --no-install-recommends $BASE_PACKAGES
# Replay every workflow `apt-get install` line with its own flags (the
# integration job uses --no-install-recommends, the VSIX smokes do not). apt
# upgrades in place when the archive moved on, so LibreOffice tracks CI.
for line in "${APT_INSTALL_LINES[@]}"; do
    # shellcheck disable=SC2086
    apt-get install $line
done

# --- 2. CI user ----------------------------------------------------------------
if ! id "$CI_USER" >/dev/null 2>&1; then
    useradd --create-home --uid "$CI_UID" --shell /bin/bash "$CI_USER"
    log "created user $CI_USER (uid $CI_UID)"
fi
install -d -o "$CI_USER" -g "$CI_USER" "$CI_HOME/aam-ci"

# --- 3. uv (exact pin) -----------------------------------------------------------
current_uv="$(/usr/local/bin/uv --version 2>/dev/null | awk '{print $2}' || true)"
if [ "$current_uv" != "$UV_VERSION" ]; then
    work="$(mktemp -d)"
    base="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${ARCH_UV}.tar.gz"
    curl -fsSL --retry 3 -o "$work/uv.tar.gz" "$base"
    curl -fsSL --retry 3 -o "$work/uv.tar.gz.sha256" "$base.sha256"
    expected="$(awk '{print $1}' "$work/uv.tar.gz.sha256")"
    echo "$expected  $work/uv.tar.gz" | sha256sum -c -
    tar -xzf "$work/uv.tar.gz" -C "$work"
    install -m 0755 "$work/uv-${ARCH_UV}/uv" "$work/uv-${ARCH_UV}/uvx" /usr/local/bin/
    rm -rf "$work"
    log "installed uv ${UV_VERSION} (was: ${current_uv:-none})"
fi

# --- 4. Node.js (newest release of the pinned major, as setup-node resolves it) --
shasums="$(curl -fsSL --retry 3 "https://nodejs.org/dist/latest-v${NODE_MAJOR}.x/SHASUMS256.txt")"
node_line="$(printf '%s\n' "$shasums" | grep -E " node-v${NODE_MAJOR}\.[0-9]+\.[0-9]+-${ARCH_NODE}\.tar\.xz$")"
node_archive="$(printf '%s' "$node_line" | awk '{print $2}')"
node_version="${node_archive#node-}"
node_version="${node_version%-"${ARCH_NODE}".tar.xz}"
current_node="$(/usr/local/bin/node --version 2>/dev/null || true)"
if [ "$current_node" != "$node_version" ]; then
    work="$(mktemp -d)"
    curl -fsSL --retry 3 -o "$work/$node_archive" "https://nodejs.org/dist/${node_version}/${node_archive}"
    (cd "$work" && printf '%s\n' "$node_line" | sha256sum -c -)
    install -d /opt/node
    rm -rf "/opt/node/${node_version}"
    tar -xJf "$work/$node_archive" -C /opt/node
    mv "/opt/node/${node_archive%.tar.xz}" "/opt/node/${node_version}"
    for tool in node npm npx corepack; do
        ln -sfn "/opt/node/${node_version}/bin/${tool}" "/usr/local/bin/${tool}"
    done
    rm -rf "$work"
    log "installed Node.js ${node_version} (was: ${current_node:-none})"
fi

# --- 5. Python toolchain the jobs ask uv for, plus git trust for the source mount -
runuser -u "$CI_USER" -- env -i HOME="$CI_HOME" PATH="$PATH" uv python install "$PYTHON_VERSION"
if ! git config --system --get-all safe.directory 2>/dev/null | grep -Fxq "$REPO_ROOT"; then
    git config --system --add safe.directory "$REPO_ROOT"
fi

# --- 6. Report -------------------------------------------------------------------
log "Ubuntu:      ${PRETTY_NAME}"
log "LibreOffice: $(dpkg-query -W -f='${Version}' libreoffice-writer) ($(libreoffice --version 2>/dev/null | head -n1))"
log "uv:          $(/usr/local/bin/uv --version)"
log "Node.js:     $(/usr/local/bin/node --version) / npm $(/usr/local/bin/npm --version)"
log "python3:     $(python3 --version)"
log "job user:    ${CI_USER} ($(id -u "$CI_USER")), workspace ${CI_HOME}/aam-ci"
log "done"
