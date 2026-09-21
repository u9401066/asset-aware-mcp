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
from tests.native_docx_notes_helpers import source_document


def prompt(workspace, repair_note_ids=False):
    text = f"""Use ONLY asset_aware_under_test document native MCP tools. The human
supplied {workspace / "source.docx"}, a Word file containing two body pages and one
endnote page. Use the Codex default model and installed contracts; never write back
source.docx. Native note IDs are not the rendered numbering.

1. Discover complete contract policies and per-operation schemas. If delivery is
paged, assemble ALL contract_request and schema_request pages at their respective
hashes. text_limit maximum4000. Register source.docx. Read COMPLETE read_docx_notes
and EVERY initial read_docx_note record, including special separator definitions.
Read full locators, text paths, hashes and body references; do not guess filenames.
Render ALL THREE initial actual Word page PNGs with render_size1024. Export initial
Wiki to {workspace / "native-wiki"}.
2. In ONE update_docx_notes batch with exact expected_revision/catalog hash and
explicit definitions_and_native_body_references scope, perform these three edits:
 - Create footnote native ID11 in the existing footnote part. Anchor at Unicode
   offset10 in w:t 'Source 007 µg and preserved run.' using its complete main-XML
   text_path and exact expected_text_sha256. One paragraph/run text
   'NEW FOOTNOTE 007 µg', font_name Arial, font_size_pt9.
 - Create endnote native ID12 in the existing endnote part. Anchor at the END of
   w:t 'Second value -0.50 mg/L.' (the full Unicode text length), exact path/hash.
   One paragraph/run text 'NEW ENDNOTE -0.50 mg/L', font_name Arial, font_size_pt9.
 - Delete original footnote native ID8 using its full locator and exact
   expected_note_sha256, with literal_body_text:'preserve'.
Keep all original text/styles/other note IDs and special definitions intact.
3. Read the COMPLETE returned review_request and full receipt. Read the COMPLETE
current footnote ID2. With its whole reference, update_docx_note and scope
all_native_references, change ONLY w:t ' FOOTNOTE 007 µg -0.50 mg/L' to
' VERIFIED FOOTNOTE 007 µg -0.50 mg/L'. Preserve its other paragraph and formatting.
Read its COMPLETE review_request, the final catalog and EVERY final note record.
4. Render ALL THREE final actual PNGs at render_size1024. Check body text, units,
marks, note contents and bindings: page1's NEW FOOTNOTE is displayed1 and VERIFIED
FOOTNOTE is displayed2; page3's NEW ENDNOTE is displayedi and original ENDNOTE is
displayedii. IDs11/12 stay native identities. The removed old note is absent.
5. Verify DELETED footnote ID8's original full reference and re-read its COMPLETE
original record. Select its /text and verify the selection. Publish
{workspace / "verified.docx"}; export final Wiki to {workspace / "native-wiki"}.
Inspect history. Keep both immutable Wikis and all source bytes intact.
6. Finish ONLY JSON: docx_asset_id, limitations(nonempty list), visual_review
{{scope:'static_libreoffice_document_page_preview',word_checked:false,
reviewed_pages:[{{revision,page_index}}],findings:[specific observed details]}}.

The independent auditor checks actual tool order, complete records/receipts, native
IDs and formatting, all six actual PNGs, immutable old evidence and both Wikis.
No shell or fixture access. Do not claim that checking native bytes proves semantics
or universal Microsoft Word fidelity. Complete the actual workflow.
"""
    if repair_note_ids:
        start = text.index("4. Render ALL THREE final actual PNGs")
        end = text.index("5. Verify DELETED footnote", start)
        text = (
            text[:start]
            + """4. Render ALL THREE post-edit actual PNGs at render_size1024 BEFORE any further
mutation. Compare every note's displayed content/number against the complete native
records. This evaluation uses Writer24.2.7, which can swap contents when native IDs
are out of body order. Record what the actual images show, including any mismatch.
Keep the complete pre-correction footnoteID11 and endnoteID5 references.
Then explicitly correct IDs using update_docx_notes with the current complete
catalog hash and definitions_and_native_body_references scope. Two remap_ids edits:
 - existing footnote part/kind footnote: mappings [{note_id:11,new_note_id:1}].
 - existing endnote part/kind endnote: mappings
   [{note_id:12,new_note_id:1},{note_id:5,new_note_id:2}].
Only these explicitly listed IDs may change. All other IDs, special definitions,
content, native ordering, formatting and human source bytes remain intact.
Read the COMPLETE review_request, mapping receipt, corrected catalog and EVERY
corrected note record. Render ALL THREE corrected final PNGs at render_size1024.
Check page1 NEW FOOTNOTE displayed1 / VERIFIED FOOTNOTE displayed2; page3 NEW
ENDNOTE displayedi / original ENDNOTE displayedii. Check body text/units and removed
old note. Native IDs changed explicitly; old references remain historical.
Verify BOTH retained pre-correction references (footnoteID11 and endnoteID5).
"""
            + text[end:]
        )
        text = text.replace(
            "all six actual PNGs", "all nine actual PNGs across four managed revisions"
        )
    return text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--font-fixture", required=True, type=Path)
    parser.add_argument("--repair-note-ids", action="store_true")
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
        "repair_note_ids": args.repair_note_ids,
    }
    (output / "expected.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    text = prompt(workspace, args.repair_note_ids)
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
    from tests.codex_docx_notes.audit import write_audit

    result = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": result["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
