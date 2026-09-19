"""Run the user's default Codex model against only the current native MCP tool."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from tests.codex_docx_structure.fonts import environment, snapshot
from tests.codex_pdf.fixtures import sha256
from tests.codex_pdf.run import command, execute
from tests.native_docx_layout_helpers import clipped_document


def prompt(workspace):
    return f"""Use ONLY the asset_aware_under_test document native MCP tools. The human
supplied {workspace / "source.docx"}, whose table contains clipped text and does
not repeat its two title/header rows. Correct the existing native document.
Do not reconstruct it from Markdown, replace content or writeback the source.

1. Discover the native contract and actual schemas, following every schema_request
   page at one hash. Use contract.for_op only for native operation names, and use
   text_limit only with operations that accept it. Register source.docx.
2. Read COMPLETE DFM/block listings with pinned read_docx. Obtain the full table
   evidence, then read_docx_table through EVERY next_text_offset at one text_sha256.
   Inspect row layout and native XML. Keep the initial full reference and revision.
3. Render ALL initial render_docx_page PNGs (explicit docx_page_index; follow
   next_page_index). Note which row lines are visible and which are clipped.
   Export the initial Wiki to {workspace / "native-wiki"}.
4. Correct the table in ONE update_docx_table_grid batch with the current full
   reference and expected_revision: set_header_rows count2; set_row_layout index2
   count14, height.rule auto, split prevent. Keep every native cell/run/style intact.
   Read COMPLETE returned review_request and COMPLETE new read_docx DFM/blocks.
5. Render ALL corrected actual Word page PNGs. Check all14 rows, including every
   END and CONFIRMED line, numeric spelling, and both repeated headers on every
   page. Explain the observed pagination change. Never claim Microsoft Word tested.
6. Verify the original table reference as valid historical evidence. Re-read the
   complete original table record, confirming the source layout remains available.
   Publish the corrected DOCX to {workspace / "verified.docx"}, export final Wiki
   to {workspace / "native-wiki"}, inspect history. Source bytes must stay untouched.
7. Finish ONLY JSON: docx_asset_id, limitations (nonempty list), visual_review
   {{scope:'static_libreoffice_document_page_preview',word_checked:false,
   reviewed_pages:[{{revision,page_index}}],findings:[specific before/after observations]}}.

An independent auditor checks actual tool order, complete receipts, source bytes
and mtime, native cells/styles, repeated headers, row contents on each page, every
actual image and both complete historical Wiki snapshots. Use installed tools,
recover transparently from errors, and do not access fixture/expected-answer files.
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--font-fixture", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    workspace.mkdir()
    source = workspace / "source.docx"
    source.write_bytes(clipped_document())
    repo = Path(__file__).resolve().parents[2]
    fonts = snapshot(args.font_fixture)
    metadata = {
        "source_sha256": sha256(source),
        "source_mtime_ns": source.stat().st_mtime_ns,
        "server_source_sha256": hashlib.sha256(
            "\n".join(
                f"{p.relative_to(repo)}:{sha256(p)}"
                for p in sorted((repo / "src").rglob("*.py"))
            ).encode()
        ).hexdigest(),
        "lock_sha256": sha256(repo / "uv.lock"),
        "codex_version": subprocess.check_output(
            [args.codex, "--version"], text=True
        ).strip(),
        "model_selection": "Codex default; not pinned by runner",
        "font_environment": fonts,
    }
    (output / "expected.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    text = prompt(workspace)
    (output / "prompt.txt").write_text(text, encoding="utf-8")
    cli = command(args.codex, repo, workspace, output)
    cli[-1:-1] = [
        "-c",
        'mcp_servers.asset_aware_under_test.enabled_tools=["document"]',
        "-c",
        "mcp_servers.asset_aware_under_test.env.FONTCONFIG_FILE="
        + json.dumps(str(Path(fonts["root"]) / "with-cjk.conf")),
    ]
    if binary := os.environ.get("LIBREOFFICE_BIN"):
        cli[-1:-1] = [
            "-c",
            "mcp_servers.asset_aware_under_test.env.LIBREOFFICE_BIN="
            + json.dumps(binary),
        ]
    with environment(fonts):
        status = execute(cli, text, output, 900)
    from tests.codex_docx_layout.audit import write_audit

    result = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": result["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
