"""Run the user's default Codex model against only the current native MCP tool."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

from tests.codex_docx_structure.fonts import environment, snapshot
from tests.codex_docx_structure.run import prompt as create_prompt
from tests.codex_pdf.fixtures import build_pdf, sha256
from tests.codex_pdf.run import command, execute


def prompt(workspace):
    return (
        create_prompt(workspace).split("3. At EVERY revision")[0]
        + f"""3. At EVERY revision, read complete DFM and all block listings via read_docx.
   Obtain the complete current table evidence. Use read_docx_table with asset_id,
   revision and docx_table_reference, following EVERY next_text_offset until null
   at one text_sha256. Inspect actual rows/columns/merges/native XML. Retain the
   initial table reference. Discover each operation's actual installed schema;
   contract.for_op only accepts native operation names. Follow schema_request
   if schema_delivery is paged. Use text_limit only with schema/read operations.
4. Use update_docx_table_grid with the full current reference and ONE batch:
   a. Insert row at index 4, minimum height 360 twips, five cells: literal
      'Temporary 007', 'Keep paragraphs', then three defaults. Both nonempty
      cells have one 11.5-point Arial run. Indexes are zero-based.
   b. Insert column at index 5, width 600 twips, default empty cells.
   c. Merge title row 0 columns 0..5 with content_policy require_empty.
   d. Resize new row 4 to 450 twips; resize new column 5 to 800 twips.
   e. Merge row 4 columns 0..1 with append_blocks, then split that anchor.
   f. Delete new column 5 and new row 4, one each.
   g. Resize surviving column 1 to 1700 and column 3 to 1300 twips.
   Read the COMPLETE returned review_request table and complete read_docx DFM.
   View ALL actual render_docx_page PNGs for this intermediate revision (explicit
   docx_page_index, follow next_page_index). Check exact text and page layout.
5. In a second update_docx_table_grid, restore all five widths to 1500 twips
   using one resize at column index 0. Read complete table and DFM again. View
   ALL final Word PNG pages. Verify initial table reference and source PDF page
   reference; historical references must remain usable and must not migrate.
6. Publish final DOCX to {workspace / "verified.docx"}; export_wiki to
   {workspace / "native-wiki"}; inspect history. Never writeback the source PDF.
7. Finish ONLY JSON: source_asset_id, docx_asset_id, limitations (nonempty list),
   visual_review {{scope:'static_libreoffice_document_page_preview',
   word_checked:false, reviewed_pages:[{{revision,page_index}}], findings:[concrete
   observations]}}. Distinguish reviewed Writer previews from Microsoft Word.

An independent auditor checks every image, full grid reads before edits, native
XML, exact scanned strings and rich formats, operation history, old evidence,
published bytes and Wiki attachments. Do not read fixture/expected-answer files.
Complete the actual tools; preserve and recover from errors without hiding them.
"""
    )


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
    source = workspace / "source.pdf"
    build_pdf(source, "scanned")
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
    from tests.codex_docx_grid.audit import write_audit

    result = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": result["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
