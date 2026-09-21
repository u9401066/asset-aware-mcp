"""Audit the actual Codex image CRUD trace separately from its self-report."""

import argparse
import json
from pathlib import Path

from tests.codex_native_image.artifacts import (
    check_claimed_review,
    source_and_stages,
    validate_wikis,
)
from tests.codex_native_image.trace import calls_from, inspect_calls
from tests.codex_native_pdf.artifacts import read_json
from tests.codex_pdf.trace import tool_errors


def audit(output, *, save_images=True):
    expected = read_json(output / "expected.json")
    final = read_json(output / "last-message.txt")
    events = [
        json.loads(line) for line in (output / "events.jsonl").read_text().splitlines()
    ]
    calls = calls_from(events)
    workspace = output / "workspace"
    trace = inspect_calls(calls, workspace, output, save_images=save_images)
    target, book, ledger, region = source_and_stages(workspace, expected, final, trace)
    wikis = validate_wikis(workspace, trace, target, book, ledger, region)
    check_claimed_review(final, trace, calls)
    return {
        "passed": True,
        "case": expected["case"]["id"],
        "input": "EXIF-oriented benchmark PNG derived from pinned real PDF page4",
        "tool_calls": len(calls),
        "tool_errors": tool_errors(events),
        "image_revisions": len(target["history"]),
        "complete_frame_records": len(trace["records"]),
        "actual_frame_pngs": len(trace["images"]),
        "region_previews": len(trace["regions"]),
        "wiki_snapshots": wikis,
        "literal_cells": len(trace["cells"]),
        "limitations": final["limitations"],
    }


def write_audit(output):
    try:
        result = audit(output)
    except Exception as exc:
        result = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    attempt = 1
    while (output / f"audit-attempt-{attempt}.json").exists():
        attempt += 1
    (output / f"audit-attempt-{attempt}.json").write_text(text)
    (output / "audit.json").write_text(text)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    result = write_audit(parser.parse_args().output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
