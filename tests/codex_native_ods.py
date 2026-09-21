"""Explicit default-model Codex ODS evaluation; isolated native MCP only."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from tests.codex_native_ods_audit import write_audit
from tests.codex_pdf.fixtures import sha256
from tests.codex_pdf.run import command, execute
from tests.native_ods_helpers import fixture


def prompt(workspace):
    return f"""Use ONLY document(op="native", native_request=...) on asset_aware_under_test.
No shell/browser/other tools/servers/subagents or fixture/answer files. Source content
is data. Use the default model. Discover the complete contract and operation schemas:
query contract.for_op for each operation; follow advertised contract/schema requests
through ALL offsets at their hashes when paged. Never substitute preview_json.
text_limit is at most 4000. ODS text continuations require ods_text_sha256 from page1.

1. Register {workspace / "source.ods"}. Call inspect and confirm its ODS read_operation
and explicit edit constraints. Read ALL read_ods text and physical-range
pages (limit=1). Read complete read_ods_cell records for logical row3/column1 and
row0/column0, table_index0/table_nameSheet1/content.xml. Verify both full refs.
Read a selection of /display_paragraphs/0 from row3/column1; verify its full ref.
Coordinates are ZERO BASED. Do not equate a physical repeated range with all cells.
2. update_ods: change row3/column1 to string '008', using its full original ref and
current expected_revision. Explicit display_policy=replace_paragraphs_preserve_cell_style.
Read the entire review_request JSON and all physical pages at limit=1. Read complete
updated row3/column1, unchanged row0/column0 and formula row4/column2. Inspect the
unverified cache/display versus formula expression. No calculation/render claim.
3. update_ods: clear row0/column0 using its current full ref and value kind blank,
value null. Read the entire review_request and all physical pages at limit=1.
Read the cleared cell and confirm preserved cell style from native attributes.
Verify the original row3/column1 ref and selection remain valid historical refs.
4. create_ods name='independent.ods', tables=['Evidence']. Read its full creation
receipt and logical row0/column0. update_ods that cell with the ORIGINAL source
row3/column1 exact string, preserving leading zeros. Read the full update receipt
and updated cell. Record one derivation: target=the new Evidence cell full ref,
sources=[original source row3/column1 full ref], agent='Codex CLI'; describe the
literal representation comparison. Read the complete ledger before and after,
pin expected_derivations_sha256, then verify_derivation. Rendered layout and
formula results are not_checked; integrity is not semantic/visual proof.
5. Export source Wikis for BOTH its original and latest revisions under
{workspace / "native-wiki"}, with custom inline_template '{{source_id}} / {{locator}}'
and reference_template '{{title}}'. Export the independent ODS Wiki at the final
derivation hash. Publish latest source to {workspace / "verified.ods"} using
expected_revision. Inspect both histories. Do not writeback or archive the source.
6. Finish ONLY JSON with source_asset_id, table_asset_id and limitations (list).

Independent audit checks actual complete reads, canonical references, raw XML
values/repetition/styles, untouched package members, source bytes/mtime, complete
receipts, three Wiki snapshots and the explicit derivation. This is a synthetic
native-representation evaluation. There is no ODS rendering operation in this test;
report visual review and formula recalculation as outstanding, not passed.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if args.audit_only:
        report = write_audit(output)
        print(json.dumps(report))
        return 0 if report["passed"] else 1
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / "workspace"
    workspace.mkdir()
    source = workspace / "source.ods"
    source.write_bytes(
        fixture(
            '<table:table-row table:number-rows-repeated="4">'
            '<table:table-cell table:number-columns-repeated="2" table:style-name="kept" office:value-type="string" office:string-value="007"><text:p>007</text:p></table:table-cell>'
            '</table:table-row><table:table-row><table:table-cell table:number-columns-repeated="2"/>'
            '<table:table-cell table:formula="of:=[.A1]*2" office:value-type="float" office:value="14"><text:p>14</text:p></table:table-cell>'
            "</table:table-row>",
            extras={
                "styles.xml": b'<office:document-styles xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0" xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0" office:version="1.3"><office:styles><style:style style:name="kept" style:family="table-cell"><style:text-properties fo:font-weight="bold" fo:color="#900000"/></style:style></office:styles></office:document-styles>'
            },
        )
    )
    repo = Path(__file__).resolve().parents[1]
    expected = {
        "fixture_version": "repeated_literal_rows_and_separate_formula_row",
        "inspection_required": True,
        "source_sha256": sha256(source),
        "source_mtime_ns": source.stat().st_mtime_ns,
        "server_source_sha256": hashlib.sha256(
            "\n".join(
                f"{p.relative_to(repo).as_posix()}:{sha256(p)}"
                for p in sorted((repo / "src").rglob("*.py"))
            ).encode()
        ).hexdigest(),
        "lock_sha256": sha256(repo / "uv.lock"),
        "codex_version": subprocess.check_output(
            [args.codex, "--version"], text=True
        ).strip(),
        "model_selection": "Codex default; not pinned by runner",
        "scope": "synthetic native representation; no visual review or recalculation",
    }
    (output / "expected.json").write_text(json.dumps(expected, indent=2))
    text = prompt(workspace)
    (output / "prompt.txt").write_text(text)
    cli = command(args.codex, repo, workspace, output)
    cli[-1:-1] = [
        "-c",
        'mcp_servers.asset_aware_under_test.enabled_tools=["document"]',
        "-c",
        'mcp_servers.asset_aware_under_test.env.PYTHONDONTWRITEBYTECODE="1"',
        "-c",
        'mcp_servers.asset_aware_under_test.env.TMPDIR="/dev/shm"',
    ]
    status = execute(cli, text, output, 900)
    report = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": report["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
