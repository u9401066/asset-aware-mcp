"""CLI diagnostics regression tests."""

from __future__ import annotations

import json

from src import server


def test_help_prints_cli_usage_without_starting_stdio_server(
    monkeypatch,
    capsys,
) -> None:
    """`asset-aware-mcp --help` must not enter the stdio MCP server."""

    def fail_if_server_starts() -> None:
        raise AssertionError("stdio server should not start for --help")

    monkeypatch.setattr(
        server, "run_stdio_server", fail_if_server_starts, raising=False
    )

    assert server.main(["--help"]) == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out
    assert "doctor" in captured.out
    assert "list-tools" in captured.out
    assert "Starting Asset-Aware MCP server" not in captured.err


def test_no_args_starts_stdio_server(monkeypatch) -> None:
    import src.server as server

    calls: list[str] = []
    monkeypatch.setattr(server, "run_stdio_server", lambda: calls.append("serve"))

    assert server.main([]) == 0
    assert calls == ["serve"]


def test_doctor_outputs_runtime_status_json(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ENABLE_LIGHTRAG", "false")

    assert server.main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["package"]["name"] == "asset-aware-mcp"
    assert "version" in payload["package"]
    assert payload["runtime"]["python"]
    assert payload["backends"]["pymupdf"]["available"] is True
    assert isinstance(payload["backends"]["marker"]["available"], bool)
    assert payload["paths"]["data_dir"]["path"] == str(tmp_path / "data")
    assert payload["features"]["lightrag"]["enabled"] is False


def test_doctor_uses_safe_granite_defaults_when_kg_not_configured(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_EMBEDDING_MODEL", raising=False)
    monkeypatch.delenv("ENABLE_LIGHTRAG", raising=False)

    assert server.main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["features"]["ollama"]["model"] == "granite4.1"
    assert payload["features"]["ollama"]["embedding_model"] == "nomic-embed-text"
    assert payload["features"]["lightrag"]["enabled"] is False


def test_health_outputs_human_readable_runtime_status(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("ENABLE_LIGHTRAG", "false")

    assert server.main(["health"]) == 0

    output = capsys.readouterr().out
    assert "Asset-Aware MCP" in output
    assert "PyMuPDF:" in output
    assert "Marker:" in output
    assert "DATA_DIR:" in output
    assert "LightRAG:" in output
    assert "LLM model:" in output


def test_list_tools_reflects_registered_core_tools(capsys) -> None:
    assert server.main(["list-tools"]) == 0

    output = capsys.readouterr().out
    assert "ingest_documents" in output
    assert "list_documents" in output
    assert "get_job_status" in output
