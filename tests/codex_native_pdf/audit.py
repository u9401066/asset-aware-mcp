"""Audit an opt-in native-PDF Codex run without trusting its success claims."""

from __future__ import annotations

import argparse
import json

from tests.codex_native_pdf.artifacts import (
    load_asset,
    read_json,
    validate_history,
    validate_pdf,
    validate_source,
    validate_transcription,
    validate_wiki,
)
from tests.codex_native_pdf.trace import (
    complete_records,
    completed_calls,
    validate_images,
    validate_reference_use,
)
from tests.codex_pdf.trace import tool_errors


def audit(output):
    expected = read_json(output / "expected.json")
    final = read_json(output / "last-message.txt")
    events = [json.loads(s) for s in (output / "events.jsonl").read_text().splitlines()]
    workspace = output / "workspace"
    calls = completed_calls(events)
    source = load_asset(workspace, final["source_asset_id"])
    target = load_asset(workspace, final["result_asset_id"])
    records = complete_records(calls)
    checks = {}
    for name, check in (
        (
            "source_unchanged_image_only",
            lambda: validate_source(workspace, expected, source),
        ),
        (
            "actual_mcp_images",
            lambda: validate_images(calls, source, target, workspace),
        ),
        (
            "full_page_reference_readbacks",
            lambda: validate_reference_use(calls, records, source, target),
        ),
        (
            "revision_history_and_copy_lineage",
            lambda: validate_history(source, target, records),
        ),
        (
            "independent_final_pdf_pixels",
            lambda: validate_pdf(workspace, target, final),
        ),
        ("immutable_wiki_artifacts", lambda: validate_wiki(workspace, target, final)),
        (
            "exact_visual_transcription",
            lambda: validate_transcription(
                final["transcription"], expected["expected_rows"]
            ),
        ),
    ):
        checks[name] = run_check(check)
    return {
        "passed": all(c["passed"] for c in checks.values()),
        "checks": checks,
        "mcp_calls": len(calls),
        "complete_page_records": len(records),
        "tool_errors": tool_errors(events),
        "scope": "One synthetic scanned PDF; fixed-renderer pixels do not prove universal visual or semantic accuracy",
    }


def run_check(check):
    try:
        return {"passed": True, "detail": check()}
    except Exception as exc:
        return {"passed": False, "error": str(exc)}


def write_audit(output):
    try:
        report = audit(output)
    except Exception as exc:
        report = {"passed": False, "error": str(exc)}
    (output / "audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    report = write_audit(parser.parse_args().output.resolve())
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["passed"] else 1)
