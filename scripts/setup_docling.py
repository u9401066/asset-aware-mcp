#!/usr/bin/env python3
"""Cross-platform installer for the isolated Docling engine (.venv-docling).

Why this exists
---------------
Docling gives high-fidelity PDF -> asset extraction (semantic figures with
captions, table structure, reading order). It depends on ``torch``, which:
  * has no wheels for pre-release Python (e.g. 3.11.0rc1), and
  * pulls CUDA packages by default even on CPU-only machines.

So Docling is installed into an **isolated** environment (``.venv-docling``)
using a stable Python and a CPU-only torch. The Asset-Aware MCP server (running
on any Python) then calls it through a subprocess bridge — no torch ever enters
the server process.

Zero-brain install (any OS, any agent)
--------------------------------------
    python scripts/setup_docling.py            # install / repair
    python scripts/setup_docling.py --check    # diagnostics only
    python scripts/setup_docling.py --force     # recreate from scratch

Works on Windows, macOS, and Linux. Prefers ``uv`` when available (fast, correct
CPU torch handling) and falls back to stdlib ``venv`` + ``pip`` otherwise.

After a successful install the script prints the interpreter path. The MCP
adapter auto-detects ``./.venv-docling`` with no configuration; you may also set
``DOCLING_PYTHON_PATH`` or the ``docling_python_path`` setting to point elsewhere.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# --- Configuration -----------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VENV = PROJECT_ROOT / ".venv-docling"
PREFERRED_PYTHONS = ("3.12", "3.13", "3.11", "3.10")
CPU_TORCH_INDEX = "https://download.pytorch.org/whl/cpu"
IS_WINDOWS = os.name == "nt"


# --- Pretty output (no color when not a TTY) ---------------------------------


def _supports_color() -> bool:
    return sys.stdout.isatty() and not IS_WINDOWS


_C = {
    "info": "\033[0;34m",
    "ok": "\033[0;32m",
    "warn": "\033[1;33m",
    "err": "\033[0;31m",
    "end": "\033[0m",
}


def _say(level: str, msg: str) -> None:
    tag = {"info": "INFO", "ok": "OK", "warn": "WARN", "err": "ERROR"}[level]
    if _supports_color():
        print(f"{_C[level]}[{tag}]{_C['end']} {msg}")
    else:
        print(f"[{tag}] {msg}")


def info(m: str) -> None:
    _say("info", m)


def ok(m: str) -> None:
    _say("ok", m)


def warn(m: str) -> None:
    _say("warn", m)


def err(m: str) -> None:
    _say("err", m)


# --- Path helpers (cross-platform venv layout) -------------------------------


def venv_python(venv_dir: Path) -> Path:
    """Return the interpreter path inside a venv for the current OS."""
    if IS_WINDOWS:
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(cmd: list[str], *, quiet: bool = False) -> subprocess.CompletedProcess[str]:
    if not quiet:
        info("$ " + " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


# --- Interpreter discovery ---------------------------------------------------


def _uv_path() -> str | None:
    return shutil.which("uv")


def _interpreter_version(python: str) -> tuple[int, int] | None:
    proc = _run(
        [
            python,
            "-c",
            "import sys;print(f'{sys.version_info[0]}.{sys.version_info[1]}')",
        ],
        quiet=True,
    )
    if proc.returncode != 0:
        return None
    try:
        major, minor = proc.stdout.strip().split(".")[:2]
        return int(major), int(minor)
    except (ValueError, IndexError):
        return None


def find_stable_python() -> str | None:
    """Find a stable CPython >= 3.10 that has torch wheels.

    Order: uv-managed 3.12 -> system pythonX.Y -> Windows ``py -3.X`` launcher.
    """
    uv = _uv_path()
    if uv:
        for ver in PREFERRED_PYTHONS:
            proc = _run([uv, "python", "find", ver], quiet=True)
            candidate = proc.stdout.strip()
            if proc.returncode == 0 and candidate and Path(candidate).exists():
                ok(f"Found uv-managed Python {ver}: {candidate}")
                return candidate

    names = []
    for ver in PREFERRED_PYTHONS:
        names.append(f"python{ver}")
    names += ["python3", "python"]
    for name in names:
        found = shutil.which(name)
        if not found:
            continue
        ver = _interpreter_version(found)
        if ver and ver >= (3, 10) and ver[0] == 3:
            ok(f"Found system Python {ver[0]}.{ver[1]}: {found}")
            return found

    if IS_WINDOWS:
        for ver in PREFERRED_PYTHONS:
            proc = _run(["py", f"-{ver}", "-c", "import sys"], quiet=True)
            if proc.returncode == 0:
                launcher = _run(
                    ["py", f"-{ver}", "-c", "import sys;print(sys.executable)"],
                    quiet=True,
                )
                candidate = launcher.stdout.strip()
                if candidate:
                    ok(f"Found Windows py launcher {ver}: {candidate}")
                    return candidate
    return None


# --- Install steps -----------------------------------------------------------


def create_venv(base_python: str, venv_dir: Path, *, use_uv: bool) -> bool:
    if use_uv and _uv_path():
        proc = _run([_uv_path(), "venv", "--python", base_python, str(venv_dir)])
    else:
        proc = _run([base_python, "-m", "venv", str(venv_dir)])
    if proc.returncode != 0:
        err(f"venv creation failed:\n{proc.stderr[:800]}")
        return False
    ok(f"Created isolated environment: {venv_dir}")
    return True


def install_docling(venv_dir: Path, *, use_uv: bool) -> bool:
    py = str(venv_python(venv_dir))
    if use_uv and _uv_path():
        info("Installing docling with CPU torch via uv (--torch-backend cpu)...")
        proc = _run(
            [
                _uv_path(),
                "pip",
                "install",
                "--python",
                py,
                "docling",
                "--torch-backend",
                "cpu",
            ]
        )
        if proc.returncode == 0:
            ok("docling installed (uv, CPU torch)")
            return True
        warn(f"uv install failed, falling back to pip:\n{proc.stderr[:400]}")

    # pip fallback: install CPU torch explicitly, then docling.
    info("Upgrading pip...")
    _run([py, "-m", "pip", "install", "--upgrade", "pip"], quiet=True)
    info("Installing CPU torch from pytorch.org...")
    proc = _run(
        [
            py,
            "-m",
            "pip",
            "install",
            "torch",
            "torchvision",
            "--index-url",
            CPU_TORCH_INDEX,
        ]
    )
    if proc.returncode != 0:
        err(f"CPU torch install failed:\n{proc.stderr[:800]}")
        return False
    info("Installing docling...")
    proc = _run([py, "-m", "pip", "install", "docling"])
    if proc.returncode != 0:
        err(f"docling install failed:\n{proc.stderr[:800]}")
        return False
    ok("docling installed (pip, CPU torch)")
    return True


def verify(venv_dir: Path) -> bool:
    py = venv_python(venv_dir)
    if not py.exists():
        err(f"Interpreter missing: {py}")
        return False
    proc = _run(
        [
            str(py),
            "-c",
            "import docling;from docling.document_converter import DocumentConverter;"
            "print(getattr(docling,'__version__','?'))",
        ],
        quiet=True,
    )
    if proc.returncode != 0:
        err(f"Verification failed:\n{proc.stderr[:600]}")
        return False
    ok(f"Verified: docling {proc.stdout.strip()} importable in {py}")
    return True


# --- Orchestration -----------------------------------------------------------


def check_only(venv_dir: Path) -> int:
    info(f"OS: {platform.system()} ({platform.machine()})")
    info(f"uv available: {'yes' if _uv_path() else 'no'}")
    py = venv_python(venv_dir)
    if py.exists() and verify(venv_dir):
        ok("Docling engine is READY.")
        print(f"\nDOCLING_PYTHON_PATH={py}")
        return 0
    warn("Docling engine NOT installed. Run: python scripts/setup_docling.py")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Install the isolated Docling engine (.venv-docling)."
    )
    parser.add_argument("--check", action="store_true", help="diagnostics only")
    parser.add_argument("--force", action="store_true", help="recreate venv")
    parser.add_argument("--venv", default=str(DEFAULT_VENV), help="target venv path")
    parser.add_argument(
        "--no-uv", action="store_true", help="force stdlib venv + pip path"
    )
    args = parser.parse_args(argv)

    venv_dir = Path(args.venv).resolve()
    use_uv = not args.no_uv

    if args.check:
        return check_only(venv_dir)

    info(f"Target environment: {venv_dir}")

    if venv_python(venv_dir).exists() and not args.force:
        if verify(venv_dir):
            ok("Docling already installed and working — nothing to do.")
            print(f"\nDOCLING_PYTHON_PATH={venv_python(venv_dir)}")
            return 0
        warn("Existing environment is broken; recreating...")
        args.force = True

    if args.force and venv_dir.exists():
        info(f"Removing existing {venv_dir}...")
        shutil.rmtree(venv_dir, ignore_errors=True)

    base_python = find_stable_python()
    if not base_python:
        err(
            "No stable Python (>=3.10) found. Install Python 3.12 from "
            "python.org, or install uv (https://astral.sh/uv), then re-run."
        )
        return 2

    if not create_venv(base_python, venv_dir, use_uv=use_uv):
        return 3
    if not install_docling(venv_dir, use_uv=use_uv):
        return 4
    if not verify(venv_dir):
        return 5

    py = venv_python(venv_dir)
    print()
    ok("Docling engine installed successfully.")
    print("\nNext steps:")
    print("  * The MCP adapter auto-detects ./.venv-docling — no config needed.")
    print("  * To use a custom location, set one of:")
    print(f"      export DOCLING_PYTHON_PATH={py}        # macOS/Linux")
    print(f"      $env:DOCLING_PYTHON_PATH='{py}'        # Windows PowerShell")
    print("  * Select the engine via ETL_ENGINE=docling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
