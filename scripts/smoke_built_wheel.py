#!/usr/bin/env python3
"""Install the built wheel into a clean venv and smoke the console runtime."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(
    command: list[str], *, env: dict[str, str] | None = None, timeout: int = 180
) -> None:
    print("+ " + " ".join(command))
    subprocess.run(command, cwd=ROOT, env=env, check=True, timeout=timeout)


def find_wheel(explicit: str | None) -> Path:
    if explicit:
        wheel = Path(explicit).expanduser().resolve()
        if not wheel.exists():
            raise FileNotFoundError(f"Wheel not found: {wheel}")
        return wheel

    wheels = sorted((ROOT / "dist").glob("asset_aware_mcp-*-py3-none-any.whl"))
    if not wheels:
        raise FileNotFoundError("No built asset_aware_mcp wheel found under dist/")
    if len(wheels) > 1:
        print(f"Multiple wheels found; using newest by name: {wheels[-1]}")
    return wheels[-1]


def venv_path(venv_dir: Path, executable: str) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / f"{executable}.exe"
    return venv_dir / "bin" / executable


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install dist/*.whl into a clean venv and run runtime smoke checks."
    )
    parser.add_argument(
        "--wheel", help="Wheel path. Defaults to dist/asset_aware_mcp-*.whl"
    )
    parser.add_argument(
        "--keep-venv",
        action="store_true",
        help="Keep the temporary venv for debugging.",
    )
    args = parser.parse_args()

    wheel = find_wheel(args.wheel)
    temp_root = Path(tempfile.mkdtemp(prefix="asset-aware-wheel-smoke-"))
    venv_dir = temp_root / "venv"
    try:
        run([sys.executable, "-m", "venv", str(venv_dir)])
        python = venv_path(venv_dir, "python")
        asset_aware = venv_path(venv_dir, "asset-aware-mcp")

        run([str(python), "-m", "pip", "install", "--upgrade", "pip"], timeout=240)
        run([str(python), "-m", "pip", "install", str(wheel)], timeout=600)
        run([str(asset_aware), "--help"], timeout=60)
        run([str(asset_aware), "doctor", "--json"], timeout=120)
        run([str(asset_aware), "list-tools", "--json"], timeout=120)

        smoke_env = {
            **os.environ,
            "DATA_DIR": str(temp_root / "data"),
            "ENABLE_LIGHTRAG": "false",
            "PYTHONIOENCODING": "utf-8",
        }
        run(
            [
                str(python),
                str(ROOT / "scripts" / "smoke_mcp_stdio.py"),
                "--",
                str(asset_aware),
            ],
            env=smoke_env,
            timeout=120,
        )
    finally:
        if args.keep_venv:
            print(f"Kept smoke venv at {venv_dir}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)

    print(f"Built wheel runtime smoke OK: {wheel.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
