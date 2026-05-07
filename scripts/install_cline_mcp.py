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
            paths.append(Path(appdata) / "Code - Insiders" / ext_subpath)
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
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_suffix(path.suffix + f".bak.{stamp}")
    shutil.copy2(path, backup_path)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def resolve_data_dir(root: Path) -> Path:
    data_dir = "data"
    env_path = root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() != "DATA_DIR":
                continue
            data_dir = value.strip().strip("\"'")
            break

    path = Path(data_dir).expanduser()
    return path if path.is_absolute() else root / path


def build_server_config(*, uv: str, root: Path) -> dict:
    # Use --directory so the server loads this repo's .env and relative data paths.
    data_dir = resolve_data_dir(root)
    return {
        "command": uv,
        "args": ["run", "--directory", str(root), "python", "-m", "src.server"],
        "env": {
            "DATA_DIR": str(data_dir),
            # Marker/surya progress bars can corrupt stdio MCP JSON-RPC transport.
            # Keep raw third-party progress disabled for Cline by default.
            "ASSET_AWARE_SUPPRESS_MARKER_OUTPUT": "true",
            "ASSET_AWARE_MARKER_OUTPUT_LOG": str(data_dir / "logs" / "marker.log"),
        },
        "disabled": False,
    }


def is_asset_aware_launch(entry: dict) -> bool:
    command = str(entry.get("command", ""))
    raw_args = entry.get("args", [])
    args = [str(arg) for arg in raw_args] if isinstance(raw_args, list) else []
    return (
        DEFAULT_SERVER_NAME in command
        or DEFAULT_SERVER_NAME in args
        or "src.server" in args
        or any(f"{DEFAULT_SERVER_NAME}==" in arg for arg in args)
    )


def normalize_for_compare(path_value: str) -> str:
    resolved = str(Path(path_value).expanduser().resolve())
    return resolved.lower() if platform.system().lower() == "windows" else resolved


def is_inside_or_same(parent_path: Path, child_path: Path) -> bool:
    parent = normalize_for_compare(str(parent_path))
    child = normalize_for_compare(str(child_path))
    try:
        Path(child).relative_to(Path(parent))
        return True
    except ValueError:
        return child == parent


def is_cross_workspace_data_dir_change(
    existing: dict,
    next_entry: dict,
    *,
    workspace_root: Path,
) -> bool:
    existing_env = existing.get("env")
    next_env = next_entry.get("env")
    if not isinstance(existing_env, dict) or not isinstance(next_env, dict):
        return False
    existing_data_dir = existing_env.get("DATA_DIR")
    next_data_dir = next_env.get("DATA_DIR")
    if not isinstance(existing_data_dir, str) or not isinstance(next_data_dir, str):
        return False
    if existing_data_dir == next_data_dir:
        return False

    existing_path = Path(existing_data_dir).expanduser()
    next_path = Path(next_data_dir).expanduser()
    if not existing_path.is_absolute() or not next_path.is_absolute():
        return False

    return not is_inside_or_same(workspace_root, existing_path) and is_inside_or_same(
        workspace_root, next_path
    )


def merge_server(
    settings: dict,
    *,
    server_name: str,
    server_config: dict,
    workspace_root: Path | None = None,
    force_workspace: bool = False,
) -> bool:
    servers = settings.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise RuntimeError("Invalid settings: mcpServers must be an object")
    existing = servers.get(server_name)
    if not isinstance(existing, dict):
        servers[server_name] = server_config
        return True
    if not is_asset_aware_launch(existing):
        return False
    if (
        workspace_root is not None
        and not force_workspace
        and is_cross_workspace_data_dir_change(
            existing, server_config, workspace_root=workspace_root
        )
    ):
        return False

    merged = {**existing, **server_config}
    existing_env = existing.get("env")
    next_env = server_config.get("env")
    if isinstance(existing_env, dict) or isinstance(next_env, dict):
        merged["env"] = {
            **(existing_env if isinstance(existing_env, dict) else {}),
            **(next_env if isinstance(next_env, dict) else {}),
        }
    if "alwaysAllow" in existing:
        merged["alwaysAllow"] = existing["alwaysAllow"]
    if "disabled" in existing:
        merged["disabled"] = existing["disabled"]

    servers[server_name] = merged
    return True


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
        "文件",
        "文件證據",
        "引用",
        "引用來源",
        "證據",
        "表格",
        "圖表",
        "圖片",
        "章節",
        "知識圖譜",
        "段落定位",
        "證據定位",
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
        "--force-workspace",
        action="store_true",
        help=(
            "Allow this workspace to take over an existing managed Cline server "
            "whose DATA_DIR points outside the current repository."
        ),
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
    saw_target = False
    for path in targets:
        # Create brand-new files for CLI config roots and explicit --path values.
        can_create = explicit_targets or path in creatable_cli_targets
        if not path.exists() and not can_create:
            continue
        saw_target = True

        settings = load_json(path)
        merged = merge_server(
            settings,
            server_name=args.server_name,
            server_config=server_config,
            workspace_root=root,
            force_workspace=args.force_workspace,
        )
        if not merged:
            print(
                f"[skip] custom same-key server preserved: {path} ({args.server_name})"
            )
            continue
        if not args.no_rules:
            merge_rules(settings, server_name=args.server_name)

        updated_any = True
        print(f"[plan] update: {path}")
        print(
            json.dumps(
                {
                    "mcpServers": {
                        args.server_name: settings["mcpServers"][args.server_name]
                    }
                },
                indent=2,
            )
        )

        if args.write:
            ensure_parent(path)
            backup(path)
            write_json(path, settings)
            print(f"[write] ok: {path}")
        else:
            print("[dry-run] no changes written (use --write)")

    if not updated_any and not saw_target:
        print(
            "No Cline settings file found. Re-run with --write to create the CLI settings file at ~/.cline/data/settings/cline_mcp_settings.json",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
