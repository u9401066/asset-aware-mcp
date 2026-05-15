from pathlib import Path

import scripts.install_cline_mcp as install_cline_mcp


def test_candidate_settings_paths_include_vs_code_insiders_on_windows(
    monkeypatch, tmp_path: Path
) -> None:
    appdata = tmp_path / "AppData" / "Roaming"
    home = tmp_path / "home"
    expected_subpath = Path(
        "User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
    )

    monkeypatch.setenv("APPDATA", str(appdata))
    monkeypatch.setattr(install_cline_mcp.platform, "system", lambda: "Windows")

    paths = install_cline_mcp.candidate_settings_paths(home)

    assert appdata / "Code" / expected_subpath in paths
    assert appdata / "Code - Insiders" / expected_subpath in paths


def test_merge_server_preserves_cline_local_metadata(tmp_path: Path) -> None:
    settings = {
        "mcpServers": {
            "asset-aware-mcp": {
                "command": "old-uv",
                "args": ["tool", "run", "asset-aware-mcp"],
                "env": {
                    "DATA_DIR": str(tmp_path / "old-data"),
                    "HTTP_PROXY": "http://proxy.local:8080",
                },
                "alwaysAllow": ["ingest_pdf"],
                "disabled": True,
            }
        }
    }
    server_config = {
        "command": "uv",
        "args": ["run", "--directory", str(tmp_path), "python", "-m", "src.server"],
        "env": {"DATA_DIR": str(tmp_path / "new-data")},
        "disabled": False,
    }

    install_cline_mcp.merge_server(
        settings, server_name="asset-aware-mcp", server_config=server_config
    )

    entry = settings["mcpServers"]["asset-aware-mcp"]
    assert entry["command"] == "uv"
    assert entry["env"]["DATA_DIR"] == str(tmp_path / "new-data")
    assert entry["env"]["HTTP_PROXY"] == "http://proxy.local:8080"
    assert entry["alwaysAllow"] == ["ingest_pdf"]
    assert entry["disabled"] is True


def test_merge_server_preserves_cross_workspace_data_dir_by_default(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace-a"
    other_workspace = tmp_path / "workspace-b"
    settings = {
        "mcpServers": {
            "asset-aware-mcp": {
                "command": "old-uv",
                "args": [
                    "run",
                    "--directory",
                    str(other_workspace),
                    "python",
                    "-m",
                    "src.server",
                ],
                "env": {"DATA_DIR": str(other_workspace / "data")},
            }
        }
    }
    server_config = {
        "command": "uv",
        "args": ["run", "--directory", str(workspace), "python", "-m", "src.server"],
        "env": {"DATA_DIR": str(workspace / "data")},
        "disabled": False,
    }

    merged = install_cline_mcp.merge_server(
        settings,
        server_name="asset-aware-mcp",
        server_config=server_config,
        workspace_root=workspace,
    )

    assert merged is False
    entry = settings["mcpServers"]["asset-aware-mcp"]
    assert entry["env"]["DATA_DIR"] == str(other_workspace / "data")


def test_merge_server_force_workspace_allows_data_dir_takeover(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace-a"
    other_workspace = tmp_path / "workspace-b"
    settings = {
        "mcpServers": {
            "asset-aware-mcp": {
                "command": "old-uv",
                "args": [
                    "run",
                    "--directory",
                    str(other_workspace),
                    "python",
                    "-m",
                    "src.server",
                ],
                "env": {"DATA_DIR": str(other_workspace / "data")},
            }
        }
    }
    server_config = {
        "command": "uv",
        "args": ["run", "--directory", str(workspace), "python", "-m", "src.server"],
        "env": {"DATA_DIR": str(workspace / "data")},
        "disabled": False,
    }

    merged = install_cline_mcp.merge_server(
        settings,
        server_name="asset-aware-mcp",
        server_config=server_config,
        workspace_root=workspace,
        force_workspace=True,
    )

    assert merged is True
    entry = settings["mcpServers"]["asset-aware-mcp"]
    assert entry["env"]["DATA_DIR"] == str(workspace / "data")


def test_merge_server_skips_custom_same_key_server(tmp_path: Path) -> None:
    settings = {
        "mcpServers": {
            "asset-aware-mcp": {
                "command": "custom",
                "args": ["server"],
                "env": {"DATA_DIR": str(tmp_path / "custom-data")},
            }
        }
    }
    server_config = {
        "command": "uv",
        "args": ["run", "--directory", str(tmp_path), "python", "-m", "src.server"],
        "env": {"DATA_DIR": str(tmp_path / "asset-aware-data")},
        "disabled": False,
    }

    merged = install_cline_mcp.merge_server(
        settings, server_name="asset-aware-mcp", server_config=server_config
    )

    assert merged is False
    assert settings["mcpServers"]["asset-aware-mcp"]["command"] == "custom"
    assert settings["mcpServers"]["asset-aware-mcp"]["args"] == ["server"]
    assert settings["mcpServers"]["asset-aware-mcp"]["env"]["DATA_DIR"] == str(
        tmp_path / "custom-data"
    )


def test_build_server_config_sets_workspace_data_dir_from_env(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text('DATA_DIR="custom-data"\n', encoding="utf-8")

    config = install_cline_mcp.build_server_config(uv="uv", root=tmp_path)

    assert config["env"]["DATA_DIR"] == str(tmp_path / "custom-data")
    assert config["env"]["ASSET_AWARE_SUPPRESS_MARKER_OUTPUT"] == "true"
    assert config["env"]["ASSET_AWARE_MARKER_OUTPUT_LOG"] == str(
        tmp_path / "custom-data" / "logs" / "marker.log"
    )


def test_merge_rules_adds_readable_traditional_chinese_triggers() -> None:
    settings: dict = {}

    install_cline_mcp.merge_rules(settings, server_name="asset-aware-mcp")

    triggers = settings["mcpRules"]["assetAwareDocs"]["triggers"]
    for trigger in ["文件", "引用", "表格", "圖表", "知識圖譜", "知識圖", "證據"]:
        assert trigger in triggers
    assert not any("�" in trigger or "?" in trigger for trigger in triggers)
