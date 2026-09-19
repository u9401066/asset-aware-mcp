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
from tests.native_docx_story_lifecycle_helpers import source_document


def prompt(workspace):
    return f"""Use ONLY asset_aware_under_test document native MCP tools. The human
supplied {workspace / "source.docx"}, a four-page Word document with sections A/B/C.
Only section B should receive an independent corrected header/footer. Keep sections
A and C visually unchanged, including the first-page exception and native PAGE fields.
Never write back the source. Use the Codex default model and installed contracts.

1. Discover contract and complete per-operation schemas. When contract_delivery is
   paged, read ALL contract_request pages at one contract_sha256. Observe the4000
   text_limit maximum; schema_request is separate. Register source.docx. Read the
   complete read_docx_story_structure and EVERY initial read_docx_story record.
   Inspect full XML, text-node paths, part hashes and section bindings; do not guess
   roles from filenames. Render ALL FOUR actual initial Word page PNGs with render_size1024. Export the
   initial Wiki to {workspace / "native-wiki"}.
2. In ONE update_docx_story_structure batch at the exact revision/catalog hash and
   explicit sections_and_following_inheritors scope:
   - Clone the shared default header to word/section-b/header.xml, with its full
     source_part_sha256. Preserve rich text, table contents and original parts.
   - Create word/section-b/footer.xml of kind footer with one paragraph and one
     run text 'Section B verified / 007 µg', font_name Arial, font_size_pt9.
   - Bind section_index1 default header/footer to those new parts.
   - Explicitly bind section_index2 default header/footer to their ORIGINAL shared
     parts so section C does not inherit the new section B definitions.
   - Delete the unbound word/obsolete-header.xml using its exact current part hash.
   These are seven sequential edits. Preserve all first/even-page options and fields.
3. Read the COMPLETE returned structure review_request including its full receipt.
   At the new revision, read the COMPLETE word/section-b/header.xml record. Use
   update_docx_story with its full reference and all_sections_using_part scope to
   change only the initial SOURCE token to SECTION B VERIFIED in its long text node.
   Keep all following text, runs, table values and formatting unchanged.
4. Read that COMPLETE review_request and complete final structure/ALL story records.
   Render ALL FOUR final PNGs with the same render_size1024. Confirm only page3 changes: section B has the corrected
   header and new footer. Pages1/2/4 retain their original appearance; the original
   footer fields still calculate page numbers2/4. No Microsoft Word fidelity claim.
5. Verify the DELETED obsolete story's original full reference as valid historical
   evidence; re-read its complete original record. Select its /text using
   read_selection and verify the selection. Publish {workspace / "verified.docx"},
   export final Wiki to {workspace / "native-wiki"}, and inspect history.
6. Finish ONLY JSON: docx_asset_id, limitations(nonempty list), visual_review
   {{scope:'static_libreoffice_document_page_preview',word_checked:false,
   reviewed_pages:[{{revision,page_index}}],findings:[specific observed details]}}.

Independent audit checks source bytes/mtime, all native parts/bindings, complete
reads/receipts, actual tool order and eight actual images, old deleted references,
unchanged pages and both complete immutable Wikis. No shell or fixture access.
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
    source.write_bytes(source_document())
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
    from tests.codex_story_lifecycle.audit import write_audit

    result = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": result["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
