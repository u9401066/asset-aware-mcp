"""The live-evaluation auditor must reject plausible but incomplete evidence."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pymupdf as fitz
import pytest

from tests.codex_pdf.audit import (
    first_transcription_exact,
    validate_bundle,
    validate_citations,
    validate_history,
    validate_images,
    validate_rows,
    write_audit,
)
from tests.codex_pdf.fixtures import build_pdf, expected_rows, sha256
from tests.codex_pdf.run import command
from tests.codex_pdf.trace import call_failed, completed_calls, tool_errors


@pytest.mark.parametrize(
    "mode,text_pages", [("digital", [0, 1, 2]), ("scanned", []), ("mixed", [0])]
)
def test_corpus_has_true_image_only_pages(
    tmp_path: Path, mode: str, text_pages: list[int]
) -> None:
    source = tmp_path / "fixture.pdf"
    build_pdf(source, mode)
    with fitz.open(source) as document:
        assert [
            i for i, page in enumerate(document) if page.get_text().strip()
        ] == text_pages
        assert document[2].rotation == 90
        assert document[2].cropbox == fitz.Rect(20, 30, 592, 762)


@pytest.mark.parametrize(
    "row,column,value",
    [
        (0, "Count", "7"),
        (0, "Reading", "0.50"),
        (1, "Reading", "1234.50"),
        (2, "Unit", "μg/mL"),
        (3, "Reading", "12.5"),
        (4, "Reading", "0.01"),
        (5, "Reading", ""),
        (6, "Reading", 2),
    ],
)
def test_auditor_rejects_lossy_transcription(
    row: int, column: str, value: object
) -> None:
    changed = copy.deepcopy(expected_rows())
    changed[row][column] = value
    with pytest.raises(ValueError, match="independent source truth"):
        validate_rows(changed, expected_rows())


@pytest.mark.parametrize("change", ["missing", "duplicate"])
def test_auditor_rejects_missing_or_duplicate_rows(change: str) -> None:
    rows = expected_rows()
    changed = rows[:-1] if change == "missing" else [*rows, rows[0]]
    with pytest.raises(ValueError, match="independent source truth"):
        validate_rows(changed, rows)


def test_agent_success_prose_is_not_tool_evidence() -> None:
    events = [
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "All checks passed."},
        },
        {"type": "turn.completed"},
    ]
    with pytest.raises(ValueError, match="No completed MCP calls"):
        completed_calls(events)


@pytest.mark.parametrize("kind", ["command_execution", "file_change", "web_search"])
def test_non_mcp_bypass_is_rejected(kind: str) -> None:
    events = [
        {"type": "item.completed", "item": {"type": kind}},
        {"type": "turn.completed"},
    ]
    with pytest.raises(ValueError, match="Unexpected non-MCP action"):
        completed_calls(events)


@pytest.mark.parametrize(
    "message",
    [
        "❌ Missing required input",
        '{"success": false, "error": "bad path"}',
        '{"status": "error"}',
    ],
)
def test_application_errors_remain_visible_even_with_completed_transport(
    message: str,
) -> None:
    item = {
        "type": "mcp_tool_call",
        "status": "completed",
        "tool": "document",
        "arguments": {"op": "export_assets"},
        "result": {"content": [{"type": "text", "text": message}]},
    }
    assert call_failed(item)
    assert (
        tool_errors([{"type": "item.completed", "item": item}])[0]["error"] == message
    )


@pytest.mark.parametrize("mode", ["mixed", "scanned"])
def test_image_omission_is_not_visual_inspection(mode: str) -> None:
    call = {
        "tool": "document_asset",
        "arguments": {"asset_type": "figure"},
        "result": {
            "content": [{"type": "text", "text": "Image omitted: retry smaller size"}]
        },
    }
    with pytest.raises(ValueError, match="Missing actual image responses"):
        validate_images([call], {"assets": {"figures": []}}, mode)


def _citation_inputs() -> tuple[dict, dict]:
    ref = {
        "source_type": "figure",
        "asset_id": "fig_2_1",
        "doc_id": "doc_test",
        "page": 2,
    }
    table = {
        "rows": [{"Sample": "B201"}],
        "row_ids": ["row_1"],
        "citations": {"rid:row_1:Reading": {"refs": [ref]}},
    }
    manifest = {
        "doc_id": "doc_test",
        "assets": {"tables": [], "figures": [{"id": "fig_2_1", "page": 2}]},
    }
    return table, manifest


@pytest.mark.parametrize(
    "field,value",
    [
        ("doc_id", "doc_other"),
        ("asset_id", "fig_missing"),
        ("page", 3),
        ("span_id", "invented_span"),
        ("quote", "Invented OCR quote"),
        ("line_range", [1, 2]),
    ],
)
def test_citation_audit_rejects_wrong_or_invented_visual_evidence(
    field: str, value: object
) -> None:
    table, manifest = _citation_inputs()
    validate_citations(table, manifest)
    table["citations"]["rid:row_1:Reading"]["refs"][0][field] = value
    with pytest.raises(ValueError):
        validate_citations(table, manifest)


def test_bundle_tampering_is_detected(tmp_path: Path) -> None:
    artifact = tmp_path / "note.md"
    artifact.write_text("source", encoding="utf-8")
    manifest = {
        "source_identity": {"source_sha256": "expected"},
        "artifacts": [
            {
                "path": "note.md",
                "size_bytes": artifact.stat().st_size,
                "sha256": sha256(artifact),
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    artifact.write_text("edited", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_bundle(tmp_path, "expected")


def test_runner_limits_configuration_to_synthetic_mcp_server(tmp_path: Path) -> None:
    args = command("codex", tmp_path / "repo", tmp_path / "workspace", tmp_path)
    assert "--ignore-user-config" in args and "--ephemeral" in args
    config = dict(
        args[i + 1].split("=", 1) for i, value in enumerate(args) if value == "-c"
    )
    assert json.loads(config["features.shell_tool"]) is False
    assert json.loads(config["features.multi_agent"]) is False
    assert json.loads(config["mcp_servers.asset_aware_under_test.required"]) is True
    assert json.loads(config["mcp_servers.asset_aware_under_test.env.DATA_DIR"]) == str(
        tmp_path / "workspace/data"
    )
    assert not any("CODEX_HOME" in item or "api_key" in item for item in args)


def test_successful_cli_exit_without_artifacts_is_not_a_pass(tmp_path: Path) -> None:
    (tmp_path / "run.json").write_text(
        '{"returncode": 0, "timed_out": false}', encoding="utf-8"
    )
    report = write_audit(tmp_path)
    assert report["passed"] is False
    assert json.loads((tmp_path / "audit.json").read_text())["passed"] is False


def test_initial_transcription_metric_preserves_errors_corrected_later() -> None:
    rows = expected_rows()
    calls = [
        {
            "tool": "table_data",
            "arguments": {
                "operation": "add_rows",
                "table_id": "tbl_1",
                "rows": rows[:3],
            },
        },
        {
            "tool": "table_data",
            "arguments": {
                "operation": "add_rows",
                "table_id": "tbl_1",
                "rows": rows[3:],
            },
        },
    ]
    assert first_transcription_exact(calls, "tbl_1", expected_rows())
    rows[0]["Count"] = "7"
    calls.append(
        {
            "tool": "table_data",
            "arguments": {
                "operation": "update_cell",
                "table_id": "tbl_1",
                "value": "007",
            },
        }
    )
    assert not first_transcription_exact(calls, "tbl_1", expected_rows())


@pytest.mark.parametrize("wrong_target", [False, True])
def test_crud_audit_allows_agent_corrections_but_requires_the_requested_target(
    wrong_target: bool,
) -> None:
    target = "rid:wrong/col:Reading" if wrong_target else "rid:row_b/col:Reading"
    table = {
        "rows": [{"Sample": "B202"}],
        "row_ids": ["row_b"],
        "change_log": {
            "entries": [
                {
                    "operation": "update_cell",
                    "target": "rid:row_a/col:Count",
                    "old_value": "7",
                    "new_value": "007",
                },
                {
                    "operation": "update_cell",
                    "target": target,
                    "old_value": "12.5%",
                    "new_value": "13.0%",
                },
                {
                    "operation": "update_cell",
                    "target": target,
                    "old_value": "13.0%",
                    "new_value": "12.5%",
                },
                {"operation": "delete_row", "old_value": {"Sample": "A101"}},
            ]
        },
    }
    calls = [
        {
            "tool": "table_data",
            "arguments": {"operation": "get_cell"},
            "result": {"content": [{"text": "13.0%"}]},
        },
        {
            "tool": "table_data",
            "arguments": {"operation": "query_rows"},
            "result": {"content": [{"text": "**Rows:** 6"}]},
        },
    ]
    if wrong_target:
        with pytest.raises(ValueError, match="B202 Reading"):
            validate_history(table, calls)
    else:
        validate_history(table, calls)
