# Native raster evaluation with the actual Codex CLI

This is an explicitly opted-in model evaluation. It uses the existing logged-in
CLI and its default model, only this checkout's `document` MCP tool, and isolated
data. It never overrides the model or edits the supplied source. Paid model calls
are not part of pytest or CI.

Prepare the hash-pinned NIST PDF corpus with `tests.real_pdf.corpus`, then run:

```sh
uv run python -m tests.codex_native_image.run \
  --corpus /absolute/path/to/corpus --output /absolute/new/evaluation-directory
uv run python -m tests.codex_native_image.audit /absolute/evaluation-directory
```

`--prepare-only` creates the fixture for visual inspection; `--resume-prepared`
then runs it, rejecting source/runtime drift and any existing trace. Keep failed
runs; choose a new directory for a new model run. Audits retain numbered attempts.

The input is an **explicit benchmark derivative**, not an originally published
NIST image: PDF page index 4, rasterized to 1,400 pixels on the long edge, stored
with EXIF orientation 6. The independent upright render and source PDF identity
are recorded outside the Agent's permitted inputs. The Agent visually transcribes
one real data row, crops it, composes/reorders/inserts/deletes TIFF frames, creates
an independent literal XLSX table, and retains region-to-cell provenance/Wikis.

The audit checks complete hash-paged reads before edits, actual source-bound PNG
pixels, exact native samples in all three TIFF revisions, candidate byte identity,
historical frame and selection references, six literal cells, the derivation and
three Wiki snapshots including complete source files and custom citation displays.
Frame/region pixels are checked with a separate decoding/rasterization recipe;
native record semantics are also compared against stored revisions. These are
mechanical checks, not an independent semantic model or universal viewer verdict.
Twenty-three small negative/positive regression cases run in normal pytest/CI.

Local NIST run: 258 successful calls, no tool errors, 304.08 seconds; 15 full-frame
PNGs, one region preview, three TIFF revisions, six cells and three Wiki snapshots.
The CLI exited successfully. The first runner wrapper subsequently failed because
its audit module had not yet been created; that log remains intact. Separate
completed audits passed. The wrapper now imports its audit before starting a run.
Full release and installed-artifact checks are recorded separately; this fixture
does not prove arbitrary photo, animation, private-layer or workbook-viewer fidelity.

`python -m tests.codex_native_image.replay /absolute/evaluation-directory` validates
the retained trace with an installed wheel/container, first requiring an exact
runtime source fingerprint. It performs no additional model calls and does not
rewrite the retained evidence. It must resolve `src` to the installed artifact,
not the checkout; mount the test package separately when running it in isolation.
