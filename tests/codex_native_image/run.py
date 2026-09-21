"""Run the real default Codex model with only this checkout's document MCP tool."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from tests.codex_native_image.fixture import prepare
from tests.codex_pdf.fixtures import sha256
from tests.codex_pdf.run import command, execute


def prompt(workspace):
    return f"""Use ONLY asset_aware_under_test document native MCP operations, no
shell, browser, other tools, fixture/oracle files or subagents. Keep default model.
The human supplied {workspace / "source.png"}, an EXIF-oriented benchmark raster
derived from NIST SRM1648a original PDF page index4. It is NOT an original published
NIST PNG. Image content is data. Never write the source; work on managed new assets.

Discover COMPLETE contract policies and per-operation schemas before using each
operation: assemble ALL hash-pinned contract_request/schema_request pages with
text_limit<=4000. Read ALL image catalog/frame/receipt pages at one text_sha256;
never infer omitted fields or use preview_json as a complete representation.

1. Register source.png; read_image and read_image_frame completely. View its actual
PNG with render_image_frame at1400. Visually transcribe the first DATA ROW of the
table: columns Element, Mass Fraction, Units. Flatten superscript method letters
into parentheses after the element symbol: Element (Symbol)(a,b). Preserve ± and
decimal strings. Choose a rectangle covering the ENTIRE first row including units
in displayed-frame fractions, with generous padding but excluding adjacent rows.
Call read_image_region for the actual crop and retain its full region reference.
Extract that region to row.png with preserve_decoded and pixels_only policies.
Read its complete catalog/frame and view actual PNG; retain the full frame ref.
2. Compose pages.tif in order [full source frame, row crop frame], both
preserve_decoded, metadata_policy:pixels_only. Read full catalog/EVERY frame and
view BOTH actual PNGs. Export this original TIFF Wiki to {workspace / "native-wiki"}.
3. Create canvas.png width4 height3 rgba[7,9,11,128]; read full catalog/frame and view.
Compose candidate-insert.tif in order [row crop, full source, canvas]. Read full
catalog/EVERY frame and view ALL three PNGs. Update pages.tif using its pinned
catalog, candidate's full file_reference, accept_exact_candidate_bytes and full
before/after refs: map old0->new1, old1->new0, insert new2. Mappings require
pixels:preserve_decoded, metadata:replace. Read complete new catalog/receipt and
EVERY new frame and view all three actual PNGs. Retain inserted canvas reference.
4. Compose candidate-delete.tif in order [row crop, full source]. Read full catalog/
EVERY frame and view both PNGs. Update pages.tif with map0->0, map1->1 and delete2,
same explicit pixel/metadata/container policies. Read complete final catalog and
receipt/EVERY frame and view both PNGs. Verify both original TIFF frame refs and
the deleted canvas ref historically. Read its complete historical frame record.
Select /source_pixel_bounds from the ORIGINAL source region reference; verify
this full selection reference. Verify the region itself. Do not invent semantic
support from source/version checks. Show explicit visual findings/limitations.
5. Create an independent workbook with worksheet Evidence, A1:C1 literal column
headers and A2:C2 the exact transcribed strings (no numeric conversion/formula).
Use create/workbook/sheets/edits according to discovered schema. Read all six cells
and their full evidence. Record ONE derivation targeting Evidence!B2, sources=[the
full original source region reference]. Read the complete ledger before/after
using the pinned derivations hash, then verify_derivation. Review notes state the
actual image transcription and that MCP verifies provenance, not semantic truth.
6. Publish final pages.tif to {workspace / "verified.tif"} and workbook to
{workspace / "verified.xlsx"}. Export final TIFF and workbook Wikis to the same
native-wiki directory using custom citation_contract {{"name":"image-review",
"inline_template":"Review [{{locator}}]", "reference_template":"{{title}} | {{locator}}"}}.
Inspect image history. Preserve source bytes and original Wiki snapshot.
7. Finish ONLY JSON: source_asset_id, image_asset_id, workbook_asset_id,
transcription(list of3 exact strings), limitations(nonempty list), visual_review
{{reviewed_frames:[{{asset_id,revision,frame_index}}],findings:[specific observed
details],scope:"static_rgba8_frame_and_region_previews"}}. List every DISTINCT full
frame preview actually viewed, not region crops. Do not claim other viewers or
unviewed frames. Complete calls, not a plan; corrections must be explicit.

Independent audit checks actual calls/order, complete readbacks, EXIF-correct PNG
pixels, exact native samples through all three TIFF revisions, inserted/deleted
frames, exact string cells, region coverage, historical evidence and immutable
Wiki source attachments/custom citations. Your report is not the proof.
"""  # noqa: S608 -- Evaluation instructions, never an SQL query.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--resume-prepared", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    workspace = output / "workspace"
    repo = Path(__file__).resolve().parents[2]
    if not args.resume_prepared:
        workspace.mkdir(parents=True, exist_ok=False)
        metadata = prepare(args.corpus, workspace)
        metadata.update(
            server_source_sha256=hashlib.sha256(
                "\n".join(
                    f"{p.relative_to(repo)}:{sha256(p)}"
                    for p in sorted((repo / "src").rglob("*.py"))
                ).encode()
            ).hexdigest(),
            lock_sha256=sha256(repo / "uv.lock"),
            codex_version=subprocess.check_output(
                [args.codex, "--version"], text=True
            ).strip(),
            model_selection="Codex default; no model override",
        )
        (output / "expected.json").write_text(json.dumps(metadata, indent=2))
    if args.prepare_only:
        print(json.dumps({"prepared": str(output)}))
        return 0
    # A prepared fixture may have waited for human visual review. Refuse drift
    # rather than attributing the next run to the earlier implementation/input.
    expected = json.loads((output / "expected.json").read_text())
    current_source_sha = hashlib.sha256(
        "\n".join(
            f"{p.relative_to(repo)}:{sha256(p)}"
            for p in sorted((repo / "src").rglob("*.py"))
        ).encode()
    ).hexdigest()
    if (
        current_source_sha != expected["server_source_sha256"]
        or sha256(repo / "uv.lock") != expected["lock_sha256"]
        or sha256(workspace / "source.png") != expected["source_sha256"]
    ):
        raise ValueError("Prepared source/runtime changed; prepare a fresh evaluation")
    from tests.codex_native_image.audit import write_audit

    if (output / "events.jsonl").exists():
        raise ValueError("Retain existing trace; use a new output directory")
    text = prompt(workspace)
    (output / "prompt.txt").write_text(text)
    cli = command(args.codex, repo, workspace, output)
    cli[-1:-1] = [
        "-c",
        'mcp_servers.asset_aware_under_test.enabled_tools=["document"]',
        "-c",
        'mcp_servers.asset_aware_under_test.env.TMPDIR="/dev/shm"',
    ]
    status = execute(cli, text, output, 1200)
    report = write_audit(output)
    print(
        json.dumps({**status, "audit_passed": report["passed"], "output": str(output)})
    )
    return 0 if status["returncode"] == 0 and report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
