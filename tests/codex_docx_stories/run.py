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
from tests.native_docx_stories_helpers import story_document


def prompt(workspace):
    return f"""Use ONLY the asset_aware_under_test document native MCP tools. The human
supplied {workspace / "source.docx"}, a three-page document with two sections,
a distinct first-page header and a shared default header/footer. Correct it in
native form without replacing runs/styles or writing back the source.

1. Discover the native contract and complete per-operation schemas. Respect the
   reported pagination limits. Register source.docx. Read the COMPLETE
   read_docx_stories catalog and EVERY story's full read_docx_story record through
   all next_text_offset pages at one text_sha256. Do not infer roles from filenames.
2. Render ALL initial render_docx_page PNGs, with explicit docx_page_index and
   revision. Explain which pages use the shared header/footer and the first-page
   exception. Export initial Wiki to {workspace / "native-wiki"}.
3. In the shared default header, change only SOURCE to VERIFIED in the existing
   long text node. Keep all remaining text through END-HEADER and KEEP-ITALIC.
   In ONE update_docx_story batch, insert a paragraph at direct child index3 with
   one run text 'REVIEWED 1,234.50', font_name Arial and font_size_pt9; then delete
   the old 'REMOVE THIS PARAGRAPH' direct block at index2, count1. Use its complete
   current reference and explicit shared_scope all_sections_using_part. Do not
   change the first-page header, table contents or any existing formatting.
4. Read the COMPLETE returned review_request, including its operation_result.
   At that NEW revision read the COMPLETE shared default footer. Change only its
   literal 'Page ' text node to 'Verified page '. Preserve the PAGE field and its
   cached native value; do not edit the field result. Use its full current reference.
5. Read the complete final catalog and ALL final story records/operation receipts.
   Render ALL final actual Word PNGs. Review shared-header changes on pages2/3,
   unchanged first-page header and blank first-page footer, rich text/table contents,
   the new paragraph, and dynamically rendered page numbers2/3. Microsoft Word
   has not been tested; distinguish literal field caches from rendered results.
6. Verify an original story reference as valid historical evidence and re-read its
   complete original record. Read a JSON selection from that original story's /text
   and verify the selection too. Publish to {workspace / "verified.docx"}. Export
   final Wiki to {workspace / "native-wiki"}; inspect history. Keep all source bytes.
7. Finish ONLY JSON: docx_asset_id, limitations(nonempty list), visual_review
   {{scope:'static_libreoffice_document_page_preview',word_checked:false,
   reviewed_pages:[{{revision,page_index}}],findings:[specific observed details]}}.

An independent auditor checks source bytes/mtime, complete native reads and receipts,
actual tool order and all images, preserved XML/parts, immutable references and
both complete Wiki snapshots. Use installed tools and retain errors transparently.
Do not access fixture/expected-answer files or use shell commands.
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
    source.write_bytes(story_document())
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
    from tests.codex_docx_stories.audit import write_audit

    result = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": result["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
