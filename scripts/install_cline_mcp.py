#!/usr/bin/env python3
"""Install Asset-Aware MCP into Cline's MCP settings.

This script updates Cline's `cline_mcp_settings.json` by adding (or updating) a
local STDIO MCP server entry that runs this repository via `uv run`.

It is designed to be:
- Idempotent (safe to run multiple times)
- Conservative (backs up existing settings files before writing)
- Explicit (requires --write to modify files)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import shutil
import sys
from pathlib import Path

DEFAULT_SERVER_NAME = "asset-aware-mcp"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def detect_uv() -> str:
    uv = shutil.which("uv")
    if not uv:
        raise RuntimeError(
            "uv not found on PATH. Install uv first, then retry: https://docs.astral.sh/uv/"
        )
    return uv


def cli_settings_path(cline_root: Path) -> Path:
    """Return the Cline CLI MCP settings path for a config root."""
    return cline_root / "data" / "settings" / "cline_mcp_settings.json"


def dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.expanduser()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(resolved)
    return unique


def candidate_cli_settings_paths(
    home: Path, *, cline_dir: Path | None = None
) -> list[Path]:
    """Return creatable Cline CLI settings paths."""
    custom_roots: list[Path] = []
    if cline_dir is not None:
        custom_roots.append(cline_dir)
    if env_cline_dir := os.environ.get("CLINE_DIR"):
        custom_roots.append(Path(env_cline_dir))

    roots = custom_roots if custom_roots else [home / ".cline"]
    paths = [cli_settings_path(root) for root in roots]
    return dedupe_paths(paths)


def candidate_settings_paths(
    home: Path, *, cline_dir: Path | None = None, include_vscode: bool = True
) -> list[Path]:
    # Cline CLI default and custom config roots.
    paths = candidate_cli_settings_paths(home, cline_dir=cline_dir)
    if not include_vscode:
        return dedupe_paths(paths)

    # VS Code extension globalStorage (common locations)
    # Docs show macOS location:
    # ~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json
    ext_subpath = Path(
        "User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
    )

    system = platform.system().lower()
    if system == "darwin":
        paths.append(home / "Library" / "Application Support" / "Code" / ext_subpath)
    elif system == "windows":
        # Best-effort; Windows paths vary by VS Code channel and roaming/local.
        appdata = os.environ.get("APPDATA")
        if appdata:
            paths.append(Path(appdata) / "Code" / ext_subpath)
    else:
        # Linux + remote server paths
        paths.append(home / ".config" / "Code" / ext_subpath)
        paths.append(home / ".config" / "VSCodium" / ext_subpath)
        paths.append(home / ".vscode-server" / "data" / ext_subpath)
        paths.append(home / ".vscode-server-insiders" / "data" / ext_subpath)

    return dedupe_paths(paths)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{path}: invalid JSON: {exc}") from exc


def backup(path: Path) -> None:
    if not path.exists():
        return
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_suffix(path.suffix + f".bak.{stamp}")
    shutil.copy2(path, backup_path)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_server_config(*, uv: str, root: Path) -> dict:
    # Use --directory so the server loads this repo's .env and relative data paths.
    return {
        "command": uv,
        "args": ["run", "--directory", str(root), "python", "-m", "src.server"],
        "env": {},
        "disabled": False,
    }


def merge_server(settings: dict, *, server_name: str, server_config: dict) -> None:
    servers = settings.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise RuntimeError("Invalid settings: mcpServers must be an object")
    servers[server_name] = server_config


def merge_rules(settings: dict, *, server_name: str) -> None:
    # Optional: suggest a minimal mcpRules category so Cline can auto-pick the server.
    rules = settings.setdefault("mcpRules", {})
    if not isinstance(rules, dict):
        raise RuntimeError("Invalid settings: mcpRules must be an object")

    category = rules.get("assetAwareDocs")
    if not isinstance(category, dict):
        category = {}

    servers = category.get("servers")
    if not isinstance(servers, list):
        servers = []
    if server_name not in servers:
        servers.append(server_name)

    triggers = category.get("triggers")
    if not isinstance(triggers, list):
        triggers = []
    for trig in [
        "asset-aware",
        "asset aware",
        "mcp",
        "docx",
        "dfm",
        "pdf",
        "manifest",
        "table",
        "figure",
        "citation",
        "craap",
        "knowledge graph",
        "lightrag",
        "引用",
        "證據",
        "表格",
        "圖片",
        "章節",
        "知識圖譜",
    ]:
        if trig not in triggers:
            triggers.append(trig)

    category["servers"] = servers
    category["triggers"] = triggers
    category.setdefault(
        "description",
        "Asset-aware document tools (PDF/DOCX, DFM editing, citation-ready spans, LightRAG).",
    )
    rules["assetAwareDocs"] = category


def write_json(path: Path, settings: dict) -> None:
    text = json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--server-name",
        default=DEFAULT_SERVER_NAME,
        help="Server key under mcpServers (default: asset-aware-mcp).",
    )
    parser.add_argument(
        "--path",
        action="append",
        default=[],
        help="Explicit cline_mcp_settings.json path(s) to update (repeatable).",
    )
    parser.add_argument(
        "--cline-dir",
        default=None,
        help="Cline CLI config root; updates <dir>/data/settings/cline_mcp_settings.json.",
    )
    parser.add_argument(
        "--only-cli",
        "--no-vscode",
        action="store_true",
        dest="only_cli",
        help="Only update Cline CLI settings; skip VS Code globalStorage settings files.",
    )
    parser.add_argument(
        "--no-rules",
        action="store_true",
        help="Do not add/update mcpRules for auto-selection triggers.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Actually write changes (default is dry-run).",
    )
    args = parser.parse_args()

    root = repo_root()
    uv = detect_uv()
    server_config = build_server_config(uv=uv, root=root)

    home = Path.home()
    targets = [Path(p).expanduser() for p in args.path] if args.path else []
    explicit_targets = bool(targets)
    cline_dir = Path(args.cline_dir).expanduser() if args.cline_dir else None
    creatable_cli_targets = set(candidate_cli_settings_paths(home, cline_dir=cline_dir))
    if not targets:
        targets = candidate_settings_paths(
            home, cline_dir=cline_dir, include_vscode=not args.only_cli
        )

    updated_any = False
    for path in targets:
        # Create brand-new files for CLI config roots and explicit --path values.
        can_create = explicit_targets or path in creatable_cli_targets
        if not path.exists() and not can_create:
            continue

        settings = load_json(path)
        merge_server(
            settings, server_name=args.server_name, server_config=server_config
        )
        if not args.no_rules:
            merge_rules(settings, server_name=args.server_name)

        updated_any = True
        print(f"[plan] update: {path}")
        print(json.dumps({"mcpServers": {args.server_name: server_config}}, indent=2))

        if args.write:
            ensure_parent(path)
            backup(path)
            write_json(path, settings)
            print(f"[write] ok: {path}")
        else:
            print("[dry-run] no changes written (use --write)")

    if not updated_any:
        print(
            "No Cline settings file found. Re-run with --write to create the CLI settings file at ~/.cline/data/settings/cline_mcp_settings.json",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
